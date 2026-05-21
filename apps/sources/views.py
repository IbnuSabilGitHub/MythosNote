"""Views untuk app sources."""

import os

from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sources.models import Source
from apps.workspaces.models import Workspace
from apps.sources.serializers import (
    SourceListSerializer,
    SourceSerializer,
    SourceStatusSerializer,
)
from apps.sources.tasks import process_source


ALLOWED_EXTENSIONS = {'.pdf', '.md', '.txt'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


class SourcePagination(PageNumberPagination):
    """Pagination standar untuk daftar source."""

    page_size = 10
    page_size_query_param = None


class SourceUploadView(APIView):
    """View untuk upload file source ke workspace."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Handle POST request untuk upload file source.

        Args:
            request: HTTP request object.

        Returns:
            Response dengan serializer Source dan status 201 jika berhasil,
            atau Response dengan error message jika gagal.
        """
        # Dapatkan workspace_id dari request.data
        workspace_id = request.data.get('workspace_id')
        if not workspace_id:
            return Response(
                {'error': 'workspace_id harus disertakan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validasi: workspace harus milik request.user
        workspace = get_object_or_404(
            Workspace.objects.filter(user=request.user),
            id=workspace_id
        )

        # Dapatkan file dari request.FILES
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'error': 'File harus disertakan dalam request.FILES["file"].'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validasi ekstensi file
        _, ext = os.path.splitext(uploaded_file.name)
        ext_lower = ext.lower()
        if ext_lower not in ALLOWED_EXTENSIONS:
            return Response(
                {'error': f'Ekstensi file tidak diizinkan. Hanya {", ".join(ALLOWED_EXTENSIONS)} yang diperbolehkan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validasi ukuran file (maks 20MB)
        if uploaded_file.size > MAX_FILE_SIZE:
            return Response(
                {'error': f'Ukuran file terlalu besar. Maksimal {MAX_FILE_SIZE // (1024 * 1024)}MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validasi: nama file belum ada di workspace
        if Source.objects.filter(workspace=workspace, original_filename=uploaded_file.name).exists():
            return Response(
                {'error': f'File dengan nama "{uploaded_file.name}" sudah ada di workspace ini.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Simpan file ke storage default Django
        storage_path = f'workspaces/{workspace_id}/sources/{uploaded_file.name}'
        saved_path = default_storage.save(storage_path, uploaded_file)

        # Tentukan mime_type
        mime_type = uploaded_file.content_type or 'application/octet-stream'

        # Buat objek Source dengan status='pending'
        source = Source.objects.create(
            user=request.user,
            workspace=workspace,
            original_filename=uploaded_file.name,
            mime_type=mime_type,
            file_size=uploaded_file.size,
            storage_path=saved_path,
            status='pending'
        )

        # Enqueue job RQ untuk memproses source
        from django_rq import get_queue
        queue = get_queue('default')
        queue.enqueue('apps.sources.tasks.process_source', str(source.id))

        # Balikkan serializer Source dengan status 201
        serializer = SourceSerializer(source)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SourceStatusView(APIView):
    """View untuk status processing source milik user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        """Ambil status source dan ringkasan chunk."""

        source = get_object_or_404(Source.objects.filter(user=request.user), id=id)
        total_chunks = source.chunks.count()
        successful_chunks = source.chunks.filter(metadata__status='ready').count()
        serializer = SourceStatusSerializer(
            {
                'id': source.id,
                'status': source.status,
                'progress': source.progress,
                'total_chunks': total_chunks,
                'successful_chunks': successful_chunks,
                'failed_chunks': max(total_chunks - successful_chunks, 0),
                'error_message': source.error_message,
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class SourceListView(ListAPIView):
    """View daftar source milik user."""

    permission_classes = [IsAuthenticated]
    serializer_class = SourceListSerializer
    pagination_class = SourcePagination

    def get_queryset(self):
        """Filter source hanya milik user aktif."""

        queryset = Source.objects.filter(user=self.request.user).select_related('workspace')

        workspace_id = self.request.query_params.get('workspace_id')
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)

        source_status = self.request.query_params.get('status')
        if source_status:
            queryset = queryset.filter(status=source_status)

        return queryset


class SourceDetailView(RetrieveDestroyAPIView):
    """View detail dan hapus source milik user."""

    permission_classes = [IsAuthenticated]
    serializer_class = SourceSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """Batasi akses ke source milik user aktif."""

        return Source.objects.filter(user=self.request.user).select_related('workspace')

    def perform_destroy(self, instance):
        """Hapus file mentah dari storage setelah source dihapus."""

        storage_path = instance.storage_path
        instance.delete()
        default_storage.delete(storage_path)