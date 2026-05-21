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
from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('project/', views.project, name='project'),
    path('workspace/', views.workspace, name='workspace'),
    path('', include('accounts.urls')),
    path('admin/', admin.site.urls),
    path('django-rq/', include('django_rq.urls')),
]
