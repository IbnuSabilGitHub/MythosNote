"""Views untuk app sources."""

import os
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.sources.models import Source
from apps.workspaces.models import Workspace
from apps.sources.serializers import SourceSerializer
from apps.sources.tasks import process_source


ALLOWED_EXTENSIONS = {'.pdf', '.md', '.txt'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


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