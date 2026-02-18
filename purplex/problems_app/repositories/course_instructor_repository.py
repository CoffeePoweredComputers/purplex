"""Repository for CourseInstructor model data access."""

from typing import Any

from django.contrib.auth.models import User

from purplex.problems_app.models import Course, CourseInstructor

from .base_repository import BaseRepository


class CourseInstructorRepository(BaseRepository):
    """Repository for all CourseInstructor-related database queries."""

    model_class = CourseInstructor

    @classmethod
    def get_course_instructors(
        cls, course: Course, role: str | None = None
    ) -> list[CourseInstructor]:
        """Get all instructors for a course, optionally filtered by role."""
        qs = CourseInstructor.objects.filter(course=course).select_related(
            "user", "added_by"
        )
        if role:
            qs = qs.filter(role=role)
        return list(qs.order_by("role", "added_at"))

    @classmethod
    def is_course_instructor(cls, user: User, course: Course) -> bool:
        """Check if user has any instructor role on this course."""
        return CourseInstructor.objects.filter(course=course, user=user).exists()

    @classmethod
    def get_role(cls, user: User, course: Course) -> str | None:
        """Get the user's role on a course, or None if not an instructor."""
        ci = CourseInstructor.objects.filter(course=course, user=user).first()
        return ci.role if ci else None

    @classmethod
    def add_instructor(
        cls,
        course: Course,
        user: User,
        role: str = "primary",
        added_by: User | None = None,
    ) -> CourseInstructor:
        """Add an instructor to a course."""
        return CourseInstructor.objects.create(
            course=course, user=user, role=role, added_by=added_by
        )

    @classmethod
    def remove_instructor(cls, course: Course, user: User) -> bool:
        """Remove an instructor from a course.

        Returns True if removed, False if not found.
        Raises ValueError if trying to remove the last primary instructor.
        """
        ci = CourseInstructor.objects.filter(course=course, user=user).first()
        if not ci:
            return False

        # Prevent removing the last primary instructor
        if ci.role == "primary":
            primary_count = CourseInstructor.objects.filter(
                course=course, role="primary"
            ).count()
            if primary_count <= 1:
                raise ValueError(
                    "Cannot remove the last primary instructor from a course"
                )

        ci.delete()
        return True

    @classmethod
    def update_role(
        cls, course: Course, user: User, new_role: str
    ) -> CourseInstructor | None:
        """Update an instructor's role on a course.

        Raises ValueError if demoting the last primary instructor.
        """
        ci = CourseInstructor.objects.filter(course=course, user=user).first()
        if not ci:
            return None

        # Prevent demoting the last primary
        if ci.role == "primary" and new_role != "primary":
            primary_count = CourseInstructor.objects.filter(
                course=course, role="primary"
            ).count()
            if primary_count <= 1:
                raise ValueError("Cannot demote the last primary instructor")

        ci.role = new_role
        ci.save()
        return ci

    @classmethod
    def get_courses_for_user(
        cls, user_id: int, role: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all courses where a user is an instructor.

        Returns list of dicts with course_id and role.
        """
        qs = CourseInstructor.objects.filter(
            user_id=user_id, course__is_deleted=False
        ).select_related("course")
        if role:
            qs = qs.filter(role=role)
        return list(
            qs.values(
                "course_id",
                "course__course_id",
                "course__name",
                "role",
            )
        )

    @classmethod
    def get_primary_instructor_names(cls, course: Course) -> str:
        """Get comma-joined names of primary instructors."""
        primaries = (
            CourseInstructor.objects.filter(course=course, role="primary")
            .select_related("user")
            .order_by("added_at")
        )
        names = []
        for ci in primaries:
            name = ci.user.get_full_name() or ci.user.username
            names.append(name)
        return ", ".join(names) if names else ""
