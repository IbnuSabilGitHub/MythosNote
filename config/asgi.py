"""
Konfigurasi ASGI untuk proyek config.

Mengekspos callable ASGI sebagai variabel modul bernama ``application``.

Info lebih lanjut:
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
