"""
Service layer for instructor content management.
Handles ownership-scoped CRUD operations for problems, problem sets, and courses.
"""

from django.contrib.auth.models import User

from ..models import Course, Problem, ProblemSet
from ..repositories import CourseRepository, ProblemRepository, ProblemSetRepository
from .admin_service import AdminProblemService


class InstructorContentService:
    """Handle instructor-specific content management operations."""

    # === PROBLEMS ===

    @staticmethod
    def get_instructor_problems(user: User) -> list:
        """Get all problems created by this instructor."""
        return ProblemRepository.get_by_creator(user.id)

    @staticmethod
    def get_instructor_problem(user: User, slug: str) -> Problem | None:
        """Get a problem only if owned by instructor."""
        problem = ProblemRepository.get_problem_by_slug(slug)
        if problem and problem.created_by_id == user.id:
            return problem
        return None

    @staticmethod
    def create_problem(user: User, data: dict) -> Problem:
        """Create a problem with user as creator."""
        data["created_by"] = user
        return AdminProblemService.create_problem(data)

    @staticmethod
    def update_instructor_problem(user: User, slug: str, data: dict) -> Problem | None:
        """Update a problem only if owned by instructor."""
        problem = InstructorContentService.get_instructor_problem(user, slug)
        if not problem:
            return None
        return AdminProblemService.update_problem(problem, data)

    @staticmethod
    def delete_instructor_problem(user: User, slug: str) -> dict:
        """Delete a problem only if owned by instructor."""
        problem = InstructorContentService.get_instructor_problem(user, slug)
        if not problem:
            return {"success": False, "error": "Problem not found or not owned by you"}
        return AdminProblemService.delete_problem(problem)

    # === PROBLEM SETS ===

    @staticmethod
    def get_instructor_problem_sets(user: User) -> list:
        """Get all problem sets created by this instructor."""
        return ProblemSetRepository.get_by_creator(user.id)

    @staticmethod
    def get_instructor_problem_set(user: User, slug: str) -> ProblemSet | None:
        """Get a problem set only if owned by instructor."""
        ps = ProblemSetRepository.get_by_slug(slug)
        if ps and ps.created_by_id == user.id:
            return ps
        return None

    @staticmethod
    def create_problem_set(user: User, data: dict) -> ProblemSet:
        """Create a problem set with user as creator."""
        data["created_by"] = user
        return ProblemSetRepository.create(**data)

    # === COURSES ===

    @staticmethod
    def create_course(user: User, data: dict) -> Course:
        """Create a course with user as instructor/owner."""
        # Remove instructor_id if present (frontend may send null for non-admins)
        data.pop("instructor_id", None)
        data["instructor"] = user
        return CourseRepository.create(**data)

    @staticmethod
    def can_manage_course(user: User, course: Course) -> bool:
        """Check if user owns the course."""
        return course.instructor_id == user.id or (
            hasattr(user, "profile") and user.profile.role == "admin"
        )
