"""
Repository for ProblemSet model data access.
"""

from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.db.models import Count, Prefetch, Q

from purplex.problems_app.models import (
    Course,
    Problem,
    ProblemSet,
    ProblemSetMembership,
)

from .base_repository import BaseRepository


class ProblemSetRepository(BaseRepository):
    """
    Repository for all ProblemSet-related database queries.

    This repository handles all data access for problem sets,
    including problem memberships and relationships.
    """

    model_class = ProblemSet

    @classmethod
    def get_problem_set_by_slug(cls, slug: str) -> Optional[ProblemSet]:
        """Get a problem set by slug."""
        return ProblemSet.objects.filter(slug=slug).first()

    @classmethod
    def get_all_problem_sets(cls) -> List:
        """Get all problem sets with basic metadata."""
        return list(
            ProblemSet.objects.all()
            .select_related("created_by")
            .annotate(problem_count=Count("problems"))
            .order_by("-created_at")
        )

    @classmethod
    def get_active_problem_sets(cls) -> List:
        """Get all active (published) problem sets."""
        return list(
            ProblemSet.objects.filter(is_published=True)
            .select_related("created_by")
            .annotate(problem_count=Count("problems"))
            .order_by("-created_at")
        )

    @classmethod
    def get_all_public_problem_sets(cls) -> List[Dict[str, Any]]:
        """Get all public problem sets as structured data.

        Returns:
            List of dicts with problem set data
        """
        problem_sets = (
            ProblemSet.objects.filter(is_public=True)
            .annotate(problem_count=Count("problems"))
            .order_by("title")
        )

        return [
            {
                "id": ps.id,
                "slug": ps.slug,
                "title": ps.title,
                "description": ps.description,
                "problems_count": ps.problem_count,
                "is_published": ps.is_published,
                "icon_url": ps.icon.url if ps.icon else None,
            }
            for ps in problem_sets
        ]

    @classmethod
    def get_problem_set_with_problems(cls, slug: str) -> Optional[ProblemSet]:
        """Get a problem set with all its problems prefetched and ordered."""
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
    def get_problems_in_set_ordered(cls, problem_set: ProblemSet) -> List:
        """Get all problems in a problem set, ordered by membership order."""
        return list(
            Problem.objects.filter(problem_set_memberships__problem_set=problem_set)
            .select_related("category")
            .order_by("problem_set_memberships__order")
        )

    @classmethod
    def get_problem_sets_containing_problem(cls, problem: Problem) -> List:
        """Get all problem sets that contain a specific problem."""
        return list(
            ProblemSet.objects.filter(problems=problem).distinct().order_by("title")
        )

    @classmethod
    def get_user_created_problem_sets(cls, user: User) -> List:
        """Get all problem sets created by a specific user."""
        return list(
            ProblemSet.objects.filter(created_by=user)
            .annotate(problem_count=Count("problems"))
            .order_by("-created_at")
        )

    @classmethod
    def search_problem_sets(cls, query: str, include_unpublished: bool = False) -> List:
        """Search problem sets by title or description."""
        queryset = ProblemSet.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).select_related("created_by")

        if not include_unpublished:
            queryset = queryset.filter(is_published=True)

        return list(queryset)

    @classmethod
    def get_problem_sets_by_difficulty(cls, difficulty: str) -> List:
        """Get problem sets that contain problems of a specific difficulty."""
        return list(
            ProblemSet.objects.filter(problems__difficulty=difficulty)
            .distinct()
            .select_related("created_by")
        )

    @classmethod
    def get_problem_sets_by_category(cls, category) -> List:
        """Get problem sets that contain problems from a specific category."""
        return list(
            ProblemSet.objects.filter(problems__categories=category)
            .distinct()
            .select_related("created_by")
        )

    @classmethod
    def count_problems_in_set(cls, problem_set: ProblemSet) -> int:
        """Count the number of problems in a problem set."""
        return problem_set.problems.count()

    @classmethod
    def get_problem_set_statistics(cls, problem_set: ProblemSet) -> Dict[str, Any]:
        """Get comprehensive statistics for a problem set."""
        problems = Problem.objects.filter(
            problem_set_memberships__problem_set=problem_set
        )

        stats = {
            "total_problems": problems.count(),
            "difficulty_breakdown": {},
            "category_breakdown": {},
            "total_test_cases": 0,
        }

        # Get difficulty breakdown
        difficulty_counts = problems.values("difficulty").annotate(count=Count("id"))
        for item in difficulty_counts:
            stats["difficulty_breakdown"][item["difficulty"]] = item["count"]

        # Get category breakdown
        category_counts = (
            problems.values("categories__name")
            .annotate(count=Count("id", distinct=True))
            .exclude(categories__name__isnull=True)
        )
        for item in category_counts:
            stats["category_breakdown"][item["categories__name"]] = item["count"]

        # Get total test cases
        stats["total_test_cases"] = sum(
            problem.test_cases.count() for problem in problems
        )

        return stats

    @classmethod
    def get_problem_sets_in_course(cls, course: Course) -> List:
        """Get all problem sets associated with a course."""
        return list(
            ProblemSet.objects.filter(courses=course).order_by(
                "courseproblemset__order"
            )
        )

    @classmethod
    def get_required_problem_sets_in_course(cls, course: Course) -> List:
        """Get required problem sets for a course."""
        return list(
            ProblemSet.objects.filter(
                courses=course, courseproblemset__is_required=True
            ).order_by("courseproblemset__order")
        )

    @classmethod
    def get_optional_problem_sets_in_course(cls, course: Course) -> List:
        """Get optional problem sets for a course."""
        return list(
            ProblemSet.objects.filter(
                courses=course, courseproblemset__is_required=False
            ).order_by("courseproblemset__order")
        )

    @classmethod
    def clone_problem_set(
        cls, original_set: ProblemSet, user: User, new_title: str, new_slug: str
    ) -> ProblemSet:
        """Create a copy of an existing problem set with its problems."""
        # Create new problem set
        new_set = ProblemSet.objects.create(
            title=new_title,
            slug=new_slug,
            description=f"Copy of {original_set.title}",
            created_by=user,
            is_published=False,  # Start as unpublished
        )

        # Copy problem memberships
        memberships = ProblemSetMembership.objects.filter(
            problem_set=original_set
        ).order_by("order")

        for membership in memberships:
            ProblemSetMembership.objects.create(
                problem_set=new_set,
                problem=membership.problem,
                order=membership.order,
                weight=membership.weight,
            )

        return new_set

    @classmethod
    def publish_problem_set(cls, problem_set: ProblemSet) -> bool:
        """Publish a problem set (make it available to students)."""
        try:
            problem_set.is_published = True
            problem_set.save()
            return True
        except Exception:
            return False

    @classmethod
    def unpublish_problem_set(cls, problem_set: ProblemSet) -> bool:
        """Unpublish a problem set (make it unavailable to students)."""
        try:
            problem_set.is_published = False
            problem_set.save()
            return True
        except Exception:
            return False

    @classmethod
    def get_all_titles(cls) -> List[str]:
        """
        Get all unique problem set titles for filter dropdowns.

        Returns:
            List of problem set titles, sorted alphabetically
        """
        return list(
            ProblemSet.objects.values_list("title", flat=True)
            .order_by("title")
            .distinct()
        )
