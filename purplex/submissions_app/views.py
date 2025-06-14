from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from purplex.users_app.permissions import IsAdmin, IsAdminOrReadOnly, IsAuthenticated

import json
import docker
import logging

from .models import PromptSubmission
from purplex.problems_app.models import Problem

logger = logging.getLogger(__name__)

class SubmissionsPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

class PythonTestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        data = request.data
        generated_code = data.get('generated_code')
        problem_slug = data.get('problem_slug')

        problem = Problem.objects.get(slug=problem_slug)
        
        # Use database-native test cases instead of files
        from purplex.problems_app.services import CodeExecutionService
        
        service = CodeExecutionService()
        test_results = service.test_solution(
            user_code=generated_code,
            function_name=problem.function_name,
            test_cases=list(problem.test_cases.all())
        )

        return JsonResponse({"test_results": test_results})

class PromptSubmissionResultView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, submission_id):
        # Get the submission
        submission = get_object_or_404(PromptSubmission, id=submission_id)
        
        # Check if user is admin or the owner of this submission
        if request.user == submission.user or hasattr(request.user, 'profile') and request.user.profile.is_admin:
            return render(request, 'submission_result.html', {'submission': submission})
        else:
            return JsonResponse({'error': 'Permission denied'}, status=403)

class SubmitCodeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, problem_id):
        data = json.loads(request.body)
        code = data.get('code', '')
        
        problem = get_object_or_404(Problem, id=problem_id)
        
        # Get the problem set - required field
        # For now, get the first problem set containing this problem
        problem_set = problem.problem_sets.first()
        if not problem_set:
            return JsonResponse({'error': 'Problem must belong to a problem set'}, status=400)
        
        submission = PromptSubmission.objects.create(
            user=request.user,
            problem=problem,
            problem_set=problem_set,
            score=0,  # Initial score
            prompt=code
        )

        # Test the code using database-native test cases
        from purplex.problems_app.services import CodeExecutionService
        
        service = CodeExecutionService()
        results = service.test_solution(
            user_code=code,
            function_name=problem.function_name,
            test_cases=list(problem.test_cases.all())
        )
        
        # Update submission with test results using new field structure
        passed_tests = sum(1 for test in results if test.get('pass', False))
        total_tests = len(results)
        if total_tests > 0:
            submission.score = int((passed_tests / total_tests) * 100)
        
        # Update with new field structure
        submission.test_results = results
        submission.code_variations = [code]
        submission.passing_variations = 1 if submission.score >= 100 else 0
        submission.total_variations = 1
        submission.save()

        return JsonResponse({'results': results})

class AdminSubmissionsView(APIView):
    """View for admin users to manage submissions"""
    permission_classes = [IsAdmin]
    
    def get(self, request):
        """List all submissions with pagination and filtering (admin only)"""
        # Get query parameters
        search = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '').strip()
        problem_set_filter = request.GET.get('problem_set', '').strip()
        
        # Start with all submissions
        submissions = PromptSubmission.objects.all().select_related('user', 'problem', 'problem_set')
        
        # Apply search filter
        if search:
            submissions = submissions.filter(
                models.Q(user__username__icontains=search) |
                models.Q(problem__title__icontains=search) |
                models.Q(problem_set__title__icontains=search)
            )
        
        # Apply status filter
        if status_filter:
            if status_filter == 'passed':
                submissions = submissions.filter(score__gte=100)
            elif status_filter == 'partial':
                submissions = submissions.filter(score__gt=0, score__lt=100)
            elif status_filter == 'failed':
                submissions = submissions.filter(score=0)
        
        # Apply problem set filter
        if problem_set_filter:
            submissions = submissions.filter(problem_set__title=problem_set_filter)
        
        # Order by creation time (newest first)
        submissions = submissions.order_by('-submitted_at')
        
        # Apply pagination
        paginator = SubmissionsPagination()
        paginated_submissions = paginator.paginate_queryset(submissions, request)
        
        # Serialize the data
        submissions_data = []
        for submission in paginated_submissions:
            # Calculate status based on score
            if submission.score >= 100:
                status = 'passed'
            elif submission.score > 0:
                status = 'partial'
            else:
                status = 'failed'
                
            submissions_data.append({
                'id': submission.id,
                'user': submission.user.username,
                'problem': submission.problem.title,
                'problem_set': submission.problem_set.title if submission.problem_set else 'Unknown',
                'score': submission.score,
                'status': status,
                'submitted_at': submission.submitted_at,
            })
        
        return paginator.get_paginated_response(submissions_data)
        
    def delete(self, request, submission_id):
        """Delete a submission (admin only)"""
        submission = get_object_or_404(PromptSubmission, id=submission_id)
        submission.delete()
        return Response(status=204)

class AdminSubmissionExportView(APIView):
    """Export submissions data for CSV download (admin only)"""
    permission_classes = [IsAdmin]
    
    def post(self, request):
        """Get detailed submission data for CSV export"""
        filters = request.data.get('filters', {})
        
        # Start with all submissions
        submissions = PromptSubmission.objects.all().select_related('user', 'problem', 'problem_set')
        
        # Apply filters
        search_query = filters.get('search', '').strip().lower()
        if search_query:
            submissions = submissions.filter(
                models.Q(user__username__icontains=search_query) |
                models.Q(problem__title__icontains=search_query) |
                models.Q(problem_set__title__icontains=search_query)
            )
        
        status_filter = filters.get('status', '').strip()
        if status_filter:
            # Filter by score ranges based on status
            if status_filter == 'passed':
                submissions = submissions.filter(score__gte=100)
            elif status_filter == 'partial':
                submissions = submissions.filter(score__gt=0, score__lt=100)
            elif status_filter == 'failed':
                submissions = submissions.filter(score=0)
        
        problem_set_filter = filters.get('problem_set', '').strip()
        if problem_set_filter:
            submissions = submissions.filter(problem_set__title=problem_set_filter)
        
        # Prepare detailed data for export
        export_data = []
        for submission in submissions:
            # Calculate status
            if submission.score >= 100:
                status = 'passed'
            elif submission.score > 0:
                status = 'partial'
            else:
                status = 'failed'
            
            export_data.append({
                'id': submission.id,
                'user': submission.user.username,
                'problem': submission.problem.title,
                'problem_set': submission.problem_set.title if submission.problem_set else 'Unknown',
                'course': submission.course.course_id if submission.course else None,
                'score': submission.score,
                'status': status,
                'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else '',
                'prompt': submission.prompt or '',
                
                # Submission field structure
                'code_variations': submission.code_variations or [],
                'test_results': submission.test_results or [],
                'passing_variations': submission.passing_variations or 0,
                'total_variations': submission.total_variations or 0,
                'execution_time': submission.execution_time,
                'time_spent': str(submission.time_spent) if submission.time_spent else None
            })
        
        return Response(export_data)

class AdminSubmissionDetailView(APIView):
    """Get detailed data for a single submission (admin only)"""
    permission_classes = [IsAdmin]
    
    def get(self, request, submission_id):
        """Get full submission details including user solution and feedback"""
        submission = get_object_or_404(PromptSubmission, id=submission_id)
        
        # Calculate status
        if submission.score >= 100:
            status = 'passed'
        elif submission.score > 0:
            status = 'partial'
        else:
            status = 'failed'
        
        submission_data = {
            'id': submission.id,
            'user': submission.user.username,
            'problem': submission.problem.title,
            'problem_set': submission.problem_set.title if submission.problem_set else 'Unknown',
            'course': submission.course.course_id if submission.course else None,
            'score': submission.score,
            'status': status,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else '',
            'prompt': submission.prompt or '',
            
            # Submission field structure
            'code_variations': submission.code_variations or [],
            'test_results': submission.test_results or [],
            'passing_variations': submission.passing_variations or 0,
            'total_variations': submission.total_variations or 0,
            'execution_time': submission.execution_time,
            'time_spent': str(submission.time_spent) if submission.time_spent else None
        }
        
        return Response(submission_data)

class UserLastSubmissionView(APIView):
    """Get user's most recent submission for a specific problem"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_slug):
        """Get the user's most recent submission for this problem"""
        try:
            # Get course_id from query params if provided
            course_id = request.query_params.get('course_id')
            
            # Check if problem exists
            from purplex.problems_app.models import Problem, Course
            problem = Problem.objects.filter(slug=problem_slug).first()
            if not problem:
                return Response({'has_submission': False})
            
            # Build query with optional course filter
            query = PromptSubmission.objects.filter(
                user=request.user,
                problem=problem
            )
            
            # Add course filter if provided
            if course_id:
                try:
                    course = Course.objects.get(course_id=course_id)
                    query = query.filter(course=course)
                except Course.DoesNotExist:
                    return Response({'has_submission': False})
            else:
                # If no course specified, get non-course submissions
                query = query.filter(course__isnull=True)
            
            # Get the most recent submission
            submission = query.select_related('problem', 'problem_set', 'course').order_by('-submitted_at').first()
            
            if not submission:
                return Response({'has_submission': False})
            
            # Direct field access - no JSON parsing needed!
            return Response({
                'has_submission': True,
                'submission_id': submission.id,
                'score': submission.score,
                'variations': submission.code_variations,
                'results': submission.test_results,
                'passing_variations': submission.passing_variations,
                'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
                'user_prompt': submission.prompt
            })
            
        except Exception as e:
            logger.error(f"Error in UserLastSubmissionView: {str(e)}")
            return Response({'error': str(e)}, status=500)
