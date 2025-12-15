"""
Repository for ProblemHint model data access.
"""

from typing import Any, Dict, List, Optional

from purplex.problems_app.models import Problem, ProblemHint

from .base_repository import BaseRepository


class HintRepository(BaseRepository):
    """
    Repository for all ProblemHint-related database queries.

    This repository handles all data access for hints,
    including retrieval by type and problem association.
    """

    model_class = ProblemHint

    @classmethod
    def get_problem_hints(cls, problem: Problem) -> List:
        """
        Get all hints for a specific problem.

        Args:
            problem: The problem to get hints for

        Returns:
            QuerySet of hints for the problem
        """
        return list(ProblemHint.objects.filter(problem=problem).order_by("hint_type"))

    @classmethod
    def get_problem_hints_by_type(cls, problem: Problem, hint_type: str) -> List:
        """
        Get hints of a specific type for a problem.

        Args:
            problem: The problem to get hints for
            hint_type: The type of hint (variable_fade, subgoal_hints, suggested_trace)

        Returns:
            QuerySet of hints of the specified type
        """
        return list(ProblemHint.objects.filter(problem=problem, hint_type=hint_type))

    @classmethod
    def get_hint_by_id(cls, hint_id: int) -> Optional[ProblemHint]:
        """Get a specific hint by ID."""
        return ProblemHint.objects.filter(id=hint_id).first()

    @classmethod
    def get_hint_by_problem_and_type(
        cls, problem: Problem, hint_type: str
    ) -> Optional[ProblemHint]:
        """
        Get a single hint by problem and type.

        Args:
            problem: The problem to get hint for
            hint_type: The type of hint

        Returns:
            ProblemHint instance or None if not found
        """
        return ProblemHint.objects.filter(problem=problem, hint_type=hint_type).first()

    @classmethod
    def hint_exists_for_problem(cls, problem: Problem, hint_type: str) -> bool:
        """
        Check if a specific hint type exists for a problem.

        Args:
            problem: The problem to check
            hint_type: The type of hint to check for

        Returns:
            True if hint exists, False otherwise
        """
        return ProblemHint.objects.filter(problem=problem, hint_type=hint_type).exists()

    @classmethod
    def count_hints_for_problem(cls, problem: Problem) -> Dict[str, int]:
        """
        Count hints by type for a problem.

        Args:
            problem: The problem to count hints for

        Returns:
            Dictionary with hint types as keys and counts as values
        """
        hints = (
            ProblemHint.objects.filter(problem=problem).values("hint_type").distinct()
        )
        result = {}
        for hint_type_record in hints:
            hint_type = hint_type_record["hint_type"]
            result[hint_type] = ProblemHint.objects.filter(
                problem=problem, hint_type=hint_type
            ).count()
        return result

    @classmethod
    def get_all_hint_types(cls) -> List[str]:
        """
        Get all unique hint types in the system.

        Returns:
            List of unique hint type strings
        """
        return list(
            ProblemHint.objects.values_list("hint_type", flat=True)
            .distinct()
            .order_by("hint_type")
        )

    @classmethod
    def create_hint(
        cls, problem: Problem, hint_type: str, content: str, **kwargs
    ) -> ProblemHint:
        """
        Create a new hint for a problem.

        Args:
            problem: The problem to create hint for
            hint_type: Type of hint
            content: The hint content
            **kwargs: Additional fields

        Returns:
            Created ProblemHint instance
        """
        return ProblemHint.objects.create(
            problem=problem, hint_type=hint_type, content=content, **kwargs
        )

    @classmethod
    def bulk_create_hints(cls, hints: List[ProblemHint]) -> List[ProblemHint]:
        """
        Bulk create multiple hints.

        Args:
            hints: List of ProblemHint instances to create

        Returns:
            List of created hints
        """
        return list(ProblemHint.objects.bulk_create(hints))

    @classmethod
    def update_hint_content(cls, hint_id: int, content: str) -> bool:
        """
        Update the content of a hint.

        Args:
            hint_id: ID of the hint to update
            content: New content for the hint

        Returns:
            True if updated, False if not found
        """
        updated = ProblemHint.objects.filter(id=hint_id).update(content=content)
        return updated > 0

    @classmethod
    def update_hint(cls, hint: ProblemHint, **kwargs) -> ProblemHint:
        """
        Update a hint with given fields and validate.

        Args:
            hint: ProblemHint instance to update
            **kwargs: Fields to update

        Returns:
            Updated ProblemHint instance
        """
        for attr, value in kwargs.items():
            setattr(hint, attr, value)
        hint.clean()  # Validate the hint content structure
        hint.save()
        return hint

    @classmethod
    def delete_hint(cls, hint_id: int) -> bool:
        """
        Delete a specific hint.

        Args:
            hint_id: ID of the hint to delete

        Returns:
            True if deleted, False if not found
        """
        deleted, _ = ProblemHint.objects.filter(id=hint_id).delete()
        return deleted > 0

    @classmethod
    def delete_problem_hints(
        cls, problem: Problem, hint_type: Optional[str] = None
    ) -> int:
        """
        Delete all hints for a problem, optionally filtered by type.

        Args:
            problem: The problem to delete hints for
            hint_type: Optional hint type to filter deletions

        Returns:
            Number of hints deleted
        """
        queryset = ProblemHint.objects.filter(problem=problem)
        if hint_type:
            queryset = queryset.filter(hint_type=hint_type)
        deleted, _ = queryset.delete()
        return deleted

    @classmethod
    def get_problems_with_hints(cls, hint_type: Optional[str] = None) -> List:
        """
        Get all problems that have hints, optionally filtered by type.

        Args:
            hint_type: Optional hint type to filter by

        Returns:
            QuerySet of problems with hints
        """
        hint_filter = {}
        if hint_type:
            hint_filter["problemhint__hint_type"] = hint_type

        return list(
            Problem.objects.filter(problemhint__isnull=False, **hint_filter).distinct()
        )

    @classmethod
    def get_hint_metadata(cls, hint_id: int) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a hint (custom JSON field if exists).

        Args:
            hint_id: ID of the hint

        Returns:
            Dictionary of metadata or None
        """
        hint = ProblemHint.objects.filter(id=hint_id).first()
        if hint and hasattr(hint, "metadata"):
            return hint.metadata
        return None

    @classmethod
    def update_hint_metadata(cls, hint_id: int, metadata: Dict[str, Any]) -> bool:
        """
        Update the metadata for a hint.

        Args:
            hint_id: ID of the hint
            metadata: New metadata dictionary

        Returns:
            True if updated, False if not found or no metadata field
        """
        hint = ProblemHint.objects.filter(id=hint_id).first()
        if hint and hasattr(hint, "metadata"):
            hint.metadata = metadata
            hint.save(update_fields=["metadata"])
            return True
        return False

    @classmethod
    def get_enabled_hints_for_problem(cls, problem: Problem) -> list:
        """
        Get only enabled hints for a specific problem.

        Args:
            problem: The problem to get enabled hints for

        Returns:
            List of dicts with hint information
        """
        return list(
            ProblemHint.objects.filter(problem=problem, is_enabled=True).values(
                "id", "hint_type", "min_attempts"
            )
        )

    @classmethod
    def get_valid_hint_types(cls) -> List[str]:
        """
        Get list of valid hint type choices.

        Returns:
            List of valid hint type strings
        """
        return [choice[0] for choice in ProblemHint.HINT_TYPE_CHOICES]

    @classmethod
    def get_or_create_hint(
        cls, problem: Problem, hint_type: str, defaults: Dict[str, Any]
    ) -> tuple:
        """
        Get or create a hint for a problem.

        Args:
            problem: The problem
            hint_type: Type of hint
            defaults: Default values if creating

        Returns:
            Tuple of (hint, created) where created is bool
        """
        return ProblemHint.objects.get_or_create(
            problem=problem, hint_type=hint_type, defaults=defaults
        )

    # =========================================================================
    # HINT ACTIVATION QUERIES
    # =========================================================================

    @classmethod
    def get_activations_for_user_problem(
        cls, user, problem, problem_set=None, course=None
    ):
        """
        Get hint activations for a specific user/problem combination.

        Used by hint service to check which hints a user has already seen.

        Args:
            user: User instance
            problem: Problem instance
            problem_set: Optional problem set filter
            course: Optional course filter

        Returns:
            QuerySet of HintActivation instances
        """
        from purplex.submissions.models import HintActivation

        queryset = HintActivation.objects.filter(
            submission__user=user, submission__problem=problem
        )

        if problem_set:
            queryset = queryset.filter(submission__problem_set=problem_set)
        if course:
            queryset = queryset.filter(submission__course=course)

        return queryset

    @classmethod
    def get_activations_for_course_export(cls, course, user_ids: List[int]):
        """
        Get all hint activations for a course, optimized for export.

        Args:
            course: Course instance
            user_ids: List of enrolled user IDs

        Returns:
            QuerySet of HintActivation with related data
        """
        from purplex.submissions.models import HintActivation

        return (
            HintActivation.objects.filter(
                submission__course=course, submission__user_id__in=user_ids
            )
            .select_related("hint", "submission")
            .order_by("submission__user_id", "submission__problem_id", "activated_at")
        )

    @classmethod
    def get_activations_for_research_export(cls, course=None, problem_set=None):
        """
        Get hint activations for research export with all related data.

        Args:
            course: Optional course filter
            problem_set: Optional problem set filter

        Returns:
            QuerySet of HintActivation with related data
        """
        from purplex.submissions.models import HintActivation

        queryset = HintActivation.objects.select_related(
            "submission__user",
            "submission__problem",
            "submission__problem_set",
            "submission__course",
            "hint",
        )

        if course:
            queryset = queryset.filter(submission__course=course)
        if problem_set:
            queryset = queryset.filter(submission__problem_set=problem_set)

        return queryset

    @classmethod
    def get_usage_stats_for_student(cls, course, user):
        """
        Get hint usage statistics for a specific student in a course.

        Args:
            course: Course instance
            user: User instance

        Returns:
            QuerySet with hint type counts
        """
        from django.db.models import Count

        from purplex.submissions.models import HintActivation

        return (
            HintActivation.objects.filter(
                submission__course=course, submission__user=user
            )
            .values("hint__hint_type")
            .annotate(usage_count=Count("id"))
        )
