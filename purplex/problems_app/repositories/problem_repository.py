"""
Repository for Problem and ProblemSet model data access.
"""

from typing import TYPE_CHECKING, Dict, List, Optional

from django.db.models import Count, Prefetch, Q, QuerySet

from purplex.problems_app.models import (
    Problem,
    ProblemCategory,
    ProblemSet,
    ProblemSetMembership,
    TestCase,
)

if TYPE_CHECKING:
    from purplex.problems_app.models import McqProblem

from .base_repository import BaseRepository


class ProblemRepository(BaseRepository):
    """
    Repository for all Problem-related database queries.

    This repository handles all data access for problems,
    problem sets, test cases, and categories.
    """

    model_class = Problem

    @classmethod
    def _with_test_case_counts(cls, queryset: QuerySet) -> QuerySet:
        """Add test case count annotations to avoid N+1 queries.

        Note: Uses _annotated suffix to avoid conflict with model @property methods.
        """
        return queryset.annotate(
            test_cases_count_annotated=Count("test_cases"),
            visible_test_cases_count_annotated=Count(
                "test_cases", filter=Q(test_cases__is_hidden=False)
            ),
        )

    @classmethod
    def get_problem_by_slug(cls, slug: str) -> Optional[Problem]:
        """Get a problem by its slug."""
        return Problem.objects.filter(slug=slug).first()

    @classmethod
    def get_problem_by_id(cls, problem_id: int) -> Optional[Problem]:
        """Get a problem by its ID."""
        return Problem.objects.filter(id=problem_id).first()

    @classmethod
    def get_all_problems(cls) -> List[Problem]:
        """Get all problems with optimizations."""
        queryset = (
            Problem.objects.all()
            .select_related("created_by")
            .prefetch_related("categories")
            .order_by("-created_at")
        )
        return list(cls._with_test_case_counts(queryset))

    @classmethod
    def get_active_problems(cls) -> List[Problem]:
        """Get all active (non-draft) problems."""
        queryset = (
            Problem.objects.filter(is_active=True)
            .select_related("created_by")
            .prefetch_related("categories")
            .order_by("-created_at")
        )
        return list(cls._with_test_case_counts(queryset))

    @classmethod
    def get_problems_by_category(cls, category: ProblemCategory) -> List[Problem]:
        """Get all problems in a specific category."""
        queryset = (
            Problem.objects.filter(categories=category)
            .select_related("created_by")
            .order_by("title")
        )
        return list(cls._with_test_case_counts(queryset))

    @classmethod
    def get_problems_by_difficulty(cls, difficulty: int) -> List[Problem]:
        """Get problems by difficulty level."""
        queryset = (
            Problem.objects.filter(difficulty=difficulty)
            .select_related("created_by")
            .prefetch_related("categories")
            .order_by("title")
        )
        return list(cls._with_test_case_counts(queryset))

    @classmethod
    def search_problems(cls, query: str) -> List[Problem]:
        """Search problems by title or description."""
        queryset = (
            Problem.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query),
                is_active=True,
            )
            .select_related("created_by")
            .prefetch_related("categories")
        )
        return list(cls._with_test_case_counts(queryset))

    @classmethod
    def get_problem_with_test_cases(cls, slug: str) -> Optional[Problem]:
        """Get a problem with all its test cases prefetched."""
        return Problem.objects.prefetch_related("test_cases").filter(slug=slug).first()

    # ProblemSet methods
    @classmethod
    def get_all_problem_sets(cls) -> List[ProblemSet]:
        """Get all problem sets."""
        return list(
            ProblemSet.objects.all()
            .select_related("created_by")
            .annotate(problem_count=Count("problemsetmembership"))
            .order_by("-created_at")
        )

    @classmethod
    def get_problem_set_by_slug(cls, slug: str) -> Optional[ProblemSet]:
        """Get a problem set by slug."""
        return ProblemSet.objects.filter(slug=slug).first()

    @classmethod
    def get_problem_set_by_id(cls, problem_set_id: int) -> Optional[ProblemSet]:
        """Get a problem set by ID."""
        return ProblemSet.objects.filter(id=problem_set_id).first()

    @classmethod
    def get_problem_set_with_problems(cls, slug: str) -> Optional[ProblemSet]:
        """Get a problem set with all its problems prefetched."""
        return (
            ProblemSet.objects.prefetch_related(
                Prefetch(
                    "problemsetmembership_set",
                    queryset=ProblemSetMembership.objects.select_related("problem")
                    .prefetch_related("problem__categories")
                    .order_by("order"),
                )
            )
            .filter(slug=slug)
            .first()
        )

    @classmethod
    def get_problems_in_set(cls, problem_set: ProblemSet) -> List[Problem]:
        """Get all problems in a problem set, ordered."""
        queryset = (
            Problem.objects.filter(problem_set_memberships__problem_set=problem_set)
            .prefetch_related("categories")
            .order_by("problem_set_memberships__order")
        )
        return list(cls._with_test_case_counts(queryset))

    @classmethod
    def problem_in_set(cls, problem: Problem, problem_set: ProblemSet) -> bool:
        """Check if a problem is in a problem set."""
        return ProblemSetMembership.objects.filter(
            problem=problem, problem_set=problem_set
        ).exists()

    # Category methods
    @classmethod
    def get_all_categories(cls) -> List[ProblemCategory]:
        """Get all problem categories."""
        return list(
            ProblemCategory.objects.all()
            .annotate(problem_count=Count("problems"))
            .order_by("name")
        )

    @classmethod
    def create_category(cls, **kwargs) -> ProblemCategory:
        """Create a new category."""
        return ProblemCategory.objects.create(**kwargs)

    @classmethod
    def find_category_by_exact_name(cls, name: str) -> Optional[ProblemCategory]:
        """Find a category by exact name (case-insensitive)."""
        return ProblemCategory.objects.filter(name__iexact=name).first()

    @classmethod
    def get_user_created_problems(cls, user_id: int) -> List[Problem]:
        """Get all problems created by a specific user."""
        queryset = (
            Problem.objects.filter(created_by_id=user_id)
            .prefetch_related("categories")
            .order_by("-created_at")
        )
        return list(cls._with_test_case_counts(queryset))

    @classmethod
    def count_problems_by_difficulty(cls) -> Dict[int, int]:
        """Get count of problems grouped by difficulty."""
        counts = (
            Problem.objects.filter(is_active=True)
            .values("difficulty")
            .annotate(count=Count("id"))
        )
        return {item["difficulty"]: item["count"] for item in counts}

    @classmethod
    def count_problems_in_set(cls, problem_set: ProblemSet) -> int:
        """
        Count the number of problems in a problem set.

        Args:
            problem_set: The problem set to count problems for

        Returns:
            Number of problems in the set
        """
        return problem_set.problems.count()

    @classmethod
    def get_problem_test_case_by_id(
        cls, problem: Problem, test_case_id: int, include_hidden: bool = False
    ) -> Optional[TestCase]:
        """Get a specific test case for a problem by ID."""
        queryset = TestCase.objects.filter(problem=problem, id=test_case_id)
        if not include_hidden:
            queryset = queryset.filter(is_hidden=False)
        return queryset.first()

    @classmethod
    def update_problem(cls, problem: Problem, **kwargs) -> Problem:
        """Update a problem with given fields."""
        for attr, value in kwargs.items():
            setattr(problem, attr, value)
        problem.save()
        return problem

    @staticmethod
    def get_problem_type_choices() -> list:
        """
        Get available problem type choices for the polymorphic hierarchy.

        Returns:
            List of (type_name, display_label) tuples
        """
        return [
            ("mcq", "Multiple Choice Question"),
            ("eipl", "Explain in Plain Language"),
            ("prompt", "Prompt Problem"),
            ("debug_fix", "Debug and Fix Code"),
            ("probeable_code", "Probeable Problem (Code)"),
            ("probeable_spec", "Probeable Problem (Explanation)"),
            ("refute", "Refute: Find Counterexample"),
        ]

    @classmethod
    def create_mcq_problem(cls, **kwargs) -> "McqProblem":
        """
        Create a new MCQ problem.

        Args:
            **kwargs: MCQ problem fields

        Returns:
            Created McqProblem instance
        """
        from purplex.problems_app.models import McqProblem

        return McqProblem.objects.create(**kwargs)

    @classmethod
    def get_mcq_problem_by_pk(cls, pk: int) -> Optional["McqProblem"]:
        """
        Get an MCQ problem by its primary key.

        This is used by handlers to ensure they have the properly-typed
        McqProblem instance when django-polymorphic returns the base Problem type.

        Args:
            pk: Primary key of the problem

        Returns:
            McqProblem instance or None if not found/not MCQ type
        """
        from purplex.problems_app.models import McqProblem

        return McqProblem.objects.filter(pk=pk).first()
