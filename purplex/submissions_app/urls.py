from django.urls import path
from .views import (
    AdminSubmissionsView,
    AdminSubmissionExportView,
    AdminSubmissionDetailView,
    UserLastSubmissionView
)

urlpatterns = [
    # Regular user endpoints
    # Note: test/, submit_code/, and result/ endpoints have been moved to problems_app
    path('user/last-submission/<str:problem_slug>/', UserLastSubmissionView.as_view(), name='user_last_submission'),
    
    # Admin endpoints
    path('admin/submissions/', AdminSubmissionsView.as_view(), name='admin_submissions'),
    path('admin/submissions/export/', AdminSubmissionExportView.as_view(), name='admin_submissions_export'),
    path('admin/submissions/<int:submission_id>/', AdminSubmissionDetailView.as_view(), name='admin_submission_detail'),
    path('admin/submission/<int:submission_id>/', AdminSubmissionsView.as_view(), name='admin_submission_delete'),
]