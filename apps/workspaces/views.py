from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from .models import Workspace


class WorkspaceRenameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"name": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        workspace = get_object_or_404(Workspace.objects.filter(user=request.user), id=id)
        workspace.name = name
        workspace.save(update_fields=["name", "updated_at"])  # updated_at will auto-update

        return Response({"id": str(workspace.id), "name": workspace.name}, status=status.HTTP_200_OK)


class WorkspaceDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        workspace = get_object_or_404(Workspace.objects.filter(user=request.user), id=id)
        workspace.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
