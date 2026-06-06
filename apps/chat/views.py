"""Chat views: RAG-based chat endpoint dan session management."""

import logging
import traceback

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from pgvector.django import CosineDistance
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.chat.models import ChatSession, ChatMessage
from apps.core.providers import ChatProvider, EmbeddingProvider
from apps.sources.models import SourceChunk
from apps.workspaces.models import Workspace
from apps.accounts.utils import check_and_increment_prompt

logger = logging.getLogger(__name__)


class ChatRateThrottle(UserRateThrottle):
    scope = 'chat'


class ChatView(APIView):
    """Chat endpoint using RAG: embed query → pgvector ANN → LLM generate."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatRateThrottle]

    TOP_K_MAX = 8
    MAX_MESSAGE_LENGTH = 4000
    MAX_CONTEXT_CHARS = 20_000
    HISTORY_WINDOW = 10  # pesan terakhir yang disertakan ke LLM

    EMBEDDING_ERROR_MESSAGE = "Gagal memproses pertanyaan. Coba lagi nanti."
    NO_CONTEXT_MESSAGE = "Belum ada sumber siap untuk workspace ini."
    LLM_ERROR_MESSAGE = "AI sedang tidak bisa menjawab. Coba lagi nanti."

    def post(self, request, id):
        user_question = (request.data.get("message") or "").strip()
        session_id = request.data.get("session_id")
        source_ids = request.data.get("source_ids")

        if not check_and_increment_prompt(request.user, request):
            return Response(
                {"detail": "Kuota harian chat telah habis."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not user_question:
            return Response({"message": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        if len(user_question) > self.MAX_MESSAGE_LENGTH:
            return Response(
                {"message": f"Message must be {self.MAX_MESSAGE_LENGTH} characters or fewer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workspace = get_object_or_404(Workspace.objects.filter(user=request.user), id=id)

        # Validasi source_ids
        if not isinstance(source_ids, list) or len(source_ids) == 0:
            return Response(
                {"detail": "Harap pilih setidaknya satu dokumen untuk chat."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_qs = SourceChunk.objects.filter(
            source__workspace=workspace,
            source__user=request.user,
            source__status="ready",
            embedding__isnull=False,
        )

        if not base_qs.exists():
            return Response({"detail": self.NO_CONTEXT_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

        base_qs = base_qs.filter(source__id__in=source_ids)
        if not base_qs.exists():
            return Response(
                {"detail": "Dokumen yang dipilih tidak memiliki konteks yang siap."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 1: Embed query
        try:
            query_embedding = EmbeddingProvider.get_embedding(user_question)
        except Exception:
            traceback.print_exc()
            return Response({"detail": self.EMBEDDING_ERROR_MESSAGE}, status=status.HTTP_502_BAD_GATEWAY)

        # Step 2: Multi-Document RAG — per-source top-K lalu sort global
        per_source_k = max(2, self.TOP_K_MAX // len(source_ids))
        top_chunks = []
        for sid in source_ids:
            candidates = list(
                base_qs.filter(source__id=sid)
                .annotate(distance=CosineDistance("embedding", query_embedding))
                .order_by("distance")
                .select_related("source")[:per_source_k]
            )
            top_chunks.extend(candidates)

        if not top_chunks:
            return Response({"detail": self.NO_CONTEXT_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

        top_chunks.sort(key=lambda x: x.distance)

        # Step 3: Build context string
        context_parts: list[str] = []
        unique_sources: list[dict] = []
        seen_source_ids: set = set()
        current_len = 0

        for chunk in top_chunks:
            source_obj = chunk.source
            if source_obj.id not in seen_source_ids:
                seen_source_ids.add(source_obj.id)
                unique_sources.append({"id": str(source_obj.id), "original_filename": source_obj.original_filename})

            part = f"[{source_obj.original_filename}]: {chunk.text_content}"
            if current_len + len(part) > self.MAX_CONTEXT_CHARS:
                break
            context_parts.append(part)
            current_len += len(part)

        context_text = "\n\n".join(context_parts)

        # Step 4: Retrieve or create ChatSession
        if session_id:
            session = get_object_or_404(
                ChatSession.objects.filter(user=request.user, workspace=workspace), id=session_id
            )
        else:
            title = user_question[:40] + ("..." if len(user_question) > 40 else "")
            session = ChatSession.objects.create(user=request.user, workspace=workspace, title=title)

        # Step 5: Build message list (system + sliding window history + user)
        system_context = (
            "Hanya jawab pertanyaan berdasarkan konteks dokumen berikut. "
            "Tolak pertanyaan yang berada di luar topik dokumen. "
            "Jika informasi tidak ada dalam konteks, katakan tidak ditemukan — jangan mengarang.\n\n"
            f"Konteks:\n{context_text}"
        )
        messages = [{"role": "system", "content": system_context}]

        history = ChatMessage.objects.filter(session=session).order_by("-created_at")[: self.HISTORY_WINDOW]
        for msg in reversed(list(history)):
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_question})

        # Step 6: LLM call
        try:
            response_text = ChatProvider.chat_complete(messages=messages)
        except Exception:
            traceback.print_exc()
            return Response({"detail": self.LLM_ERROR_MESSAGE}, status=status.HTTP_502_BAD_GATEWAY)

        # Step 7: Persist messages
        created_at_str = timezone.now().isoformat()
        try:
            with transaction.atomic():
                ChatMessage.objects.create(session=session, role="user", content=user_question)
                assistant_msg = ChatMessage.objects.create(
                    session=session,
                    role="assistant",
                    content=response_text,
                    metadata={"sources": unique_sources},
                )
                session.save()  # touch updated_at
                created_at_str = assistant_msg.created_at.isoformat()
        except Exception:
            logger.warning("Gagal menyimpan pesan chat ke database.", exc_info=True)

        return Response(
            {
                "message": user_question,
                "response": response_text,
                "sources": unique_sources,
                "created_at": created_at_str,
                "session_id": str(session.id),
            },
            status=status.HTTP_200_OK,
        )


class ChatSessionListView(APIView):
    """List chat sessions in a workspace."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        workspace = get_object_or_404(Workspace.objects.filter(user=request.user), id=id)
        sessions = ChatSession.objects.filter(user=request.user, workspace=workspace).order_by("-updated_at")
        data = [
            {
                "id": str(s.id),
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]
        return Response(data, status=status.HTTP_200_OK)


class ChatMessageListView(APIView):
    """List messages in a chat session."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(ChatSession.objects.filter(user=request.user), id=session_id)
        messages = ChatMessage.objects.filter(session=session).order_by("created_at")
        data = [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
        return Response(data, status=status.HTTP_200_OK)


class ChatMessageDeleteView(APIView):
    """Delete all chat history in a workspace."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        workspace = get_object_or_404(Workspace.objects.filter(user=request.user), id=id)
        ChatSession.objects.filter(user=request.user, workspace=workspace).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
