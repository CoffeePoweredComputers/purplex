"""
Clean URL configuration for the redesigned pipeline.

Add these to your main urls.py to use the new endpoints.
"""

from django.urls import path
from .views.eipl_clean import CleanEiPLSubmissionView, TaskStatusView
from .views.sse_clean import CleanTaskSSEView, CleanTaskStatusView

app_name = 'problems_clean'

urlpatterns = [
    # Main submission endpoint
    path('submit/eipl/', CleanEiPLSubmissionView.as_view(), name='eipl_submit'),
    
    # Task status endpoints
    path('tasks/<str:task_id>/status/', CleanTaskStatusView.as_view(), name='task_status'),
    path('tasks/<str:task_id>/stream/', CleanTaskSSEView.as_view(), name='task_stream'),
]