"""
WSGI config for purplex project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Set environment to production by default for WSGI
os.environ.setdefault('PURPLEX_ENV', 'production')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purplex.settings')

application = get_wsgi_application()
