"""
Repository for Submission model operations.
Handles all database queries related to submissions.
"""

from typing import List, Dict, Any
from django.db.models import Q
from django.core.paginator import Paginator
from ..models import Submission
from purplex.problems_app.repositories.base_repository import BaseRepository


class SubmissionRepository(BaseRepository[Submission]):
    """
    Repository for handling all Submission database operations.

    This repository ensures that all database operations for submissions
    go through a consistent interface and follow the repository pattern.
    """

    model_class = Submission

    @classmethod
    def get_paginated_submissions(
        cls,
        page: int = 1,
        page_size: int = 25,
        **filter_kwargs
    ) -> Dict[str, Any]:
        """
        Get paginated submissions with filters.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            **filter_kwargs: Additional filter arguments

        Returns:
            Dict with paginated results and metadata
        """
        # Get filtered queryset
        queryset = Submission.objects.select_related(
            'user', 'problem', 'problem_set', 'course'
        ).prefetch_related(
            'test_executions', 'code_variations', 'segmentation'
        )

        # Apply filters (same as get_filtered_submissions)
        search = filter_kwargs.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(problem__title__icontains=search) |
                Q(submission_id__icontains=search)
            )

        submission_type = filter_kwargs.get('submission_type')
        if submission_type:
            queryset = queryset.filter(submission_type=submission_type)

        status_filter = filter_kwargs.get('status_filter')
        if status_filter:
            queryset = queryset.filter(completion_status=status_filter)

        # Course filter - by course name
        course_filter = filter_kwargs.get('course_filter')
        if course_filter:
            queryset = queryset.filter(course__name=course_filter)

        # Order by most recent
        queryset = queryset.order_by('-submitted_at')

        # Paginate
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return {
            'submissions': list(page_obj.object_list),
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }

    @classmethod
    def export_submissions(
        cls,
        filters: Dict[str, Any]
    ) -> List[Submission]:
        """
        Export submissions based on filters with optimized queries.

        Args:
            filters: Dictionary of filter criteria

        Returns:
            List of Submission objects for export
        """
        from django.db.models import Prefetch, Q
        from purplex.problems_app.models import UserProgress

        # CRITICAL FIX: Prefetch all related data to prevent N+1 queries
        # Note: OuterRef doesn't work in Prefetch - we prefetch all user progress
        # and filter in Python if needed, which is still faster than N+1 queries
        queryset = Submission.objects.select_related(
            'user', 'problem', 'problem_set', 'course'
        ).prefetch_related(
            'hint_activations__hint',
            'test_executions__test_case',
            'code_variations__test_executions__test_case',
            'segmentation',
            # Prefetch all user progress with related objects
            Prefetch(
                'user__userprogress_set',
                queryset=UserProgress.objects.select_related(
                    'problem', 'problem_set', 'course'
                )
            )
        )

        # Apply filters
        # Search filter - matches frontend 'search' parameter
        if filters.get('search'):
            queryset = queryset.filter(
                Q(user__username__icontains=filters['search']) |
                Q(user__email__icontains=filters['search']) |
                Q(problem__title__icontains=filters['search']) |
                Q(submission_id__icontains=filters['search'])
            )

        # Status filter - matches frontend 'status' parameter
        if filters.get('status'):
            queryset = queryset.filter(completion_status=filters['status'])

        # Problem set filter - matches frontend 'problem_set' parameter (by title)
        if filters.get('problem_set'):
            queryset = queryset.filter(problem_set__title=filters['problem_set'])

        # Course filter - matches frontend 'course' parameter (by name)
        if filters.get('course'):
            queryset = queryset.filter(course__name=filters['course'])

        if filters.get('start_date'):
            queryset = queryset.filter(submitted_at__gte=filters['start_date'])

        if filters.get('end_date'):
            queryset = queryset.filter(submitted_at__lte=filters['end_date'])

        if filters.get('course_id'):
            queryset = queryset.filter(course__course_id=filters['course_id'])

        if filters.get('user_id'):
            queryset = queryset.filter(user_id=filters['user_id'])

        if filters.get('submission_type'):
            queryset = queryset.filter(submission_type=filters['submission_type'])

        return list(queryset.order_by('-submitted_at'))




