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

    # Catch all routes except api/admin/static/media
    urlpatterns += [
        re_path(r'^$', serve_vue_app),  # Root URL
        re_path(r'^(?!api|admin|static|media).*$', serve_vue_app),  # All other non-API routes
    ]
