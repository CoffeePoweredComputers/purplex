"""
URL configuration for the new submission system.
"""

from django.urls import path
from . import views

app_name = 'submissions'

urlpatterns = [
    # CSV Export
    path('export/csv/', views.ExportSubmissionsCSV.as_view(), name='export_csv'),

    # API Endpoints
    path('api/<str:submission_id>/', views.SubmissionDetailAPI.as_view(), name='detail'),
    path('api/stats/', views.UserSubmissionStatsAPI.as_view(), name='stats'),
]