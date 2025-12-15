"""
Repository for CourseProblemSet model data access.
"""

from typing import Any, Dict, List, Optional

from django.db.models import Max, Q

from purplex.problems_app.models import Course, CourseProblemSet, ProblemSet

from .base_repository import BaseRepository


class CourseProblemSetRepository(BaseRepository):
    """
    Repository for all CourseProblemSet-related database queries.

    This repository handles all data access for course-problem set
    relationships including ordering and versioning.
    """

    model_class = CourseProblemSet

    @classmethod
    def get_by_course_and_problem_set(
        cls, course: Course, problem_set: ProblemSet
    ) -> Optional[CourseProblemSet]:
        """Get a specific course-problem set relationship."""
        return (
            CourseProblemSet.objects.filter(course=course, problem_set=problem_set)
            .select_related("course", "problem_set")
            .first()
        )

    @classmethod
    def get_course_problem_sets_ordered(cls, course: Course) -> List[CourseProblemSet]:
        """Get all problem sets for a course, ordered by their sequence."""
        return list(
            CourseProblemSet.objects.filter(course=course)
            .select_related("problem_set")
            .order_by("order", "added_at")
        )

    @classmethod
    def get_problem_set_courses(cls, problem_set: ProblemSet) -> List[CourseProblemSet]:
        """Get all courses that contain a specific problem set."""
        return list(
            CourseProblemSet.objects.filter(problem_set=problem_set)
            .select_related("course")
            .filter(course__is_active=True, course__is_deleted=False)
            .order_by("course__name")
        )

    @classmethod
    def get_required_problem_sets(cls, course: Course) -> List[CourseProblemSet]:
        """Get all required problem sets for a course."""
        return list(
            CourseProblemSet.objects.filter(course=course, is_required=True)
            .select_related("problem_set")
            .order_by("order")
        )

    @classmethod
    def get_optional_problem_sets(cls, course: Course) -> List[CourseProblemSet]:
        """Get all optional problem sets for a course."""
        return list(
            CourseProblemSet.objects.filter(course=course, is_required=False)
            .select_related("problem_set")
            .order_by("order")
        )

    @classmethod
    def add_problem_set_to_course(
        cls,
        course: Course,
        problem_set: ProblemSet,
        order: int = 0,
        is_required: bool = True,
        problem_set_version: int = 1,
    ) -> CourseProblemSet:
        """Add a problem set to a course with specific ordering and settings."""
        return CourseProblemSet.objects.create(
            course=course,
            problem_set=problem_set,
            order=order,
            is_required=is_required,
            problem_set_version=problem_set_version,
        )

    @classmethod
    def remove_problem_set_from_course(
        cls, course: Course, problem_set: ProblemSet
    ) -> bool:
        """
        Remove a problem set from a course.

        Returns:
            True if removed, False if not found
        """
        deleted, _ = CourseProblemSet.objects.filter(
            course=course, problem_set=problem_set
        ).delete()
        return deleted > 0

    @classmethod
    def update_problem_set_order(
        cls, course: Course, problem_set: ProblemSet, new_order: int
    ) -> bool:
        """Update the order of a problem set in a course."""
        updated = CourseProblemSet.objects.filter(
            course=course, problem_set=problem_set
        ).update(order=new_order)
        return updated > 0

    @classmethod
    def update_problem_set_requirement(
        cls, course: Course, problem_set: ProblemSet, is_required: bool
    ) -> bool:
        """Update whether a problem set is required in a course."""
        updated = CourseProblemSet.objects.filter(
            course=course, problem_set=problem_set
        ).update(is_required=is_required)
        return updated > 0

    @classmethod
    def course_has_problem_set(cls, course: Course, problem_set: ProblemSet) -> bool:
        """Check if a course contains a specific problem set."""
        return CourseProblemSet.objects.filter(
            course=course, problem_set=problem_set
        ).exists()

    @classmethod
    def get_max_order_in_course(cls, course: Course) -> int:
        """Get the maximum order value for problem sets in a course."""
        result = CourseProblemSet.objects.filter(course=course).aggregate(
            max_order=Max("order")
        )
        return result["max_order"] or 0

    @classmethod
    def reorder_problem_sets(
        cls, course: Course, problem_set_orders: List[Dict[str, Any]]
    ) -> bool:
        """
        Bulk update the order of multiple problem sets in a course.

        Args:
            course: The course to update
            problem_set_orders: List of dicts with 'problem_set_id' and 'order' keys

        Returns:
            True if all updates succeeded
        """
        try:
            for item in problem_set_orders:
                CourseProblemSet.objects.filter(
                    course=course, problem_set_id=item["problem_set_id"]
                ).update(order=item["order"])
            return True
        except Exception:
            return False

    @classmethod
    def get_next_order(cls, course: Course) -> int:
        """Get the next available order value for adding a problem set to a course."""
        return cls.get_max_order_in_course(course) + 1

    @classmethod
    def count_problem_sets_in_course(cls, course: Course) -> int:
        """Count the number of problem sets in a course."""
        return CourseProblemSet.objects.filter(course=course).count()

    @classmethod
    def count_required_problem_sets(cls, course: Course) -> int:
        """Count the number of required problem sets in a course."""
        return CourseProblemSet.objects.filter(course=course, is_required=True).count()

    @classmethod
    def get_course_problem_sets_with_stats(
        cls, course: Course
    ) -> List[CourseProblemSet]:
        """Get course problem sets with related statistics."""
        return list(
            CourseProblemSet.objects.filter(course=course)
            .select_related("problem_set")
            .prefetch_related("problem_set__problems")
            .order_by("order")
        )

    @classmethod
    def search_course_problem_sets(
        cls, course: Course, query: str
    ) -> List[CourseProblemSet]:
        """Search problem sets within a course by title or description."""
        return list(
            CourseProblemSet.objects.filter(course=course)
            .select_related("problem_set")
            .filter(
                Q(problem_set__title__icontains=query)
                | Q(problem_set__description__icontains=query)
            )
            .order_by("order")
        )

    @classmethod
    def get_max_order(cls, course: Course) -> int:
        """
        Alias for get_max_order_in_course for compatibility.
        Get the maximum order value for problem sets in a course.
        """
        return cls.get_max_order_in_course(course)

    @classmethod
    def delete_by_filter(cls, **filters) -> tuple:
        """
        Delete records matching the given filter criteria.

        Args:
            **filters: Keyword arguments for filtering

        Returns:
            Tuple of (number deleted, dict of deletions by model)
        """
        return CourseProblemSet.objects.filter(**filters).delete()
