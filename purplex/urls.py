"""
URL configuration for purplex project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from .views import csrf_token
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('csrf/', csrf_token, name='csrf_token'),
        path('', include('purplex.problems_app.urls')),
        path('', include('purplex.users_app.urls')),
    ])),
]

urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )

# Serve Vue frontend at root
if settings.DEBUG is False:  # Only in production
    from django.http import HttpResponse

    def serve_vue_app(request, path=''):
        """Serve the Vue.js frontend application"""
        index_path = os.path.join(settings.BASE_DIR, 'purplex/client/dist/index.html')
        try:
            with open(index_path, 'r') as f:
                return HttpResponse(f.read(), content_type='text/html')
        except FileNotFoundError:
            return HttpResponse('Frontend not built. Please build the Vue app.', status=404)

    # Custom view to serve Vue static assets with correct MIME types
    def serve_vue_assets(request, *args, **kwargs):
        """Serve Vue.js static assets with correct MIME types"""
        # Handle different URL patterns
        if 'folder' in kwargs and 'filename' in kwargs:
            # For (js|css|assets)/(.*) pattern
            path = f"{kwargs['folder']}/{kwargs['filename']}"
        elif 'path' in kwargs:
            # For direct path parameter
            path = kwargs['path']
        elif len(args) >= 2:
            # For positional arguments from regex groups
            path = f'{args[0]}/{args[1]}'
        elif len(args) == 1:
            # Single path argument
            path = args[0]
        else:
            # Fall back to request path
            path = request.path.lstrip('/')

        file_path = os.path.join(settings.BASE_DIR, 'purplex/client/dist', path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            content_type = 'text/html'
            if path.endswith('.js'):
                content_type = 'application/javascript'
            elif path.endswith('.css'):
                content_type = 'text/css'
            elif path.endswith('.json'):
                content_type = 'application/json'
            elif path.endswith('.png'):
                content_type = 'image/png'
            elif path.endswith('.jpg') or path.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif path.endswith('.svg'):
                content_type = 'image/svg+xml'
            elif path.endswith('.ico'):
                content_type = 'image/x-icon'

            with open(file_path, 'rb') as f:
                return HttpResponse(f.read(), content_type=content_type)
        return HttpResponse('File not found', status=404)

    # Helper wrapper functions for different URL patterns
    def serve_folder_file(request, folder, filename):
        """Wrapper for folder/filename pattern"""
        return serve_vue_assets(request, folder=folder, filename=filename)

    def serve_by_path(request, *args, **kwargs):
        """Wrapper for direct path pattern"""
        return serve_vue_assets(request, path=request.path.lstrip('/'))

    # Serve Vue app's static assets (js, css, assets folders)
    urlpatterns += [
        re_path(r'^(js|css|assets)/(.*)$', serve_folder_file),
        re_path(r'^favicon\.ico$', serve_by_path),
        re_path(r'^.*\.(jpg|jpeg|png|gif|ico|svg)$', serve_by_path),
    ]

    # Catch all routes except api/admin/static/media
    urlpatterns += [
        re_path(r'^$', serve_vue_app),  # Root URL
        re_path(r'^(?!api|admin|static|media|js|css|assets).*$', serve_vue_app),  # All other non-API routes
    ]
