"""
Repository for Course model data access.
"""

from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.db.models import Count, Q

from purplex.problems_app.models import Course, CourseEnrollment, CourseProblemSet

from .base_repository import BaseRepository


class CourseRepository(BaseRepository):
    """
    Repository for all Course-related database queries.

    This repository handles all data access for courses,
    enrollments, and course-problem set relationships.
    """

    model_class = Course

    @classmethod
    def get_active_course(cls, course_id: str) -> Optional[Course]:
        """
        Get an active, non-deleted course by course_id (case-insensitive).

        Args:
            course_id: The user-defined course ID (e.g., CS101-FALL2024)

        Returns:
            Course instance or None if not found
        """
        return Course.objects.filter(
            course_id__iexact=course_id, is_active=True, is_deleted=False
        ).first()

    @classmethod
    def get_course_by_slug(cls, slug: str) -> Optional[Course]:
        """Get a course by slug."""
        return Course.objects.filter(slug=slug, is_deleted=False).first()

    @classmethod
    def get_course_by_id(cls, course_id: str) -> Optional[Course]:
        """Get a course by its course_id field (case-insensitive)."""
        return Course.objects.filter(course_id__iexact=course_id).first()

    @classmethod
    def get_course_by_pk(cls, pk: int) -> Optional[Course]:
        """Get a course by its primary key (integer ID)."""
        return Course.objects.filter(pk=pk, is_deleted=False).first()

    @classmethod
    def get_course_by_enrollment_code(cls, code: str) -> Optional[Course]:
        """Get a course by its enrollment code."""
        return Course.objects.filter(
            enrollment_code=code, is_active=True, is_deleted=False
        ).first()

    @classmethod
    def course_exists(cls, course_id: str) -> bool:
        """Check if a course exists by course_id (case-insensitive)."""
        return Course.objects.filter(course_id__iexact=course_id).exists()

    @classmethod
    def get_course_problem_set_ids(cls, course: Course) -> List[int]:
        """Get list of problem set IDs for a course."""
        return list(course.problem_sets.values_list("id", flat=True))

    @classmethod
    def get_all_courses_with_stats(cls):
        """Get all courses with statistics for admin view.

        Returns:
            QuerySet of Course objects annotated with:
            - problem_sets_count: number of problem sets
            - enrolled_students_count: active enrollments
        """
        return (
            Course.objects.select_related("instructor")
            .annotate(
                problem_sets_count=Count("problem_sets"),
                enrolled_students_count=Count(
                    "enrollments", filter=Q(enrollments__is_active=True)
                ),
            )
            .order_by("-created_at")
        )

    @classmethod
    def get_active_courses_with_stats(cls):
        """Get only active courses with statistics.

        Returns:
            QuerySet of active Course objects annotated with:
            - problem_sets_count: number of problem sets
            - enrolled_students_count: active enrollments
        """
        return (
            Course.objects.filter(is_active=True, is_deleted=False)
            .select_related("instructor")
            .annotate(
                problem_sets_count=Count("problem_sets"),
                enrolled_students_count=Count(
                    "enrollments", filter=Q(enrollments__is_active=True)
                ),
            )
            .order_by("-created_at")
        )

    @classmethod
    def get_instructor_courses_with_stats(
        cls, instructor_id: int
    ) -> List[Dict[str, Any]]:
        """Get all courses for an instructor with statistics.

        Args:
            instructor_id: ID of the instructor

        Returns:
            List of dicts with course data and statistics
        """
        courses = (
            Course.objects.filter(instructor_id=instructor_id, is_deleted=False)
            .annotate(
                problem_sets_count=Count("problem_sets"),
                enrolled_students_count=Count(
                    "enrollments", filter=Q(enrollments__is_active=True)
                ),
            )
            .order_by("-created_at")
        )

        return [
            {
                "id": c.id,
                "course_id": c.course_id,
                "name": c.name,
                "description": c.description,
                "is_active": c.is_active,
                "enrollment_open": c.enrollment_open,
                "problem_sets_count": c.problem_sets_count,
                "enrolled_students_count": c.enrolled_students_count,
                "created_at": c.created_at,
            }
            for c in courses
        ]

    @classmethod
    def get_user_enrolled_courses_with_data(cls, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all courses a user is enrolled in with full data.

        Args:
            user_id: ID of the user

        Returns:
            List of dicts with course and enrollment data
        """
        enrollments = (
            CourseEnrollment.objects.filter(
                user_id=user_id,
                is_active=True,
                course__is_active=True,
                course__is_deleted=False,
            )
            .select_related("course__instructor")
            .prefetch_related("course__courseproblemset_set__problem_set__problems")
            .order_by("-enrolled_at")
        )

        result = []
        for enrollment in enrollments:
            course = enrollment.course
            course_problem_sets = []

            for cps in course.courseproblemset_set.all():
                ps = cps.problem_set
                course_problem_sets.append(
                    {
                        "problem_set_id": ps.id,
                        "problem_set_slug": ps.slug,
                        "problem_set_title": ps.title,
                        "problem_set_description": ps.description,
                        "order": cps.order,
                        "is_required": cps.is_required,
                        "total_problems": ps.problems.count(),
                    }
                )

            result.append(
                {
                    "course": {
                        "id": course.id,
                        "course_id": course.course_id,
                        "name": course.name,
                        "description": course.description,
                        "instructor_name": course.instructor.get_full_name()
                        or course.instructor.username,
                    },
                    "enrolled_at": enrollment.enrolled_at,
                    "problem_sets": course_problem_sets,
                }
            )

        return result

    @classmethod
    def user_is_enrolled(cls, user: User, course: Course) -> bool:
        """
        Check if a user is enrolled in a specific course.

        Args:
            user: The user to check
            course: The course to check enrollment in

        Returns:
            True if user is enrolled, False otherwise
        """
        return CourseEnrollment.objects.filter(
            user=user, course=course, is_active=True
        ).exists()

    @classmethod
    def get_enrollment(cls, user: User, course: Course) -> Optional[CourseEnrollment]:
        """Get a specific enrollment record."""
        return CourseEnrollment.objects.filter(
            user=user, course=course, is_active=True
        ).first()

    @classmethod
    def get_course_enrollments_with_users(cls, course_id: int) -> List[Dict[str, Any]]:
        """Get all active enrollments for a course with user data.

        Args:
            course_id: ID of the course

        Returns:
            List of dicts with enrollment and user data
        """
        enrollments = (
            CourseEnrollment.objects.filter(course_id=course_id, is_active=True)
            .select_related("user")
            .order_by("-enrolled_at")
        )

        return [
            {
                "enrollment_id": e.id,
                "enrolled_at": e.enrolled_at,
                "user": {
                    "id": e.user.id,
                    "username": e.user.username,
                    "email": e.user.email,
                    "first_name": e.user.first_name,
                    "last_name": e.user.last_name,
                    "full_name": e.user.get_full_name(),
                },
            }
            for e in enrollments
        ]

    @classmethod
    def get_enrollment_count(cls, course: Course) -> int:
        """Get the count of active enrollments for a course."""
        return CourseEnrollment.objects.filter(course=course, is_active=True).count()

    @classmethod
    def create_enrollment(
        cls, user: User, course: Course, **kwargs
    ) -> CourseEnrollment:
        """Create a new enrollment."""
        return CourseEnrollment.objects.create(user=user, course=course, **kwargs)

    @classmethod
    def update_or_create_enrollment(
        cls, user: User, course: Course, defaults: dict
    ) -> tuple:
        """Update or create an enrollment."""
        return CourseEnrollment.objects.update_or_create(
            user=user, course=course, defaults=defaults
        )

    @classmethod
    def deactivate_enrollment(cls, user: User, course: Course) -> bool:
        """
        Deactivate a user's enrollment in a course.

        Returns:
            True if enrollment was deactivated, False if not found
        """
        updated = CourseEnrollment.objects.filter(
            user=user, course=course, is_active=True
        ).update(is_active=False)
        return updated > 0

    @classmethod
    def get_course_problem_sets_with_data(cls, course_id: int) -> List[Dict[str, Any]]:
        """Get all problem sets for a course with full data.

        Args:
            course_id: ID of the course

        Returns:
            List of dicts with problem set data and metadata
        """
        course_problem_sets = (
            CourseProblemSet.objects.filter(course_id=course_id)
            .select_related("problem_set")
            .prefetch_related("problem_set__problems")
            .order_by("order")
        )

        return [
            {
                "course_problem_set_id": cps.id,
                "order": cps.order,
                "is_required": cps.is_required,
                "problem_set": {
                    "id": cps.problem_set.id,
                    "slug": cps.problem_set.slug,
                    "title": cps.problem_set.title,
                    "description": cps.problem_set.description,
                    "icon_url": (
                        cps.problem_set.icon.url if cps.problem_set.icon else None
                    ),
                    "problems_count": cps.problem_set.problems.count(),
                    "is_public": cps.problem_set.is_public,
                },
            }
            for cps in course_problem_sets
        ]

    @classmethod
    def get_course_problem_set(
        cls, course: Course, problem_set_slug: str
    ) -> Optional[CourseProblemSet]:
        """Get a specific course-problem set relationship."""
        return (
            CourseProblemSet.objects.filter(
                course=course, problem_set__slug=problem_set_slug
            )
            .select_related("problem_set")
            .first()
        )

    @classmethod
    def add_problem_set_to_course(
        cls, course: Course, problem_set, order: int = 0
    ) -> CourseProblemSet:
        """Add a problem set to a course."""
        return CourseProblemSet.objects.create(
            course=course, problem_set=problem_set, order=order
        )

    @classmethod
    def remove_problem_set_from_course(cls, course: Course, problem_set) -> bool:
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
        cls, course: Course, problem_set, new_order: int
    ) -> bool:
        """Update the order of a problem set in a course."""
        updated = CourseProblemSet.objects.filter(
            course=course, problem_set=problem_set
        ).update(order=new_order)
        return updated > 0

    @classmethod
    def course_has_problem_set(cls, course: Course, problem_set) -> bool:
        """Check if a course contains a specific problem set."""
        return CourseProblemSet.objects.filter(
            course=course, problem_set=problem_set
        ).exists()

    @classmethod
    def get_courses_containing_problem_set(
        cls, problem_set_id: int
    ) -> List[Dict[str, Any]]:
        """Get all courses that contain a specific problem set.

        Args:
            problem_set_id: ID of the problem set

        Returns:
            List of dicts with course data
        """
        courses = (
            Course.objects.filter(
                course_problem_sets__problem_set_id=problem_set_id,
                is_active=True,
                is_deleted=False,
            )
            .distinct()
            .select_related("instructor")
        )

        return [
            {
                "id": c.id,
                "course_id": c.course_id,
                "name": c.name,
                "instructor_name": c.instructor.get_full_name()
                or c.instructor.username,
            }
            for c in courses
        ]

    @classmethod
    def get_unassigned_problem_sets_for_course(
        cls, course_id: str
    ) -> List[Dict[str, Any]]:
        """Get problem sets not yet assigned to a course.

        Args:
            course_id: Course identifier

        Returns:
            List of dicts with available problem set data
        """
        from ..models import ProblemSet

        # Get assigned problem set IDs (case-insensitive course_id match)
        assigned_ids = CourseProblemSet.objects.filter(
            course__course_id__iexact=course_id
        ).values_list("problem_set_id", flat=True)

        # Get available problem sets
        problem_sets = (
            ProblemSet.objects.filter(is_public=True)
            .exclude(id__in=assigned_ids)
            .order_by("title")
        )

        return [
            {
                "id": ps.id,
                "slug": ps.slug,
                "title": ps.title,
                "description": ps.description,
                "problems_count": ps.problems.count(),
            }
            for ps in problem_sets
        ]

    @classmethod
    def search_courses(cls, query: str) -> List[Dict[str, Any]]:
        """Search for courses by name, description, or course_id.

        Args:
            query: Search query string

        Returns:
            List of dicts with matching course data
        """
        courses = Course.objects.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(course_id__icontains=query),
            is_active=True,
            is_deleted=False,
        ).select_related("instructor")

        return [
            {
                "id": c.id,
                "course_id": c.course_id,
                "name": c.name,
                "description": c.description,
                "instructor_name": c.instructor.get_full_name()
                or c.instructor.username,
                "enrollment_open": c.enrollment_open,
            }
            for c in courses
        ]

    @classmethod
    def get_all_names(cls) -> List[str]:
        """
        Get all unique course names for filter dropdowns.

        Returns:
            List of course names, sorted alphabetically
        """
        return list(
            Course.objects.values_list("name", flat=True).order_by("name").distinct()
        )
