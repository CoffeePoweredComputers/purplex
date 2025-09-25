"""
Views for the new submission system.
Provides CSV export and API endpoints for submission data.
"""

import csv
import json
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Prefetch

from .models import (
    Submission,
    TestExecution,
    HintActivation,
    CodeVariation,
    SegmentationAnalysis
)
from .services import SubmissionService


class ExportSubmissionsCSV(APIView):
    """
    Export submissions to CSV with complete data.
    Much cleaner than the old system's nested JSON approach.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """
        Generate CSV export of submissions with all related data.
        """
        # Get filter parameters
        course_id = request.query_params.get('course')
        problem_set_slug = request.query_params.get('problem_set')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Build queryset with optimized prefetch
        queryset = Submission.objects.select_related(
            'user',
            'problem',
            'problem_set',
            'course',
        ).prefetch_related(
            'test_executions__test_case',
            'hint_activations__hint',
            'code_variations',
            'segmentation',
            'feedback'
        )

        # Apply filters
        if course_id:
            queryset = queryset.filter(course__course_id=course_id)
        if problem_set_slug:
            queryset = queryset.filter(problem_set__slug=problem_set_slug)
        if start_date:
            queryset = queryset.filter(submitted_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(submitted_at__lte=end_date)

        # Order by submission time
        queryset = queryset.order_by('-submitted_at')

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        filename = f'submissions_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Define CSV fields
        fieldnames = [
            # Basic info
            'submission_id',
            'user',
            'problem',
            'problem_set',
            'course',
            'submission_type',
            'submitted_at',

            # Scores and status
            'score',
            'completion_status',
            'execution_status',
            'passed_all_tests',

            # Performance metrics
            'execution_time_ms',
            'memory_used_mb',
            'time_spent_seconds',

            # Content
            'raw_input',
            'processed_code',

            # Test results summary
            'tests_total',
            'tests_passed',
            'tests_failed',
            'test_details',  # JSON string of detailed results

            # Code variations (for EiPL)
            'variations_count',
            'best_variation_score',
            'variations_summary',  # JSON string of variations

            # Segmentation (for EiPL)
            'segmentation_level',
            'segment_count',
            'segmentation_feedback',

            # Hints
            'hints_activated_count',
            'hints_activated_types',
            'hint_details',  # JSON string of hint activations

            # Aggregate metrics
            'error_types_encountered',
            'avg_test_execution_time_ms',
        ]

        writer = csv.DictWriter(response, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        # Write each submission
        for submission in queryset:
            row = self._build_csv_row(submission)
            writer.writerow(row)

        return response

    def _build_csv_row(self, submission):
        """
        Build a CSV row from a submission instance.
        """
        # Basic info
        row = {
            'submission_id': str(submission.submission_id),
            'user': submission.user.username,
            'problem': submission.problem.title,
            'problem_set': submission.problem_set.title if submission.problem_set else '',
            'course': submission.course.course_id if submission.course else '',
            'submission_type': submission.submission_type,
            'submitted_at': submission.submitted_at.isoformat(),
            'score': submission.score,
            'completion_status': submission.completion_status,
            'execution_status': submission.execution_status,
            'passed_all_tests': submission.passed_all_tests,
            'execution_time_ms': submission.execution_time_ms or 0,
            'memory_used_mb': submission.memory_used_mb or 0,
            'time_spent_seconds': submission.time_spent.total_seconds() if submission.time_spent else 0,
            'raw_input': submission.raw_input,
            'processed_code': submission.processed_code,
        }

        # Test execution details
        test_executions = submission.test_executions.all()
        tests_passed = sum(1 for te in test_executions if te.passed)
        tests_total = len(test_executions)

        row['tests_total'] = tests_total
        row['tests_passed'] = tests_passed
        row['tests_failed'] = tests_total - tests_passed

        # Build detailed test results
        test_details = []
        error_types = set()
        total_test_time = 0
        test_count_with_time = 0

        for te in test_executions:
            test_detail = {
                'test_number': te.execution_order + 1,
                'passed': te.passed,
                'inputs': te.input_values,
                'expected': te.expected_output,
                'actual': te.actual_output,
                'error_type': te.error_type,
                'error_message': te.error_message[:200] if te.error_message else None,
                'execution_time_ms': te.execution_time_ms,
                'is_hidden': te.test_case.is_hidden
            }
            test_details.append(test_detail)

            if te.error_type and te.error_type != 'none':
                error_types.add(te.error_type)

            if te.execution_time_ms:
                total_test_time += te.execution_time_ms
                test_count_with_time += 1

        row['test_details'] = json.dumps(test_details, separators=(',', ':'))
        row['error_types_encountered'] = ','.join(sorted(error_types))
        row['avg_test_execution_time_ms'] = (
            total_test_time / test_count_with_time if test_count_with_time > 0 else 0
        )

        # Code variations (for EiPL)
        if submission.submission_type == 'eipl':
            variations = submission.code_variations.all()
            row['variations_count'] = variations.count()

            if variations:
                best_variation = max(variations, key=lambda v: v.score)
                row['best_variation_score'] = best_variation.score

                variations_summary = []
                for var in variations:
                    variations_summary.append({
                        'index': var.variation_index,
                        'score': var.score,
                        'tests_passed': var.tests_passed,
                        'tests_total': var.tests_total,
                        'is_selected': var.is_selected,
                        'code': var.generated_code
                    })
                row['variations_summary'] = json.dumps(variations_summary, separators=(',', ':'))
            else:
                row['best_variation_score'] = 0
                row['variations_summary'] = '[]'
        else:
            row['variations_count'] = 0
            row['best_variation_score'] = 0
            row['variations_summary'] = '[]'

        # Segmentation analysis
        if hasattr(submission, 'segmentation'):
            seg = submission.segmentation
            row['segmentation_level'] = seg.comprehension_level
            row['segment_count'] = seg.segment_count
            row['segmentation_feedback'] = seg.feedback_message
        else:
            row['segmentation_level'] = ''
            row['segment_count'] = 0
            row['segmentation_feedback'] = ''

        # Hint activations
        hint_activations = submission.hint_activations.all()
        row['hints_activated_count'] = hint_activations.count()

        if hint_activations:
            hint_types = set()
            hint_details = []

            for ha in hint_activations:
                hint_types.add(ha.hint.hint_type)
                hint_details.append({
                    'hint_type': ha.hint.hint_type,
                    'trigger': ha.trigger_type,
                    'order': ha.activation_order,
                    'viewed_seconds': ha.viewed_duration_seconds
                })

            row['hints_activated_types'] = ','.join(sorted(hint_types))
            row['hint_details'] = json.dumps(hint_details, separators=(',', ':'))
        else:
            row['hints_activated_types'] = ''
            row['hint_details'] = '[]'

        return row


class SubmissionDetailAPI(APIView):
    """
    API endpoint for retrieving detailed submission information.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, submission_id):
        """
        Get complete details for a specific submission.
        """
        try:
            # Check if user has permission to view this submission
            submission = Submission.objects.get(submission_id=submission_id)

            # Users can only see their own submissions unless they're staff
            if not request.user.is_staff and submission.user != request.user:
                return Response(
                    {'error': 'You do not have permission to view this submission'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get detailed submission data
            details = SubmissionService.get_submission_details(submission_id)

            # Filter out hidden test cases for non-staff users
            if not request.user.is_staff:
                details['test_results'] = [
                    tr for tr in details['test_results']
                    if not tr.get('is_hidden', False)
                ]

            return Response(details, status=status.HTTP_200_OK)

        except Submission.DoesNotExist:
            return Response(
                {'error': 'Submission not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserSubmissionStatsAPI(APIView):
    """
    API endpoint for user submission statistics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get aggregated submission statistics for the current user.
        """
        problem_slug = request.query_params.get('problem')
        course_id = request.query_params.get('course')

        # Get problem and course if specified
        problem = None
        course = None

        if problem_slug:
            from purplex.problems_app.models import Problem
            try:
                problem = Problem.objects.get(slug=problem_slug)
            except Problem.DoesNotExist:
                return Response(
                    {'error': 'Problem not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        if course_id:
            from purplex.problems_app.models import Course
            try:
                course = Course.objects.get(course_id=course_id)
            except Course.DoesNotExist:
                return Response(
                    {'error': 'Course not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Get statistics
        stats = SubmissionService.get_user_submission_stats(
            user=request.user,
            problem=problem,
            course=course
        )

        return Response(stats, status=status.HTTP_200_OK)