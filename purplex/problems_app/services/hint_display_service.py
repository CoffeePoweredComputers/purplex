"""Service for managing hint display and presentation logic."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class HintDisplayService:
    """
    Handle all hint display and presentation business logic.

    This service centralizes all hint display transformations and
    presentation logic that was previously scattered across views.
    """

    # Display name mappings for hint types
    HINT_TYPE_DISPLAY_NAMES = {
        "variable_fade": "Variable Fade",
        "subgoal_highlight": "Subgoal Highlighting",
        "suggested_trace": "Suggested Trace",
    }

    # Emoji mappings for hint types
    HINT_TYPE_EMOJIS = {
        "variable_fade": "🏷️",
        "subgoal_highlight": "🎯",
        "suggested_trace": "🔍",
    }

    # Descriptions for hint types
    HINT_TYPE_DESCRIPTIONS = {
        "variable_fade": "Gradually reveals variable names in the solution",
        "subgoal_highlight": "Highlights key subgoals to solve the problem",
        "suggested_trace": "Provides a step-by-step trace through the solution",
    }

    # Default minimum attempts before hints are available
    DEFAULT_MIN_ATTEMPTS = 3

    @classmethod
    def get_display_name(cls, hint_type: str) -> str:
        """
        Get the display name for a hint type.

        Args:
            hint_type: The internal hint type identifier

        Returns:
            Human-readable display name
        """
        return cls.HINT_TYPE_DISPLAY_NAMES.get(
            hint_type, hint_type.replace("_", " ").title()
        )

    @classmethod
    def get_emoji(cls, hint_type: str) -> str:
        """
        Get the emoji for a hint type.

        Args:
            hint_type: The internal hint type identifier

        Returns:
            Emoji character for the hint type
        """
        return cls.HINT_TYPE_EMOJIS.get(hint_type, "💡")

    @classmethod
    def get_description(cls, hint_type: str) -> str:
        """
        Get the description for a hint type.

        Args:
            hint_type: The internal hint type identifier

        Returns:
            Description of what the hint type does
        """
        return cls.HINT_TYPE_DESCRIPTIONS.get(hint_type, "Provides helpful guidance")

    @classmethod
    def format_available_hints(
        cls, hints: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Format available hints for API response.

        Args:
            hints: List of hint availability data

        Returns:
            Formatted list of hints for display
        """
        available_hints = []
        for hint in hints:
            title = cls.get_display_name(hint["type"])
            description = cls.get_description(hint["type"])

            available_hints.append(
                {
                    "type": hint["type"],
                    "title": title,
                    "description": description,
                    "unlocked": hint["available"],
                    "available": hint["available"],
                    "attempts_needed": hint["attempts_needed"],
                }
            )
        return available_hints

    @classmethod
    def transform_hint_for_display(cls, hint: dict[str, Any]) -> dict[str, Any]:
        """
        Transform a raw hint into display format.

        Args:
            hint: Raw hint data from database/service

        Returns:
            Transformed hint with display properties
        """
        hint_type = hint.get("type", "")

        return {
            "id": hint.get("id"),
            "type": hint_type,
            "display_name": cls.get_display_name(hint_type),
            "emoji": cls.get_emoji(hint_type),
            "description": cls.get_description(hint_type),
            "available": hint.get("available", False),
            "content": hint.get("content"),
            "order": hint.get("order", 0),
            "metadata": hint.get("metadata", {}),
        }

    @classmethod
    def transform_hints_for_display(
        cls, hints: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Transform multiple hints for display.

        Args:
            hints: List of raw hint data

        Returns:
            List of transformed hints
        """
        return [cls.transform_hint_for_display(hint) for hint in hints]

    @classmethod
    def format_hint_availability_response(
        cls, hints_data: dict[str, Any], user_attempts: int
    ) -> dict[str, Any]:
        """
        Format the hint availability response for API.

        Args:
            hints_data: Raw hints availability data
            user_attempts: Number of attempts user has made

        Returns:
            Formatted response for API
        """
        available_hints = []
        unavailable_hints = []

        for hint_type, hint_info in hints_data.items():
            display_hint = {
                "type": hint_type,
                "display_name": cls.get_display_name(hint_type),
                "emoji": cls.get_emoji(hint_type),
                "available": hint_info.get("available", False),
            }

            if hint_info.get("available"):
                available_hints.append(display_hint)
            else:
                unavailable_hints.append(display_hint)

        return {
            "user_attempts": user_attempts,
            "min_attempts_required": cls.DEFAULT_MIN_ATTEMPTS,
            "available_hints": available_hints,
            "unavailable_hints": unavailable_hints,
            "message": cls._get_availability_message(
                user_attempts, len(available_hints)
            ),
        }

    @classmethod
    def _get_availability_message(cls, attempts: int, available_count: int) -> str:
        """
        Generate an appropriate message about hint availability.

        Args:
            attempts: Number of user attempts
            available_count: Number of available hints

        Returns:
            User-friendly message
        """
        if attempts < cls.DEFAULT_MIN_ATTEMPTS:
            remaining = cls.DEFAULT_MIN_ATTEMPTS - attempts
            return f"Try {remaining} more time{'s' if remaining != 1 else ''} to unlock hints"
        elif available_count == 0:
            return "No hints are available for this problem"
        elif available_count == 1:
            return "1 hint is available"
        else:
            return f"{available_count} hints are available"

    @classmethod
    def format_hint_content_response(
        cls, hint_type: str, content: Any, additional_data: dict | None = None
    ) -> dict[str, Any]:
        """
        Format hint content for API response.

        Args:
            hint_type: Type of hint
            content: The actual hint content
            additional_data: Any additional data to include

        Returns:
            Formatted hint content response
        """
        response = {
            "type": hint_type,
            "display_name": cls.get_display_name(hint_type),
            "emoji": cls.get_emoji(hint_type),
            "content": content,
        }

        if additional_data:
            response.update(additional_data)

        return response

    @classmethod
    def should_show_hint(
        cls, user_attempts: int, min_attempts: int | None = None
    ) -> bool:
        """
        Determine if hints should be shown based on attempts.

        Args:
            user_attempts: Number of attempts user has made
            min_attempts: Minimum attempts required (uses default if None)

        Returns:
            True if hints should be shown
        """
        min_required = (
            min_attempts if min_attempts is not None else cls.DEFAULT_MIN_ATTEMPTS
        )
        return user_attempts >= min_required

    @classmethod
    def get_hint_types_list(cls) -> list[dict[str, str]]:
        """
        Get a list of all hint types with their properties.

        Returns:
            List of dictionaries containing hint type information
        """
        return [
            {
                "type": hint_type,
                "display_name": display_name,
                "emoji": cls.HINT_TYPE_EMOJIS.get(hint_type, "💡"),
                "description": cls.HINT_TYPE_DESCRIPTIONS.get(hint_type, ""),
            }
            for hint_type, display_name in cls.HINT_TYPE_DISPLAY_NAMES.items()
        ]

    @classmethod
    def validate_hint_type(cls, hint_type: str) -> bool:
        """
        Validate if a hint type is recognized.

        Args:
            hint_type: The hint type to validate

        Returns:
            True if valid, False otherwise
        """
        return hint_type in cls.HINT_TYPE_DISPLAY_NAMES
