"""
WSGI config for purplex project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

# IMPORTANT: Monkey patch must happen BEFORE any other imports when using gevent workers
# This makes standard library threading-compatible with gevent greenlets
try:
    from gevent import monkey
    monkey.patch_all()
except ImportError:
    pass  # gevent not installed, skip monkey patching

import os

from django.core.wsgi import get_wsgi_application

# Set environment to production by default for WSGI
os.environ.setdefault('PURPLEX_ENV', 'production')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purplex.settings')

application = get_wsgi_application()
