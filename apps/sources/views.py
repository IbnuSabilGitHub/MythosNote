"""Views for source management APIs."""

import mimetypes
import os
import uuid

import django_rq
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.text import get_valid_filename
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.utils import check_and_increment_upload
from apps.sources.models import Source, SourceChunk
from apps.sources.serializers import SourceDetailSerializer, SourceListSerializer
from apps.workspaces.models import Workspace


ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# Magic bytes for file type validation
FILE_MAGIC_BYTES = {
    ".pdf": [b"%PDF"],
    ".docx": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"],
}


def _validate_file_magic(uploaded_file: UploadedFile, extension: str) -> bool:
    """Validate file content matches expected magic bytes for the extension.

    Returns True if validation passes (no magic check needed, or magic matches).
    """
    expected = FILE_MAGIC_BYTES.get(extension.lower())
    if not expected:
        return True
    pos = uploaded_file.tell()
    header = uploaded_file.read(8)
    uploaded_file.seek(pos)
    return any(header.startswith(magic) for magic in expected)


class UploadRateThrottle(UserRateThrottle):
    scope = 'upload'


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
            return Response({"workspace_id": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        workspace = get_object_or_404(Workspace.objects.filter(user=request.user), id=workspace_id)

        if Source.objects.filter(workspace=workspace).count() >= settings.WORKSPACE_MAX_SOURCES:
            return Response(
                {"detail": f"Workspace ini telah mencapai batas maksimal dokumen ({settings.WORKSPACE_MAX_SOURCES})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not check_and_increment_upload(request.user, request):
            return Response(
                {"detail": "Kuota upload/embedding harian Anda telah habis."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response({"file": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        _, extension = os.path.splitext(uploaded_file.name)
        if extension.lower() not in ALLOWED_EXTENSIONS:
            return Response(
                {"file": "Format tidak didukung. Gunakan PDF, TXT, MD, atau DOCX."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > MAX_FILE_SIZE:
            return Response(
                {"file": f"File terlalu besar. Maksimal {MAX_FILE_SIZE_MB} MB."},
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

        safe_name = get_valid_filename(os.path.basename(uploaded_file.name))
        unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        storage_path = f"workspaces/{workspace.id}/sources/{unique_name}"
        try:
            saved_path = default_storage.save(storage_path, uploaded_file)
        except Exception:
            return Response({"detail": "Failed to save file. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            with transaction.atomic():
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
            return Response({"file": "File dengan nama ini sudah ada di workspace."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            queue = django_rq.get_queue("default")
            queue.enqueue("apps.sources.tasks.process_source", str(source.id))
        except Exception as exc:
            source.status = "failed"
            source.error_message = f"Failed to queue source processing: {exc}"
            source.save(update_fields=["status", "error_message", "updated_at"])

        return Response(SourceDetailSerializer(source).data, status=status.HTTP_201_CREATED)


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


class SourceDownloadView(APIView):
    """Download a source file belonging to the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        source = get_object_or_404(Source.objects.filter(user=request.user), id=id)

        if not default_storage.exists(source.storage_path):
            return Response({"detail": "File tidak ditemukan di storage."}, status=status.HTTP_404_NOT_FOUND)

        file_handle = default_storage.open(source.storage_path, "rb")
        response = FileResponse(file_handle, content_type=source.mime_type)
        response["Content-Disposition"] = f'attachment; filename="{source.original_filename}"'
        return response


class SourceStatusView(APIView):
    """Return source processing status for polling."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        source = get_object_or_404(
            Source.objects.filter(user=request.user).prefetch_related("chunks"),
            id=id,
        )
        return Response(SourceDetailSerializer(source).data, status=status.HTTP_200_OK)
