"""
Repository for Submission model operations.
Handles all database queries related to submissions.
"""

from typing import Any, Dict, List, Optional

from django.core.paginator import Paginator
from django.db.models import Prefetch, Q

from purplex.problems_app.repositories.base_repository import BaseRepository

from ..models import CodeVariation, HintActivation, Submission, SubmissionFeedback


class SubmissionRepository(BaseRepository[Submission]):
    """
    Repository for handling all Submission database operations.

    This repository ensures that all database operations for submissions
    go through a consistent interface and follow the repository pattern.
    """

    model_class = Submission

    @classmethod
    def get_paginated_submissions(
        cls, page: int = 1, page_size: int = 25, **filter_kwargs
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
            "user", "problem", "problem_set", "course"
        ).prefetch_related("test_executions", "code_variations", "segmentation")

        # Apply filters (same as get_filtered_submissions)
        search = filter_kwargs.get("search")
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
                | Q(problem__title__icontains=search)
                | Q(submission_id__icontains=search)
            )

        submission_type = filter_kwargs.get("submission_type")
        if submission_type:
            queryset = queryset.filter(submission_type=submission_type)

        status_filter = filter_kwargs.get("status_filter")
        if status_filter:
            queryset = queryset.filter(completion_status=status_filter)

        # Course filter - by course name
        course_filter = filter_kwargs.get("course_filter")
        if course_filter:
            queryset = queryset.filter(course__name=course_filter)

        # Order by most recent
        queryset = queryset.order_by("-submitted_at")

        # Paginate
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return {
            "submissions": list(page_obj.object_list),
            "total_count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page,
            "page_size": page_size,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }

    @classmethod
    def export_submissions(cls, filters: Dict[str, Any]) -> List[Submission]:
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
            "user", "problem", "problem_set", "course"
        ).prefetch_related(
            "hint_activations__hint",
            "test_executions__test_case",
            "code_variations__test_executions__test_case",
            "segmentation",
            # Prefetch all user progress with related objects
            Prefetch(
                "user__userprogress_set",
                queryset=UserProgress.objects.select_related(
                    "problem", "problem_set", "course"
                ),
            ),
        )

        # Apply filters
        # Search filter - matches frontend 'search' parameter
        if filters.get("search"):
            queryset = queryset.filter(
                Q(user__username__icontains=filters["search"])
                | Q(user__email__icontains=filters["search"])
                | Q(problem__title__icontains=filters["search"])
                | Q(submission_id__icontains=filters["search"])
            )

        # Status filter - matches frontend 'status' parameter
        if filters.get("status"):
            queryset = queryset.filter(completion_status=filters["status"])

        # Problem set filter - matches frontend 'problem_set' parameter (by title)
        if filters.get("problem_set"):
            queryset = queryset.filter(problem_set__title=filters["problem_set"])

        # Course filter - matches frontend 'course' parameter (by name)
        if filters.get("course"):
            queryset = queryset.filter(course__name=filters["course"])

        if filters.get("start_date"):
            queryset = queryset.filter(submitted_at__gte=filters["start_date"])

        if filters.get("end_date"):
            queryset = queryset.filter(submitted_at__lte=filters["end_date"])

        if filters.get("course_id"):
            queryset = queryset.filter(course__course_id=filters["course_id"])

        if filters.get("user_id"):
            queryset = queryset.filter(user_id=filters["user_id"])

        if filters.get("submission_type"):
            queryset = queryset.filter(submission_type=filters["submission_type"])

        return list(queryset.order_by("-submitted_at"))

    @classmethod
    def get_with_details(cls, submission_id: str) -> Optional[Submission]:
        """
        Get a submission with all related data pre-fetched.

        Args:
            submission_id: The submission UUID

        Returns:
            Submission with related data or None
        """
        try:
            return (
                Submission.objects.select_related(
                    "user", "problem", "problem_set", "course", "segmentation"
                )
                .prefetch_related(
                    "test_executions__test_case",
                    "hint_activations__hint",
                    Prefetch(
                        "code_variations",
                        queryset=CodeVariation.objects.prefetch_related(
                            "test_executions__test_case"
                        ),
                    ),
                    Prefetch(
                        "feedback",
                        queryset=SubmissionFeedback.objects.select_related(
                            "provided_by"
                        ).filter(is_visible_to_student=True),
                    ),
                )
                .get(submission_id=submission_id)
            )
        except Submission.DoesNotExist:
            return None

    @classmethod
    def create_hint_activation(
        cls,
        submission: Submission,
        hint_id: int,
        activation_order: int,
        trigger_type: str = "manual",
        viewed_duration_seconds: Optional[int] = None,
    ) -> HintActivation:
        """
        Create a hint activation record for a submission.

        Args:
            submission: The submission
            hint_id: ID of the hint that was activated
            activation_order: Order in which hint was activated
            trigger_type: How the hint was triggered
            viewed_duration_seconds: How long the hint was viewed

        Returns:
            Created HintActivation instance
        """
        return HintActivation.objects.create(
            submission=submission,
            hint_id=hint_id,
            activation_order=activation_order,
            trigger_type=trigger_type,
            viewed_duration_seconds=viewed_duration_seconds,
        )

    @classmethod
    def count_for_problem(cls, problem) -> int:
        """
        Count total submissions for a problem.

        Used by admin service to check before deletion.

        Args:
            problem: Problem instance

        Returns:
            Number of submissions for this problem
        """
        return Submission.objects.filter(problem=problem).count()

    @classmethod
    def get_recent_for_course(cls, course, user_ids: List[int], days: int = 7) -> int:
        """
        Count recent submissions for a course by enrolled students.

        Args:
            course: Course instance
            user_ids: List of enrolled user IDs
            days: Number of days to look back (default 7)

        Returns:
            Count of recent submissions
        """
        from datetime import timedelta

        from django.utils import timezone

        return Submission.objects.filter(
            course=course,
            user_id__in=user_ids,
            submitted_at__gte=timezone.now() - timedelta(days=days),
        ).count()

    @classmethod
    def get_error_stats_for_problem(
        cls, course, problem, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get common error statistics for a problem in a course.

        Args:
            course: Course instance
            problem: Problem instance
            limit: Maximum number of error types to return

        Returns:
            List of dicts with error_type and count
        """
        from django.db.models import Count

        from ..models import TestExecution

        return list(
            TestExecution.objects.filter(
                submission__course=course, submission__problem=problem, passed=False
            )
            .values("error_type")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )

    @classmethod
    def get_for_student_detail(cls, course, user, limit: int = 20):
        """
        Get recent submissions for a student in a course.

        Args:
            course: Course instance
            user: User instance
            limit: Maximum submissions to return

        Returns:
            QuerySet of recent Submission instances
        """
        return (
            Submission.objects.filter(course=course, user=user)
            .select_related("problem_set", "problem")
            .order_by("-submitted_at")[:limit]
        )

    @classmethod
    def get_for_research_export(
        cls, course=None, problem_set=None, start_date=None, end_date=None
    ):
        """
        Get submissions for research export with all related data.

        Args:
            course: Optional course filter
            problem_set: Optional problem set filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            QuerySet of Submission with related data
        """
        queryset = Submission.objects.select_related(
            "user", "problem", "problem_set", "course", "segmentation"
        ).prefetch_related(
            "test_executions__test_case",
            "hint_activations__hint",
            "code_variations",
        )

        if course:
            queryset = queryset.filter(course=course)
        if problem_set:
            queryset = queryset.filter(problem_set=problem_set)
        if start_date:
            queryset = queryset.filter(submitted_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(submitted_at__lte=end_date)

        return queryset

    @classmethod
    def get_latest_per_problem_in_set(cls, user, problem_set, course=None):
        """
        Get latest submissions per problem for a user in a problem set.

        Uses PostgreSQL DISTINCT ON to get one submission per problem.

        Args:
            user: User instance
            problem_set: ProblemSet instance
            course: Optional course filter

        Returns:
            QuerySet of Submission with segmentation prefetched
        """
        queryset = Submission.objects.filter(user=user, problem_set=problem_set)

        if course:
            queryset = queryset.filter(course=course)

        return (
            queryset.prefetch_related("segmentation")
            .order_by("problem__id", "-submitted_at")
            .distinct("problem__id")
        )

    @classmethod
    def get_latest_with_variations(cls, user, problem, problem_set=None, course=None):
        """
        Get latest submission with all variation data prefetched.

        Args:
            user: User instance
            problem: Problem instance
            problem_set: Optional problem set filter
            course: Optional course filter

        Returns:
            Submission with related data or None
        """
        filters = {"user": user, "problem": problem}

        if problem_set:
            filters["problem_set"] = problem_set
        if course:
            filters["course"] = course

        return (
            Submission.objects.filter(**filters)
            .prefetch_related(
                "test_executions__test_case",
                "code_variations__test_executions__test_case",
                "segmentation",
            )
            .order_by("-submitted_at")
            .first()
        )

    @classmethod
    def get_user_submission_history(
        cls, user, problem, problem_set=None, course=None, limit: int = 10
    ):
        """
        Get submission history for a user on a specific problem.

        Used by submission views for displaying submission history.
        NOTE: 'problem' is intentionally excluded from select_related
        to allow django-polymorphic to resolve the correct subclass.

        Args:
            user: User instance
            problem: Problem instance
            problem_set: Optional problem set filter
            course: Optional course filter
            limit: Maximum submissions to return

        Returns:
            List of Submission instances with related data prefetched
        """
        filters = {"user": user, "problem": problem}

        if problem_set:
            filters["problem_set"] = problem_set
        if course:
            filters["course"] = course

        return list(
            Submission.objects.filter(**filters)
            .select_related("problem_set", "course", "segmentation")
            .prefetch_related("code_variations", "test_executions")
            .order_by("-submitted_at")[:limit]
        )
