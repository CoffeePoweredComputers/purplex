"""Submission validation service for centralizing submission validation logic."""

from typing import TYPE_CHECKING

from django.utils import timezone

from ..handlers import get_handler, is_registered
from ..models import CourseProblemSet
from ..repositories import CourseRepository, ProblemRepository

# Import models only for type hints
if TYPE_CHECKING:
    from ..models import Course, ProblemSet


class SubmissionValidationService:
    """Service for validating submission requests"""

    @staticmethod
    def validate_submission(data: dict) -> tuple[bool, str | None, dict | None]:
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

        # Check deadline enforcement if submitting to a course with a problem set
        validated_data["is_late"] = False
        if validated_data.get("course") and validated_data.get("problem_set"):
            deadline_result = SubmissionValidationService._check_deadline(
                validated_data["course"], validated_data["problem_set"]
            )
            if not deadline_result["allowed"]:
                return False, deadline_result["error"], None
            validated_data["is_late"] = deadline_result.get("is_late", False)

        validated_data["raw_input"] = raw_input.strip()
        return True, None, validated_data

    @staticmethod
    def _check_deadline(course: "Course", problem_set: "ProblemSet") -> dict:
        """
        Check if submission is allowed based on deadline type.

        Args:
            course: The course being submitted to
            problem_set: The problem set being submitted to

        Returns:
            dict with keys:
                - allowed: bool - whether submission is permitted
                - is_late: bool - whether submission is past due date
                - error: str (optional) - error message if not allowed
        """
        try:
            cps = CourseProblemSet.objects.get(course=course, problem_set=problem_set)
        except CourseProblemSet.DoesNotExist:
            # Problem set not associated with course - allow (other validation handles)
            return {"allowed": True, "is_late": False}

        # No due date or deadline_type is 'none' - always allow
        if not cps.due_date or cps.deadline_type == "none":
            return {"allowed": True, "is_late": False}

        now = timezone.now()
        is_past_due = now > cps.due_date

        if not is_past_due:
            return {"allowed": True, "is_late": False}

        # Past due date - check deadline type
        if cps.deadline_type == "hard":
            formatted_date = cps.due_date.strftime("%B %d, %Y at %I:%M %p")
            return {
                "allowed": False,
                "error": f"Submission deadline has passed. This problem set closed on {formatted_date}.",
                "is_late": True,
            }
        elif cps.deadline_type == "soft":
            return {"allowed": True, "is_late": True}

        return {"allowed": True, "is_late": False}
