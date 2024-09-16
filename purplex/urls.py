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
from django.urls import path, include
from django.views.generic import RedirectView

from .views import ProblemListView
from .views import ProblemSetListView
from .views import GetProblemSet
from .views import AIView

from purplex.views import submit_code, test_view


urlpatterns = [
    path('admin/', admin.site.urls),

    path('submit_code/', submit_code),
    path('submit_code/<int:problem_id>/', submit_code, name='submit_code'),

    path('api/problems/', ProblemListView.as_view(), name='problem_list'),

    path('api/problem-sets/', ProblemSetListView.as_view(), name='problem_set_list'),
    path('api/problem-set/<str:sid>', GetProblemSet.as_view(), name='get_problem_set'),

    path('api/generate/', AIView.as_view(), name='ai_generate'),
    path('api/test/', test_view, name='test_code')

] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
