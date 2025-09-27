"""
Repository for Submission model operations.
Handles all database queries related to submissions.
"""

from typing import List, Dict, Any, Optional
from django.db.models import Q, QuerySet
from django.db import transaction
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
    def get_by_submission_id(cls, submission_id: str) -> Optional[Submission]:
        """Get a submission by its UUID."""
        try:
            return Submission.objects.select_related(
                'user', 'problem', 'problem_set', 'course'
            ).prefetch_related(
                'test_executions', 'code_variations', 'segmentation'
            ).get(submission_id=submission_id)
        except Submission.DoesNotExist:
            return None

    @classmethod
    def get_filtered_submissions(
        cls,
        search: Optional[str] = None,
        submission_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        course_id: Optional[str] = None,
        problem_set_slug: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[Submission]:
        """
        Get filtered submissions with all necessary related data.

        Args:
            search: Search term for user/problem/submission ID
            submission_type: Filter by submission type
            status_filter: Filter by completion status
            course_id: Filter by course ID
            problem_set_slug: Filter by problem set slug
            start_date: Filter submissions after this date
            end_date: Filter submissions before this date
            user_id: Filter by specific user

        Returns:
            List of filtered Submission objects
        """
        queryset = Submission.objects.select_related(
            'user', 'problem', 'problem_set', 'course'
        ).prefetch_related(
            'test_executions', 'code_variations', 'segmentation'
        )

        # Apply filters
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(problem__title__icontains=search) |
                Q(submission_id__icontains=search)
            )

        if submission_type:
            queryset = queryset.filter(submission_type=submission_type)

        if status_filter:
            queryset = queryset.filter(completion_status=status_filter)

        if course_id:
            queryset = queryset.filter(course__course_id=course_id)

        if problem_set_slug:
            queryset = queryset.filter(problem_set__slug=problem_set_slug)

        if start_date:
            queryset = queryset.filter(submitted_at__gte=start_date)

        if end_date:
            queryset = queryset.filter(submitted_at__lte=end_date)

        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Order by most recent
        queryset = queryset.order_by('-submitted_at')

        return list(queryset)

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
        Export submissions based on filters.

        Args:
            filters: Dictionary of filter criteria

        Returns:
            List of Submission objects for export
        """
        queryset = Submission.objects.select_related(
            'user', 'problem', 'problem_set', 'course'
        ).prefetch_related(
            'hint_activations__hint'
        )

        # Apply filters
        if filters.get('start_date'):
            queryset = queryset.filter(submitted_at__gte=filters['start_date'])

        if filters.get('end_date'):
            queryset = queryset.filter(submitted_at__lte=filters['end_date'])

        if filters.get('course_id'):
            queryset = queryset.filter(course__course_id=filters['course_id'])

        if filters.get('problem_set_slug'):
            queryset = queryset.filter(problem_set__slug=filters['problem_set_slug'])

        if filters.get('user_id'):
            queryset = queryset.filter(user_id=filters['user_id'])

        if filters.get('submission_type'):
            queryset = queryset.filter(submission_type=filters['submission_type'])

        return list(queryset.order_by('-submitted_at'))

    @classmethod
    @transaction.atomic
    def create_submission(
        cls,
        user_id: int,
        problem_id: int,
        problem_set_id: int,
        raw_input: str,
        submission_type: str,
        course_id: Optional[int] = None,
        processed_code: str = "",
        time_spent: Optional[Any] = None
    ) -> Submission:
        """
        Create a new submission with proper transaction handling.

        Args:
            user_id: User making the submission
            problem_id: Problem being submitted
            problem_set_id: Problem set context
            raw_input: Original user input
            submission_type: Type of submission (direct_code, eipl, etc)
            course_id: Optional course context
            processed_code: Final code to execute
            time_spent: Optional time duration

        Returns:
            Created Submission object
        """
        submission = Submission.objects.create(
            user_id=user_id,
            problem_id=problem_id,
            problem_set_id=problem_set_id,
            course_id=course_id,
            raw_input=raw_input,
            processed_code=processed_code,
            submission_type=submission_type,
            time_spent=time_spent
        )
        return submission

    @classmethod
    def get_user_submissions(
        cls,
        user_id: int,
        problem_id: Optional[int] = None,
        course_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Submission]:
        """
        Get submissions for a specific user.

        Args:
            user_id: User ID
            problem_id: Optional filter by problem
            course_id: Optional filter by course
            limit: Maximum number of results

        Returns:
            List of Submission objects
        """
        queryset = Submission.objects.filter(user_id=user_id)

        if problem_id:
            queryset = queryset.filter(problem_id=problem_id)

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return list(
            queryset.select_related(
                'problem', 'problem_set', 'course'
            ).order_by('-submitted_at')[:limit]
        )

    @classmethod
    def get_latest_submission(
        cls,
        user_id: int,
        problem_id: int,
        course_id: Optional[int] = None
    ) -> Optional[Submission]:
        """
        Get the most recent submission for a user-problem combination.

        Args:
            user_id: User ID
            problem_id: Problem ID
            course_id: Optional course context

        Returns:
            Latest Submission object or None
        """
        queryset = Submission.objects.filter(
            user_id=user_id,
            problem_id=problem_id
        )

        if course_id:
            queryset = queryset.filter(course_id=course_id)

        return queryset.select_related(
            'problem', 'problem_set', 'course'
        ).prefetch_related(
            'segmentation'
        ).order_by('-submitted_at').first()

    @classmethod
    def update_submission_status(
        cls,
        submission_id: int,
        execution_status: str,
        score: Optional[int] = None,
        passed_all_tests: Optional[bool] = None,
        execution_time_ms: Optional[int] = None,
        memory_used_mb: Optional[float] = None
    ) -> Optional[Submission]:
        """
        Update submission status after execution.

        Args:
            submission_id: Submission primary key
            execution_status: New execution status
            score: Optional score update
            passed_all_tests: Optional test results
            execution_time_ms: Optional execution time
            memory_used_mb: Optional memory usage

        Returns:
            Updated Submission object or None
        """
        try:
            submission = Submission.objects.get(pk=submission_id)

            submission.execution_status = execution_status

            if score is not None:
                submission.score = score
                # Update completion status based on score
                if score >= 100:
                    submission.completion_status = 'complete'
                elif score > 0:
                    submission.completion_status = 'partial'
                else:
                    submission.completion_status = 'incomplete'

            if passed_all_tests is not None:
                submission.passed_all_tests = passed_all_tests
                submission.is_correct = passed_all_tests

            if execution_time_ms is not None:
                submission.execution_time_ms = execution_time_ms

            if memory_used_mb is not None:
                submission.memory_used_mb = memory_used_mb

            submission.save()
            return submission

        except Submission.DoesNotExist:
            return None