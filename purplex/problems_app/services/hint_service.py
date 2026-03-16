"""Service layer for hint-related business logic."""

import logging
from typing import TYPE_CHECKING, Any

from django.http import Http404

from ..models import ProblemHint
from ..repositories import (
    CourseRepository,
    HintRepository,
    ProblemRepository,
    ProgressRepository,
)

# Import models only for type hints
if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class HintService:
    """Handle all hint-related business logic."""

    @staticmethod
    def get_hint_availability(
        user,
        problem_slug: str,
        course_id: str | None = None,
        problem_set_slug: str | None = None,
    ) -> dict[str, Any]:
        """
        Check hint availability for a user on a specific problem.

        Args:
            user: User instance
            problem_slug: Problem slug
            course_id: Optional course ID for context
            problem_set_slug: Optional problem set slug for context

        Returns:
            Dictionary with hint availability information
        """
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            raise Http404("Problem not found")

        # Get optional context
        problem_set = None
        course = None

        if problem_set_slug:
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                raise Http404("Problem set not found")

        if course_id:
            course = CourseRepository.get_active_course(course_id)
            if not course:
                raise Http404("Course not found")

        # Get user progress with context using ID-based method
        progress = ProgressRepository.get_by_ids(
            user_id=user.id,
            problem_id=problem.id,
            problem_set_id=problem_set.id if problem_set else None,
            course_id=course.id if course else None,
        )

        attempts = progress.attempts if progress else 0

        # Get only enabled hints for the problem
        hints = HintRepository.get_enabled_hints_for_problem(problem)

        # Build availability response
        availability = {
            "problem_slug": problem_slug,
            "user_attempts": attempts,
            "hints": [],
        }

        for hint in hints:
            hint_info = {
                "id": hint["id"],
                "type": hint["hint_type"],
                "min_attempts": hint["min_attempts"],
                "available": attempts >= hint["min_attempts"],
                "attempts_needed": max(0, hint["min_attempts"] - attempts),
            }
            availability["hints"].append(hint_info)

        # Sort by hint type
        availability["hints"].sort(key=lambda x: x["type"])

        return availability

    @staticmethod
    def get_used_hints(
        user,
        problem_slug: str,
        course_id: str | None = None,
        problem_set_slug: str | None = None,
    ) -> list[str]:
        """
        Get list of hint types the user has already activated for this problem.

        Args:
            user: User instance
            problem_slug: Problem slug
            course_id: Optional course ID for context
            problem_set_slug: Optional problem set slug for context

        Returns:
            List of hint type strings (e.g., ['variable_fade', 'subgoal_highlight'])
        """
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            return []

        # Get optional context
        problem_set = None
        course = None

        if problem_set_slug:
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)

        if course_id:
            course = CourseRepository.get_active_course(course_id)

        # Query hint activations for this user/problem/context via repository
        activations_query = (
            HintRepository.get_activations_for_user_problem(
                user=user, problem=problem, problem_set=problem_set, course=course
            )
            .select_related("hint")
            .order_by("activated_at")
        )

        # Build list of unique hint types that were used
        used_hint_types = []
        seen_hint_types = set()

        for activation in activations_query:
            hint_type = activation.hint.hint_type
            if hint_type not in seen_hint_types:
                seen_hint_types.add(hint_type)
                used_hint_types.append(hint_type)

        return used_hint_types

    @staticmethod
    def get_hint_content(
        user,
        problem_slug: str,
        hint_type: str,
        course_id: str | None = None,
        problem_set_slug: str | None = None,
    ) -> dict[str, Any]:
        """
        Get specific hint content if user has access.

        Args:
            user: User instance
            problem_slug: Problem slug
            hint_type: Type of hint requested
            course_id: Optional course ID for context
            problem_set_slug: Optional problem set slug for context

        Returns:
            Dictionary with hint content or error information
        """
        # Get the problem
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem or not problem.is_active:
            return {"error": "not_found", "message": "Problem not found"}

        # Validate hint type
        valid_hint_types = HintRepository.get_valid_hint_types()
        if hint_type not in valid_hint_types:
            return {
                "error": "invalid_type",
                "message": f"Invalid hint type. Must be one of: {', '.join(valid_hint_types)}",
            }

        # Validate course and problem set if provided
        course = None
        problem_set = None

        if problem_set_slug:
            problem_set = ProblemRepository.get_problem_set_by_slug(problem_set_slug)
            if not problem_set:
                return {"error": "not_found", "message": "Problem set not found"}
            if not ProblemRepository.problem_in_set(problem, problem_set):
                return {
                    "error": "invalid_context",
                    "message": "Problem does not belong to the specified problem set",
                }

        if course_id:
            course = CourseRepository.get_active_course(course_id)
            if not course:
                return {"error": "not_found", "message": "Course not found"}
            if not CourseRepository.user_is_enrolled(user, course):
                return {
                    "error": "forbidden",
                    "message": "You are not enrolled in this course",
                }

        # Get the hint
        hints = HintRepository.get_problem_hints_by_type(problem, hint_type)
        hint = hints[0] if hints else None
        if not hint:
            return {"error": "not_found", "message": "Hint not found for this problem"}

        # Check if hint is enabled
        if not hint.is_enabled:
            return {"error": "disabled", "message": "This hint is not enabled"}

        # Get user attempts with context using ID-based method
        progress = ProgressRepository.get_by_ids(
            user_id=user.id,
            problem_id=problem.id,
            problem_set_id=problem_set.id if problem_set else None,
            course_id=course.id if course else None,
        )
        user_attempts = progress.attempts if progress else 0

        # Check if user has enough attempts
        if user_attempts < hint.min_attempts:
            return {
                "error": "insufficient_attempts",
                "message": f"You need {hint.min_attempts - user_attempts} more attempts before this hint is available",
                "attempts_needed": hint.min_attempts - user_attempts,
                "current_attempts": user_attempts,
                "min_attempts": hint.min_attempts,
            }

        # Return hint content
        return {
            "type": hint.hint_type,
            "content": hint.content,
            "min_attempts": hint.min_attempts,
            "success": True,
        }


class AdminHintService:
    """Handle hint administration business logic."""

    @staticmethod
    def get_problem_hints_config(problem_slug: str) -> dict[str, Any]:
        """
        Get all hint configurations for a problem, including defaults for missing types.

        Args:
            problem_slug: Problem slug

        Returns:
            Dictionary with problem slug and hint configurations
        """
        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            raise ValueError(f"Problem with slug {problem_slug} not found")

        # Get all hints for this problem
        hints = HintRepository.get_problem_hints(problem)

        # Build response with all hint types
        hint_configs = []
        hint_types_found = set()

        # Add existing hints
        for hint in hints:
            hint_configs.append(
                {
                    "type": hint.hint_type,
                    "is_enabled": hint.is_enabled,
                    "min_attempts": hint.min_attempts,
                    "content": hint.content,
                }
            )
            hint_types_found.add(hint.hint_type)

        # Build default content for counterexample from RefuteProblem if available
        counterexample_default = {"input": {}, "explanation": ""}
        try:
            refute = problem.refuteproblem
            if refute.expected_counterexample:
                counterexample_default = {
                    "input": refute.expected_counterexample,
                    "explanation": "",
                }
        except Exception:
            pass  # Not a RefuteProblem or no expected_counterexample

        # Add default configs for missing hint types
        for hint_type in HintRepository.get_valid_hint_types():
            if hint_type not in hint_types_found:
                default_content = {
                    "variable_fade": {"mappings": []},
                    "subgoal_highlight": {"subgoals": []},
                    "suggested_trace": {"suggested_call": "", "explanation": ""},
                    "counterexample": counterexample_default,
                }
                hint_configs.append(
                    {
                        "type": hint_type,
                        "is_enabled": False,
                        "min_attempts": 3,
                        "content": default_content.get(hint_type, {}),
                    }
                )

        return {"problem_slug": problem.slug, "hints": hint_configs}

    @staticmethod
    def bulk_update_hints(
        problem_slug: str, hints_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Bulk update all hint types for a problem.

        Args:
            problem_slug: Problem slug
            hints_data: List of hint configurations

        Returns:
            Dictionary with updated hint configurations
        """
        from django.core.exceptions import ValidationError

        problem = ProblemRepository.get_problem_by_slug(problem_slug)
        if not problem:
            raise ValueError(f"Problem with slug {problem_slug} not found")

        if not isinstance(hints_data, list):
            raise ValueError("hints must be an array of hint configurations")

        # Validate hint types
        valid_hint_types = HintRepository.get_valid_hint_types()

        try:
            updated_hints = []

            for hint_data in hints_data:
                # Validate required fields
                hint_type = hint_data.get("type")
                if not hint_type:
                    raise ValueError("Each hint must have a type field")

                if hint_type not in valid_hint_types:
                    raise ValueError(
                        f"Invalid hint type: {hint_type}. Must be one of: {', '.join(valid_hint_types)}"
                    )

                # Validate content structure before creating/updating
                content = hint_data.get("content", {})
                temp_hint = ProblemHint(
                    problem=problem, hint_type=hint_type, content=content
                )
                temp_hint.clean()  # Raises ValidationError if content is invalid

                # Get or create the hint
                hint, created = HintRepository.get_or_create_hint(
                    problem=problem,
                    hint_type=hint_type,
                    defaults={
                        "is_enabled": hint_data.get("is_enabled", False),
                        "min_attempts": hint_data.get("min_attempts", 3),
                        "content": hint_data.get("content", {}),
                    },
                )

                # Update existing hint
                if not created:
                    hint = HintRepository.update_hint(
                        hint,
                        is_enabled=hint_data.get("is_enabled", hint.is_enabled),
                        min_attempts=hint_data.get("min_attempts", hint.min_attempts),
                        content=hint_data.get("content", hint.content),
                    )

                updated_hints.append(
                    {
                        "type": hint.hint_type,
                        "is_enabled": hint.is_enabled,
                        "min_attempts": hint.min_attempts,
                        "content": hint.content,
                        "created": created,
                    }
                )

            return {"problem_slug": problem.slug, "hints": updated_hints}

        except ValidationError as e:
            raise ValueError(str(e)) from e
        except ValueError:
            raise  # Re-raise ValueErrors (validation failures)
        except Exception as e:
            logger.error(f"Failed to update hints for problem {problem_slug}: {str(e)}")
            raise RuntimeError(
                "Failed to update hints. Please check the hint configurations."
            ) from e
