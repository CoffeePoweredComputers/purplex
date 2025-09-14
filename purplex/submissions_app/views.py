from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from purplex.users_app.permissions import IsAdmin, IsAuthenticated

import logging

from .services import SubmissionService

logger = logging.getLogger(__name__)

class SubmissionsPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

# PythonTestView removed - use problems_app.views.submission_views.TestSolutionView instead

# PromptSubmissionResultView removed - deprecated view

# SubmitCodeView removed - use problems_app.views.submission_views.SubmitSolutionView instead

class AdminSubmissionsView(APIView):
    """View for admin users to manage submissions"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """List all submissions with pagination and filtering (admin only)"""
        # Get query parameters
        search = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '').strip()
        problem_set_filter = request.GET.get('problem_set', '').strip()
        
        # Use service to get filtered submissions
        submissions = SubmissionService.get_all_submissions(
            search=search,
            status_filter=status_filter,
            problem_set_filter=problem_set_filter
        )
        
        # Apply pagination
        paginator = SubmissionsPagination()
        paginated_submissions = paginator.paginate_queryset(submissions, request)
        
        # Serialize the data using service
        submissions_data = []
        for submission in paginated_submissions:
            submissions_data.append(
                SubmissionService.format_submission_for_list(submission)
            )
        
        return paginator.get_paginated_response(submissions_data)
        
    def delete(self, request, submission_id):
        """Delete a submission (admin only)"""
        success = SubmissionService.delete_submission(submission_id)
        if success:
            return Response(status=204)
        return Response({"error": "Submission not found"}, status=404)

class AdminSubmissionExportView(APIView):
    """Export submissions data for CSV download (admin only)"""
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Get detailed submission data for CSV export"""
        filters = request.data.get('filters', {})
        
        # Use service to get export data
        export_data = SubmissionService.get_submissions_for_export(filters)
        
        return Response(export_data)

class AdminSubmissionDetailView(APIView):
    """Get detailed data for a single submission (admin only)"""
    permission_classes = [IsAdmin]
    
    def get(self, request, submission_id):
        """Get full submission details including user solution and feedback"""
        submission = SubmissionService.get_submission_detail(submission_id)
        if not submission:
            return Response({"error": "Submission not found"}, status=404)
        
        # Format submission data using service
        submission_data = SubmissionService.format_submission_for_export(submission)
        
        return Response(submission_data)

class UserLastSubmissionView(APIView):
    """Get user's most recent submission for a specific problem"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_slug):
        """Get the user's most recent submission for this problem"""
        try:
            # Get course_id from query params if provided
            course_id = request.query_params.get('course_id')
            
            # Use service to get last submission
            submission_data = SubmissionService.get_user_last_submission(
                user=request.user,
                problem_slug=problem_slug,
                course_id=course_id
            )
            
            if not submission_data:
                return Response({'has_submission': False})
            
            response_data = submission_data
            
            # Include detailed segmentation data if available
            try:
                if hasattr(submission, 'segmentation') and submission.segmentation:
                    segmentation_analysis = submission.segmentation.analysis
                    if segmentation_analysis and segmentation_analysis.get('success'):
                        response_data['segmentation'] = {
                            'segments': segmentation_analysis['segments'],
                            'segment_count': segmentation_analysis['segment_count'],
                            'comprehension_level': segmentation_analysis['comprehension_level'],
                            'feedback': segmentation_analysis['feedback'],
                            'user_prompt': submission.prompt,
                            'passed': submission.segmentation_passed
                        }
            except Exception as e:
                logger.warning(f"Failed to retrieve segmentation data: {str(e)}")
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error in UserLastSubmissionView: {str(e)}")
            return Response({'error': str(e)}, status=500)
