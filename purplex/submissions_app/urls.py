from django.urls import path
from .views import (
    PythonTestView, 
    PromptSubmissionResultView, 
    SubmitCodeView,
    AdminSubmissionsView,
    AdminSubmissionExportView,
    AdminSubmissionDetailView
)

urlpatterns = [
    # Regular user endpoints
    path('test/', PythonTestView.as_view(), name='test_code'),
    path('submit_code/<int:problem_id>/', SubmitCodeView.as_view(), name='submit_code'),
    path('result/<int:submission_id>/', PromptSubmissionResultView.as_view(), name='submission_result'),
    
    # Admin endpoints
    path('admin/submissions/', AdminSubmissionsView.as_view(), name='admin_submissions'),
    path('admin/submissions/export/', AdminSubmissionExportView.as_view(), name='admin_submissions_export'),
    path('admin/submissions/<int:submission_id>/', AdminSubmissionDetailView.as_view(), name='admin_submission_detail'),
    path('admin/submission/<int:submission_id>/', AdminSubmissionsView.as_view(), name='admin_submission_delete'),
]