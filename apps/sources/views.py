"""Views for source management APIs."""

import os

import django_rq
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sources.models import GenerateJob, Source, SourceChunk
from apps.sources.providers import ChatProvider
from apps.sources.serializers import SourceDetailSerializer, SourceListSerializer
from apps.sources.utils import delete_source_from_supabase, upload_source_to_supabase
from apps.workspaces.models import Workspace


ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt"}
MAX_FILE_SIZE = 20 * 1024 * 1024


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
            .only("id", "original_filename", "status", "created_at")
            .order_by("-created_at")
        )


class SourceUploadView(APIView):
    """Upload a source file and queue background chunking."""

    permission_classes = [IsAuthenticated]

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
                {"file": "Only .pdf, .md, and .txt files are supported."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > MAX_FILE_SIZE:
            return Response(
                {"file": "File size must be 20MB or smaller."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        storage_path = f"workspaces/{workspace.id}/sources/{uploaded_file.name}"
        try:
            saved_path = upload_source_to_supabase(
                uploaded_file,
                storage_path,
                uploaded_file.content_type or 'application/octet-stream',
            )
        except Exception as exc:
            return Response(
                {'detail': f'Failed to upload file to Supabase: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            with transaction.atomic():
                source = Source.objects.create(
                    user=request.user,
                    workspace=workspace,
                    original_filename=uploaded_file.name,
                    mime_type=uploaded_file.content_type or "application/octet-stream",
                    file_size=uploaded_file.size,
                    storage_path=saved_path,
                    status="pending",
                    progress=0,
                    error_message="",
                )
        except IntegrityError:
            delete_source_from_supabase(saved_path)
            return Response(
                {"file": "A source with this file name already exists in this workspace."},
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
            delete_source_from_supabase(storage_path)

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


def _get_workspace_ready_chunks(request, workspace_id: str):
    workspace = get_object_or_404(
        Workspace.objects.filter(user=request.user),
        id=workspace_id,
    )

    chunks = SourceChunk.objects.filter(
        source__workspace=workspace,
        source__user=request.user,
        source__status="ready",
    ).values_list("text_content", flat=True)

    if not chunks.exists():
        return None, Response(
            {"detail": "No ready source chunks found for this workspace."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return chunks, None


class ChatView(APIView):
    """Chat endpoint using workspace source chunks as context."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response(
                {"message": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        chunks, error_response = _get_workspace_ready_chunks(request, id)
        if error_response:
            return error_response

        context_text = "\n\n".join(chunks)
        prompt = f"{context_text}\n\n{message}"

        response_text = ChatProvider.chat_complete(
            messages=[{"role": "user", "content": prompt}],
        )

        return Response({"response": response_text}, status=status.HTTP_200_OK)


class GenerateView(APIView):
    """Generate summary/mindmap/quiz/table from workspace source chunks."""

    permission_classes = [IsAuthenticated]

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

        context_text = "\n\n".join(chunks)
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
