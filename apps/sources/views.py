"""Views for source management APIs."""

import os
import uuid

import django_rq
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from pgvector.django import CosineDistance
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from django.core.files.storage import default_storage

from apps.sources.models import GenerateJob, Source, SourceChunk, ChatSession, ChatMessage
from apps.sources.providers import ChatProvider, EmbeddingProvider
from apps.sources.serializers import SourceDetailSerializer, SourceListSerializer
from apps.workspaces.models import Workspace


ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024

# Magic bytes for file type validation
FILE_MAGIC_BYTES = {
    ".pdf": [b"%PDF"],
    ".docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
}


def _validate_file_magic(uploaded_file, extension: str) -> bool:
    """Validate file content matches expected magic bytes for the extension.

    Returns True if validation passes (magic matches or no magic check needed).
    """
    expected = FILE_MAGIC_BYTES.get(extension.lower())
    if not expected:
        return True  # No magic bytes check for .txt/.md
    pos = uploaded_file.tell()
    header = uploaded_file.read(8)
    uploaded_file.seek(pos)
    return any(header.startswith(magic) for magic in expected)


class UploadRateThrottle(UserRateThrottle):
    scope = 'upload'


class ChatRateThrottle(UserRateThrottle):
    scope = 'chat'


class GenerateRateThrottle(UserRateThrottle):
    scope = 'generate'


class SourcePagination(PageNumberPagination):
    """Default pagination for source lists."""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class SourceListView(ListAPIView):
    """List sources belonging to the authenticated user and workspace."""

    permission_classes = [IsAuthenticated]
    serializer_class = SourceListSerializer
    pagination_class = SourcePagination

    def get_queryset(self):
        workspace_id = self.request.query_params.get("workspace_id")
        if not workspace_id:
            raise ValidationError({"workspace_id": "This query parameter is required."})

        workspace = get_object_or_404(
            Workspace.objects.filter(user=self.request.user),
            id=workspace_id,
        )

        return (
            Source.objects.filter(user=self.request.user, workspace=workspace)
            .only("id", "original_filename", "status", "created_at", "file_size", "progress", "error_message")
            .order_by("-created_at")
        )


class SourceUploadView(APIView):
    """Upload a source file and queue background chunking."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [UploadRateThrottle]

    def post(self, request):
        workspace_id = request.data.get("workspace_id")
        if not workspace_id:
            return Response(
                {"workspace_id": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workspace = get_object_or_404(
            Workspace.objects.filter(user=request.user),
            id=workspace_id,
        )

        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"file": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, extension = os.path.splitext(uploaded_file.name)
        if extension.lower() not in ALLOWED_EXTENSIONS:
            return Response(
                {"file": "Format tidak didukung. Gunakan PDF, TXT, MD, atau DOCX."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > MAX_FILE_SIZE:
            return Response(
                {"file": "File terlalu besar. Maksimal 20 MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(uploaded_file.name) > 150:
            return Response(
                {"file": "Nama file terlalu panjang. Maksimal 150 karakter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not _validate_file_magic(uploaded_file, extension):
            return Response(
                {"file": "Isi file tidak sesuai dengan format yang diharapkan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        safe_name = os.path.basename(uploaded_file.name)
        from django.utils.text import get_valid_filename
        safe_name = get_valid_filename(safe_name)
        unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        storage_path = f"workspaces/{workspace.id}/sources/{unique_name}"
        try:
            saved_path = default_storage.save(storage_path, uploaded_file)
        except Exception:
            return Response(
                {'detail': 'Failed to save file. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            with transaction.atomic():
                import mimetypes
                detected_mime, _ = mimetypes.guess_type(uploaded_file.name)
                source = Source.objects.create(
                    user=request.user,
                    workspace=workspace,
                    original_filename=uploaded_file.name,
                    mime_type=detected_mime or "application/octet-stream",
                    file_size=uploaded_file.size,
                    storage_path=saved_path,
                    status="pending",
                    progress=0,
                    error_message="",
                )
        except IntegrityError:
            default_storage.delete(saved_path)
            return Response(
                {"file": "File dengan nama ini sudah ada di workspace."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            queue = django_rq.get_queue("default")
            queue.enqueue("apps.sources.tasks.process_source", str(source.id))
        except Exception as exc:
            source.status = "failed"
            source.error_message = f"Failed to queue source processing: {exc}"
            source.save(update_fields=["status", "error_message", "updated_at"])

        serializer = SourceDetailSerializer(source)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SourceDeleteView(APIView):
    """Delete a source belonging to the authenticated user."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        source = get_object_or_404(
            Source.objects.filter(user=request.user).select_related("workspace"),
            id=id,
        )

        storage_path = source.storage_path
        source.delete()
        if storage_path:
            default_storage.delete(storage_path)

        return Response(status=status.HTTP_204_NO_CONTENT)


class SourceStatusView(APIView):
    """Return source processing status for polling."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        source = get_object_or_404(
            Source.objects.filter(user=request.user).prefetch_related("chunks"),
            id=id,
        )
        serializer = SourceDetailSerializer(source)
        return Response(serializer.data, status=status.HTTP_200_OK)


MAX_GENERATE_CHUNKS = 200
MAX_GENERATE_CHARS = 15_000


def _get_workspace_ready_chunks(request, workspace_id: str):
    workspace = get_object_or_404(
        Workspace.objects.filter(user=request.user),
        id=workspace_id,
    )

    chunks = SourceChunk.objects.filter(
        source__workspace=workspace,
        source__user=request.user,
        source__status="ready",
    ).values_list("text_content", flat=True)[:MAX_GENERATE_CHUNKS]

    if not chunks.exists():
        return None, Response(
            {"detail": "No ready source chunks found for this workspace."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return chunks, None


class ChatView(APIView):
    """Chat endpoint using RAG: embed query → pgvector ANN → LLM generate."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatRateThrottle]
    # Dynamic Top-K: fetch kandidat lebih banyak, potong berdasarkan similarity
    TOP_K_MAX = 8       # kandidat maksimum yang di-fetch dari pgvector
    TOP_K_MIN = 2       # minimum chunk jika similarity sangat tinggi
    # Threshold similarity (1 - cosine_distance)
    SIM_HIGH = 0.85     # sangat relevan → ambil TOP_K_MIN chunk
    SIM_MED  = 0.70     # relevan        → ambil 4 chunk
    MAX_MESSAGE_LENGTH = 4000
    # Token efficiency: batasi history yang dikirim ke LLM
    HISTORY_WINDOW = 10  # jumlah pesan terakhir (user+assistant) yang disertakan
    EMBEDDING_ERROR_MESSAGE = "Gagal memproses pertanyaan. Coba lagi nanti."
    NO_CONTEXT_MESSAGE = "Belum ada sumber siap untuk workspace ini."
    LLM_ERROR_MESSAGE = "AI sedang tidak bisa menjawab. Coba lagi nanti."

    def post(self, request, id):
        user_question = (request.data.get("message") or "").strip()
        session_id = request.data.get("session_id")
        source_ids = request.data.get("source_ids")  # optional list of UUIDs

        if not user_question:
            return Response(
                {"message": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(user_question) > self.MAX_MESSAGE_LENGTH:
            return Response(
                {"message": f"Message must be {self.MAX_MESSAGE_LENGTH} characters or fewer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate workspace ownership
        workspace = get_object_or_404(
            Workspace.objects.filter(user=request.user),
            id=id,
        )

        base_qs = SourceChunk.objects.filter(
            source__workspace=workspace,
            source__user=request.user,
            source__status="ready",
            embedding__isnull=False,
        )

        # Filter by selected source_ids if provided and non-empty
        if source_ids and isinstance(source_ids, list) and len(source_ids) > 0:
            base_qs = base_qs.filter(source__id__in=source_ids)

        if not base_qs.exists():
            return Response(
                {"detail": self.NO_CONTEXT_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 1: Embed the user question
        try:
            query_embedding = EmbeddingProvider.get_embedding(user_question)
        except Exception:
            return Response(
                {"detail": self.EMBEDDING_ERROR_MESSAGE},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Step 2: pgvector ANN search — fetch TOP_K_MAX, potong dengan dynamic top-k
        candidates = list(
            base_qs
            .annotate(distance=CosineDistance("embedding", query_embedding))
            .order_by("distance")
            .select_related("source")[: self.TOP_K_MAX]
        )

        if not candidates:
            return Response(
                {"detail": self.NO_CONTEXT_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Dynamic Top-K: gunakan similarity teratas untuk tentukan berapa chunk dipakai
        # CosineDistance ∈ [0, 2]; similarity = 1 - distance ∈ [-1, 1]
        best_similarity = 1.0 - candidates[0].distance
        if best_similarity >= self.SIM_HIGH:
            dynamic_k = self.TOP_K_MIN          # sangat relevan: cukup 2 chunk
        elif best_similarity >= self.SIM_MED:
            dynamic_k = 4                       # relevan: 4 chunk
        else:
            dynamic_k = self.TOP_K_MAX          # kurang relevan: ambil semua 8

        top_chunks = candidates[:dynamic_k]

        # Step 3: Build context string and keep list of unique sources
        context_parts = []
        unique_sources = []
        seen_source_ids = set()
        # Token efficiency: format kompak + naikkan limit karena format lebih hemat
        max_context_chars = 8000
        current_len = 0

        for chunk in top_chunks:
            source_obj = chunk.source
            if source_obj.id not in seen_source_ids:
                seen_source_ids.add(source_obj.id)
                unique_sources.append({
                    "id": str(source_obj.id),
                    "original_filename": source_obj.original_filename,
                })

            # Format kompak: "[filename]: content" vs "[Dokumen: filename]\ncontent"
            part = f"[{source_obj.original_filename}]: {chunk.text_content}"
            if current_len + len(part) > max_context_chars:
                break
            context_parts.append(part)
            current_len += len(part)

        context_text = "\n\n".join(context_parts)

        # Step 4: Retrieve or create ChatSession
        if session_id:
            session = get_object_or_404(
                ChatSession.objects.filter(user=request.user, workspace=workspace),
                id=session_id,
            )
        else:
            title = user_question[:40] + ("..." if len(user_question) > 40 else "")
            session = ChatSession.objects.create(
                user=request.user,
                workspace=workspace,
                title=title,
            )

        # Step 5: Generate response via LLM with retrieved context & history
        # Token efficiency: system prompt dipersingkat tanpa kehilangan instruksi inti
        system_context = (
            "Jawab pertanyaan pengguna berdasarkan konteks dokumen berikut. "
            "Jika informasi tidak ada dalam konteks, katakan tidak ditemukan — jangan mengarang.\n\n"
            f"Konteks:\n{context_text}"
        )

        messages = [{"role": "system", "content": system_context}]

        # Retrieve previous messages — sliding window untuk hemat token
        history_msgs = (
            ChatMessage.objects.filter(session=session)
            .order_by("-created_at")[: self.HISTORY_WINDOW]
        )
        for msg in reversed(list(history_msgs)):
            messages.append({"role": msg.role, "content": msg.content})

        # Append current user question
        messages.append({"role": "user", "content": user_question})

        try:
            response_text = ChatProvider.chat_complete(
                messages=messages,
            )
        except Exception:
            return Response(
                {"detail": self.LLM_ERROR_MESSAGE},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Save user question and assistant reply to session
        created_at_str = timezone.now().isoformat()
        try:
            with transaction.atomic():
                ChatMessage.objects.create(
                    session=session,
                    role="user",
                    content=user_question,
                )
                assistant_msg = ChatMessage.objects.create(
                    session=session,
                    role="assistant",
                    content=response_text,
                    metadata={"sources": unique_sources},
                )
                session.save()  # Touch updated_at to bring it to top
                created_at_str = assistant_msg.created_at.isoformat()
        except Exception:
            pass

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
        workspace = get_object_or_404(
            Workspace.objects.filter(user=request.user),
            id=id,
        )
        sessions = ChatSession.objects.filter(
            user=request.user,
            workspace=workspace,
        ).order_by("-updated_at")

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
        session = get_object_or_404(
            ChatSession.objects.filter(user=request.user),
            id=session_id,
        )
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
        workspace = get_object_or_404(
            Workspace.objects.filter(user=request.user),
            id=id,
        )
        ChatSession.objects.filter(user=request.user, workspace=workspace).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GenerateView(APIView):
    """Generate summary/mindmap/quiz/table from workspace source chunks."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [GenerateRateThrottle]
    # Token efficiency: batasi context generate agar tidak kirim semua chunks
    MAX_GENERATE_CHARS = 12_000  # ~3k token; cukup untuk dokumen panjang

    PROMPT_TEMPLATES = {
        "summary": "Summarize the following context into concise bullet points.",
        "mindmap": "Create a mindmap outline with clear main branches and sub-branches.",
        "quiz": "Create a quiz with questions and answers based on the context.",
        "table": "Create a structured table with key entities and attributes.",
    }

    def post(self, request, id):
        action = (request.data.get("action") or "").strip().lower()
        if action not in self.PROMPT_TEMPLATES:
            return Response(
                {"action": "Invalid action. Use summary, mindmap, quiz, or table."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chunks, error_response = _get_workspace_ready_chunks(request, id)
        if error_response:
            return error_response

        # Bangun context dengan char-limit guard — hemat token, cegah blow-up
        context_parts = []
        total_chars = 0
        for chunk in chunks:
            if total_chars + len(chunk) > self.MAX_GENERATE_CHARS:
                break
            context_parts.append(chunk)
            total_chars += len(chunk)
        context_text = "\n\n".join(context_parts)

        instruction = self.PROMPT_TEMPLATES[action]
        prompt = f"{context_text}\n\nTask: {instruction}"

        job = GenerateJob.objects.create(
            user=request.user,
            workspace_id=id,
            action=action,
            status="queued",
        )

        try:
            queue = django_rq.get_queue("default")
            queue.enqueue("apps.sources.tasks.process_generate_job", str(job.id), prompt)
        except Exception as exc:
            job.status = "failed"
            job.error_message = f"Failed to queue generate job: {exc}"
            job.save(update_fields=["status", "error_message", "updated_at"])
            return Response(
                {"detail": "Failed to queue generate job."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"generate_job": {"id": str(job.id), "status": job.status}},
            status=status.HTTP_202_ACCEPTED,
        )
