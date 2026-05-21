"""URLs untuk app sources."""

from django.urls import path
from apps.sources.views import SourceUploadView

urlpatterns = [
    path('api/sources/upload/', SourceUploadView.as_view(), name='source-upload'),
]