"""API views untuk kuota penggunaan AI user."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.utils import get_user_quota_status


class QuotaStatusView(APIView):
    """Kembalikan status kuota harian user yang sedang login."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        quota = get_user_quota_status(request.user, request)
        return Response(quota)
