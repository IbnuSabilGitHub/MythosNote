"""URLs untuk app sources."""

from django.urls import path

from apps.sources.views import SourceDetailView, SourceListView, SourceStatusView, SourceUploadView

urlpatterns = [
    path('api/sources/', SourceListView.as_view(), name='source-list'),
    path('api/sources/<uuid:id>/', SourceDetailView.as_view(), name='source-detail'),
    path('api/sources/<uuid:id>/status/', SourceStatusView.as_view(), name='source-status'),
    path('api/sources/upload/', SourceUploadView.as_view(), name='source-upload'),
]