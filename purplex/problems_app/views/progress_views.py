"""Views for tracking user progress on problems and problem sets."""

import logging
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from ..models import Problem, ProblemSet, Course, UserProgress, UserProblemSetProgress
from purplex.users_app.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class UserProgressView(APIView):
    """Get user's progress for a specific problem or all problems."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, problem_slug=None):
        user = request.user
        
        if problem_slug:
            # Get progress for specific problem
            problem = get_object_or_404(Problem, slug=problem_slug)
            try:
                progress = UserProgress.objects.get(user=user, problem=problem)
                return Response({
                    'problem_slug': problem.slug,
                    'status': progress.status,
                    'best_score': progress.best_score,
                    'attempts': progress.attempts,
                    'is_completed': progress.is_completed,
                    'completion_percentage': progress.completion_percentage,
                    'last_attempt': progress.last_attempt,
                    'completed_at': progress.completed_at,
                })
            except UserProgress.DoesNotExist:
                return Response({
                    'problem_slug': problem.slug,
                    'status': 'not_started',
                    'best_score': 0,
                    'attempts': 0,
                    'is_completed': False,
                    'completion_percentage': 0,
                    'last_attempt': None,
                    'completed_at': None,
                })
        else:
            # Get all progress for user
            progress_list = UserProgress.objects.filter(user=user).select_related('problem')
            progress_data = []
            
            for progress in progress_list:
                progress_data.append({
                    'problem_slug': progress.problem.slug,
                    'problem_title': progress.problem.title,
                    'status': progress.status,
                    'best_score': progress.best_score,
                    'attempts': progress.attempts,
                    'is_completed': progress.is_completed,
                    'completion_percentage': progress.completion_percentage,
                    'last_attempt': progress.last_attempt,
                })
            
            return Response(progress_data)


class ProblemSetProgressView(APIView):
    """Get user's progress for a problem set."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        user = request.user
        problem_set = get_object_or_404(ProblemSet, slug=slug)
        
        # Get course_id from query params if provided
        # Handle both DRF and Django requests
        query_params = getattr(request, 'query_params', request.GET)
        course_id = query_params.get('course_id')
        course = None
        if course_id:
            try:
                course = Course.objects.get(course_id=course_id)
            except Course.DoesNotExist:
                return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get or create problem set progress with course context
        set_progress, created = UserProblemSetProgress.objects.get_or_create(
            user=user,
            problem_set=problem_set,
            course=course,
            defaults={'total_problems': problem_set.problems.count()}
        )
        
        # If created, update the progress
        if created:
            # For new problem set progress, we'll update it based on any existing progress
            first_progress = UserProgress.objects.filter(
                user=user,
                problem_set=problem_set,
                course=course
            ).first()
            if first_progress:
                UserProblemSetProgress.update_from_progress(first_progress)
                set_progress.refresh_from_db()
        
        # Get individual problem progress with course context
        memberships = problem_set.problemsetmembership_set.all().select_related('problem')
        
        # Get all progress for this user, problem set, and course in one query
        user_progress_dict = {}
        user_progresses = UserProgress.objects.filter(
            user=user,
            problem_set=problem_set,
            course=course
        ).select_related('problem')
        
        for progress in user_progresses:
            user_progress_dict[progress.problem.id] = progress
        
        problems_progress = []
        for membership in memberships:
            problem = membership.problem
            progress = user_progress_dict.get(problem.id)
            
            if progress:
                status = progress.status
                best_score = progress.best_score
                attempts = progress.attempts
            else:
                status = 'not_started'
                best_score = 0
                attempts = 0
            
            problems_progress.append({
                'problem_slug': problem.slug,
                'problem_title': problem.title,
                'order': membership.order,
                'status': status,
                'best_score': best_score,
                'attempts': attempts,
            })
        
        # Sort by order
        problems_progress.sort(key=lambda x: x['order'])
        
        return Response({
            'problem_set': {
                'slug': problem_set.slug,
                'title': problem_set.title,
                'total_problems': set_progress.total_problems,
                'completed_problems': set_progress.completed_problems,
                'in_progress_problems': set_progress.in_progress_problems,
                'completion_percentage': set_progress.completion_percentage,
                'is_completed': set_progress.is_completed,
                'average_score': set_progress.average_score,
                'last_activity': set_progress.last_activity,
            },
            'problems_progress': problems_progress
        })


class UserProgressSummaryView(APIView):
    """Get summary of user's progress across all courses."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get all course progress for the user
        course_progresses = UserProblemSetProgress.objects.filter(
            user=user,
            course__isnull=False
        ).select_related('problem_set', 'course').order_by('course__course_id', 'problem_set__title')
        
        # Format course-based progress
        course_data = {}
        for progress in course_progresses:
            course_id = progress.course.course_id
            if course_id not in course_data:
                course_data[course_id] = {
                    'course_name': progress.course.name,
                    'problem_sets': []
                }
            course_data[course_id]['problem_sets'].append({
                'problem_set_slug': progress.problem_set.slug,
                'problem_set_title': progress.problem_set.title,
                'completed_problems': progress.completed_problems,
                'total_problems': progress.total_problems,
                'completion_percentage': progress.completion_percentage,
                'is_completed': progress.is_completed,
                'last_activity': progress.last_activity,
            })
        
        # Calculate overall stats
        total_problems = 0
        total_completed = 0
        
        for course_info in course_data.values():
            for ps in course_info['problem_sets']:
                total_problems += ps['total_problems']
                total_completed += ps['completed_problems']
        
        return Response({
            'overall': {
                'total_problems': total_problems,
                'completed_problems': total_completed,
                'completion_percentage': int((total_completed / total_problems * 100) if total_problems > 0 else 0),
            },
            'courses': course_data
        })