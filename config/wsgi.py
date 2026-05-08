"""
Konfigurasi WSGI untuk proyek config.

Mengekspos callable WSGI sebagai variabel modul bernama ``application``.

Info lebih lanjut:
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
