"""
Konfigurasi URL untuk proyek config.

Daftar `urlpatterns` mengarahkan URL ke view. Info lebih lanjut:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Contoh:
Function views
    1. Tambah import:  from my_app import views
    2. Tambah URL ke urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Tambah import:  from other_app.views import Home
    2. Tambah URL ke urlpatterns:  path('', Home.as_view(), name='home')
Menyertakan URLconf lain
    1. Import include(): from django.urls import include, path
    2. Tambah URL ke urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from . import views


def _staff_required_urls(urlpatterns):
    """Wrap all views in urlpatterns with staff_member_required."""
    protected = []
    for pattern in urlpatterns:
        if hasattr(pattern, 'callback'):
            pattern.callback = staff_member_required(pattern.callback)
        protected.append(pattern)
    return protected


urlpatterns = [
    path('', views.home, name='home'),
    path('project/', views.project, name='project'),
    path('workspace/', views.workspace, name='workspace'),
    path('', include('apps.workspaces.urls')),
    path('', include('apps.accounts.urls')),
    path('', include('apps.sources.urls')),
    path('admin/', admin.site.urls),
    path('django-rq/', include((_staff_required_urls(
        __import__('django_rq.urls', fromlist=['urlpatterns']).urlpatterns
    ), 'django_rq'), namespace='django-rq')),
    path('404-test/', views.custom_404_view, name='404_test'),
]

handler404 = 'config.views.custom_404_view'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
