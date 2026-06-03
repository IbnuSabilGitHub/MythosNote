"""API views for workspace generate feature."""

import django_rq
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.utils import check_and_increment_generate
from apps.generate.models import GenerateJob
from apps.generate.serializers import (
    GenerateCreateSerializer,
    GenerateJobCreatedSerializer,
    GenerateJobSerializer,
)
from apps.generate.services import GenerateContextError, get_generate_context
from apps.workspaces.models import Workspace


class GenerateRateThrottle(UserRateThrottle):
    scope = "generate"


class GenerateJobPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


class GenerateWorkspaceView(APIView):
    """POST: create job. GET: list jobs for workspace."""

    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        if self.request.method == "POST":
            return [GenerateRateThrottle()]
        return []

    def get(self, request, id):
        workspace = get_object_or_404(
            Workspace.objects.filter(user=request.user),
            id=id,
        )
        queryset = GenerateJob.objects.filter(user=request.user, workspace=workspace)
        paginator = GenerateJobPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = GenerateJobSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, id):
        serializer = GenerateCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        source_ids = [str(sid) for sid in data["source_ids"]]

        try:
            get_generate_context(
                user=request.user,
                workspace_id=id,
                source_ids=source_ids,
            )
        except GenerateContextError as exc:
            return Response({"detail": exc.message}, status=exc.status_code)

        if not check_and_increment_generate(request.user, request):
            return Response(
                {"detail": "Kuota harian generate telah habis."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        workspace = get_object_or_404(
            Workspace.objects.filter(user=request.user),
            id=id,
        )

        job = GenerateJob.objects.create(
            user=request.user,
            workspace=workspace,
            action=data["action"],
            source_ids=source_ids,
            options=data.get("options") or {},
            status="queued",
        )

        try:
            queue = django_rq.get_queue("default")
            queue.enqueue("apps.generate.tasks.process_generate_job", str(job.id))
        except Exception as exc:
            job.status = "failed"
            job.error_message = f"Failed to queue generate job: {exc}"
            job.save(update_fields=["status", "error_message", "updated_at"])
            return Response(
                {"detail": "Failed to queue generate job."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        out = GenerateJobCreatedSerializer(job)
        return Response({"generate_job": out.data}, status=status.HTTP_202_ACCEPTED)


class GenerateJobDetailView(APIView):
    """GET: poll job. DELETE: remove job."""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_object_or_404(
            GenerateJob.objects.filter(user=request.user),
            id=job_id,
        )
        return Response(GenerateJobSerializer(job).data, status=status.HTTP_200_OK)

    def delete(self, request, job_id):
        job = get_object_or_404(
            GenerateJob.objects.filter(user=request.user),
            id=job_id,
        )
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
