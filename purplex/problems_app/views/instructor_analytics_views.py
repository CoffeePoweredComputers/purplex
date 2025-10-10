"""
API views for instructor analytics.
"""

from django.http import HttpResponse
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from purplex.problems_app.models import Course, Problem
from purplex.problems_app.services.instructor_analytics_service import (
    InstructorAnalyticsService
)
from purplex.problems_app.services.course_export_service import CourseExportService


class InstructorCourseAnalyticsView(APIView):
    """
    Get analytics overview for a course.

    Requires: User must be the course instructor
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """Get course analytics overview."""
        try:
            course = Course.objects.get(course_id=course_id)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to view this course analytics'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get analytics
        analytics = InstructorAnalyticsService.get_course_overview(course)

        return Response(analytics, status=status.HTTP_200_OK)


class InstructorStudentListView(APIView):
    """
    Get list of students in a course with progress metrics.

    Query Parameters:
        sort_by: Field to sort by (progress, score, activity, name)
        order: Sort order (asc or desc)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """Get student list with metrics."""
        try:
            course = Course.objects.get(course_id=course_id)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to view this course'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get query parameters
        sort_by = request.query_params.get('sort_by', 'progress')
        order = request.query_params.get('order', 'desc')

        # Get student list
        students = InstructorAnalyticsService.get_student_list(
            course=course,
            sort_by=sort_by,
            order=order
        )

        return Response({
            'course_id': course.course_id,
            'students': students,
            'total_students': len(students),
        }, status=status.HTTP_200_OK)


class InstructorStudentDetailView(APIView):
    """
    Get detailed analytics for a specific student.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, user_id):
        """Get student detail analytics."""
        try:
            course = Course.objects.get(course_id=course_id)
            user = User.objects.get(id=user_id)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to view this data'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get student analytics
        analytics = InstructorAnalyticsService.get_student_detail(
            course=course,
            user=user
        )

        return Response(analytics, status=status.HTTP_200_OK)


class InstructorProblemAnalyticsView(APIView):
    """
    Get analytics for a specific problem.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, problem_slug):
        """Get problem analytics."""
        try:
            course = Course.objects.get(course_id=course_id)
            problem = Problem.objects.get(slug=problem_slug)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Problem.DoesNotExist:
            return Response(
                {'error': 'Problem not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to view this data'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get problem analytics
        analytics = InstructorAnalyticsService.get_problem_analytics(
            course=course,
            problem=problem
        )

        return Response(analytics, status=status.HTTP_200_OK)


class InstructorCourseExportView(APIView):
    """
    Export course progress to CSV.

    Query Parameters:
        include_inactive: Include inactive students (default: false)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        """Export course progress."""
        try:
            course = Course.objects.get(course_id=course_id)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verify instructor permission
        if course.instructor != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to export this course'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get parameters
        include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'

        # Generate CSV
        csv_data = CourseExportService.export_course_progress(
            course=course,
            include_inactive=include_inactive
        )

        # Create response
        response = HttpResponse(csv_data, content_type='text/csv')
        filename = f'course_{course.course_id}_progress_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
