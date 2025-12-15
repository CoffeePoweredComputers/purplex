"""Submission validation service for centralizing submission validation logic."""

from typing import TYPE_CHECKING, Optional, Tuple

from ..handlers import get_handler, is_registered
from ..repositories import CourseRepository, ProblemRepository

# Import models only for type hints
if TYPE_CHECKING:
    pass


class SubmissionValidationService:
    """Service for validating submission requests"""

    @staticmethod
    def validate_submission(data: dict) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Generic submission validation that delegates type-specific validation to handlers.

        Args:
            data: Request data dictionary containing:
                - problem_slug (required)
                - raw_input (required) - the user's submission content
                - problem_set_slug (optional)
                - course_id (optional)

        Returns:
            Tuple[bool, Optional[str], Optional[dict]]:
            (is_valid, error_message, validated_data)
        """
        validated_data = {}

        # Extract common required fields
        problem_slug = data.get("problem_slug")
        raw_input = data.get(
            "raw_input", data.get("user_prompt", "")
        )  # Support both field names
        problem_set_slug = data.get("problem_set_slug")
        course_id = data.get("course_id")

        # Validate required problem_slug
        if not problem_slug:
            return False, "problem_slug is required", None

        # Validate problem exists and is active
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem or not problem.is_active:
            return False, "Problem not found", None
        validated_data["problem"] = problem

        # Delegate type-specific input validation to handler
        if is_registered(problem.problem_type):
            handler = get_handler(problem.problem_type)
            validation_result = handler.validate_input(raw_input, problem)
            if not validation_result.is_valid:
                return False, validation_result.error, None
        else:
            # Fallback for unregistered types - basic non-empty check
            if not raw_input or not raw_input.strip():
                return False, "Submission input is required", None

        # Validate optional problem set
        if problem_set_slug:
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                return False, "Problem set not found", None
            validated_data["problem_set"] = problem_set

        # Validate optional course
        if course_id:
            course = CourseRepository.get_active_course(course_id)
            if not course:
                return False, "Course not found", None
            validated_data["course"] = course

        validated_data["raw_input"] = raw_input.strip()
        return True, None, validated_data
