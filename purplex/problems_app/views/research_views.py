"""
Research data export views.
"""

import csv
from io import StringIO
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status as http_status

from purplex.problems_app.models import ProgressSnapshot
from purplex.problems_app.services.research_export_service import ResearchExportService
from purplex.problems_app.repositories.course_repository import CourseRepository
from purplex.problems_app.repositories.problem_set_repository import ProblemSetRepository
from purplex.users_app.repositories.user_repository import UserRepository
import hashlib


class ResearchDataExportView(APIView):
    """
    Export comprehensive research data in JSON format.

    Query Parameters:
        course: Course ID filter
        problem_set: Problem set slug filter
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        include_code: Include student code (default: false)
        anonymize: Anonymize user data (default: false)
        format: Export format (json or csv, default: json)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Export complete research dataset."""
        # Parse filters
        course_id = request.query_params.get('course')
        problem_set_slug = request.query_params.get('problem_set')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        include_code = request.query_params.get('include_code', 'false').lower() == 'true'
        anonymize = request.query_params.get('anonymize', 'false').lower() == 'true'
        export_format = request.query_params.get('format', 'json').lower()

        # Get course and problem set objects
        course = None
        problem_set = None

        if course_id:
            course = CourseRepository.get_course_by_id(course_id)
            if not course:
                return Response(
                    {'error': f'Course {course_id} not found'},
                    status=http_status.HTTP_404_NOT_FOUND
                )

        if problem_set_slug:
            problem_set = ProblemSetRepository.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                return Response(
                    {'error': f'Problem set {problem_set_slug} not found'},
                    status=http_status.HTTP_404_NOT_FOUND
                )

        # Parse dates
        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DD)'},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str)
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DD)'},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

        # Export data
        dataset = ResearchExportService.export_complete_dataset(
            course=course,
            problem_set=problem_set,
            start_date=start_date,
            end_date=end_date,
            include_code=include_code,
            anonymize=anonymize
        )

        # Return appropriate format
        if export_format == 'json':
            response = JsonResponse(dataset, safe=False)
            response['Content-Disposition'] = f'attachment; filename="research_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            return response
        else:
            return Response(
                {'error': 'Unsupported format. Use json.'},
                status=http_status.HTTP_400_BAD_REQUEST
            )


class ProgressHistoryExportView(APIView):
    """
    Export historical progress snapshots for time-series analysis.

    Query Parameters:
        course: Course ID filter
        problem_set: Problem set slug filter
        user: Username filter (optional)
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        anonymize: Anonymize user data (default: false)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Export progress history in CSV format."""
        from django.utils import timezone

        # Parse filters
        course_id = request.query_params.get('course')
        problem_set_slug = request.query_params.get('problem_set')
        username = request.query_params.get('user')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        anonymize = request.query_params.get('anonymize', 'false').lower() == 'true'

        # Build queryset via repository
        from ..repositories import ProgressRepository
        queryset = ProgressRepository.get_snapshots_base_queryset()

        # Apply filters
        if course_id:
            # Filter by problem sets in course
            course = CourseRepository.get_course_by_id(course_id)
            if not course:
                return Response(
                    {'error': f'Course {course_id} not found'},
                    status=http_status.HTTP_404_NOT_FOUND
                )
            problem_sets = course.problem_sets.all()
            queryset = queryset.filter(problem_set__in=problem_sets)

        if problem_set_slug:
            queryset = queryset.filter(problem_set__slug=problem_set_slug)

        if username:
            user = UserRepository.get_by_username(username)
            if not user:
                return Response(
                    {'error': f'User {username} not found'},
                    status=http_status.HTTP_404_NOT_FOUND
                )
            queryset = queryset.filter(user=user)

        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str).date()
                queryset = queryset.filter(snapshot_date__gte=start_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DD)'},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str).date()
                queryset = queryset.filter(snapshot_date__lte=end_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DD)'},
                    status=http_status.HTTP_400_BAD_REQUEST
                )

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'user_id',
            'user_email',
            'problem_slug',
            'problem_set_slug',
            'snapshot_date',
            'completion_percentage',
            'problems_completed',
            'average_score',
            'time_spent_today_seconds',
            'cumulative_time_seconds',
        ])

        # Track cumulative time per user/problem
        cumulative_time = {}

        # Write data rows
        for snapshot in queryset:
            # Anonymize if requested
            user_id = snapshot.user.username
            user_email = snapshot.user.email
            if anonymize:
                hash_key = hashlib.sha256(f"user_{snapshot.user.id}".encode()).hexdigest()[:16]
                user_id = f"user_{hash_key}"
                user_email = f"{hash_key}@anonymized.edu"

            # Calculate cumulative time
            key = f"{snapshot.user.id}_{snapshot.problem.id if snapshot.problem else 'all'}"
            if key not in cumulative_time:
                cumulative_time[key] = 0

            time_today = snapshot.time_spent_today.total_seconds() if snapshot.time_spent_today else 0
            cumulative_time[key] += time_today

            writer.writerow([
                user_id,
                user_email,
                snapshot.problem.slug if snapshot.problem else '',
                snapshot.problem_set.slug if snapshot.problem_set else '',
                snapshot.snapshot_date.isoformat(),
                snapshot.completion_percentage,
                snapshot.problems_completed,
                snapshot.average_score,
                time_today,
                cumulative_time[key],
            ])

        # Create response
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        filename = f'progress_history_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response
