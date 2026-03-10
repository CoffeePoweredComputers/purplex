"""
Test suite for HintDisplayService.

Covers display name/emoji/description lookups, validation, formatting,
transformation, and model consistency (regression gate).
"""

import pytest

from purplex.problems_app.models import ProblemHint
from purplex.problems_app.services.hint_display_service import HintDisplayService

pytestmark = [pytest.mark.unit]


class TestHintTypeDisplayNames:
    """Tests for get_display_name()."""

    def test_variable_fade(self):
        assert HintDisplayService.get_display_name("variable_fade") == "Variable Fade"

    def test_subgoal_highlight(self):
        assert (
            HintDisplayService.get_display_name("subgoal_highlight")
            == "Subgoal Highlighting"
        )

    def test_suggested_trace(self):
        assert (
            HintDisplayService.get_display_name("suggested_trace") == "Suggested Trace"
        )

    def test_unknown_type_falls_back_to_title_case(self):
        assert HintDisplayService.get_display_name("some_new_type") == "Some New Type"


class TestHintTypeEmojis:
    """Tests for get_emoji()."""

    def test_variable_fade(self):
        assert HintDisplayService.get_emoji("variable_fade") == "🏷️"

    def test_subgoal_highlight(self):
        assert HintDisplayService.get_emoji("subgoal_highlight") == "🎯"

    def test_suggested_trace(self):
        assert HintDisplayService.get_emoji("suggested_trace") == "🔍"

    def test_unknown_type_falls_back_to_lightbulb(self):
        assert HintDisplayService.get_emoji("unknown") == "💡"


class TestHintTypeDescriptions:
    """Tests for get_description()."""

    def test_variable_fade(self):
        assert (
            "variable names"
            in HintDisplayService.get_description("variable_fade").lower()
        )

    def test_subgoal_highlight(self):
        assert (
            "subgoal" in HintDisplayService.get_description("subgoal_highlight").lower()
        )

    def test_suggested_trace(self):
        assert "trace" in HintDisplayService.get_description("suggested_trace").lower()

    def test_unknown_type_falls_back_to_generic(self):
        assert (
            HintDisplayService.get_description("unknown") == "Provides helpful guidance"
        )


class TestValidateHintType:
    """Tests for validate_hint_type()."""

    @pytest.mark.parametrize(
        "hint_type",
        ["variable_fade", "subgoal_highlight", "suggested_trace"],
    )
    def test_valid_types_return_true(self, hint_type):
        assert HintDisplayService.validate_hint_type(hint_type) is True

    def test_invalid_type_returns_false(self):
        assert HintDisplayService.validate_hint_type("nonexistent") is False

    def test_old_wrong_key_subgoal_hints_returns_false(self):
        """Regression: the old typo 'subgoal_hints' must not be valid."""
        assert HintDisplayService.validate_hint_type("subgoal_hints") is False


class TestGetHintTypesList:
    """Tests for get_hint_types_list()."""

    def test_returns_three_entries(self):
        result = HintDisplayService.get_hint_types_list()
        assert len(result) == 3

    def test_each_entry_has_required_keys(self):
        for entry in HintDisplayService.get_hint_types_list():
            assert set(entry.keys()) == {"type", "display_name", "emoji", "description"}

    def test_contains_subgoal_highlight(self):
        types = {e["type"] for e in HintDisplayService.get_hint_types_list()}
        assert "subgoal_highlight" in types

    def test_does_not_contain_subgoal_hints(self):
        types = {e["type"] for e in HintDisplayService.get_hint_types_list()}
        assert "subgoal_hints" not in types


class TestFormatAvailableHints:
    """Tests for format_available_hints()."""

    def test_subgoal_highlight_gets_correct_title_and_description(self):
        hints = [{"type": "subgoal_highlight", "available": True, "attempts_needed": 0}]
        result = HintDisplayService.format_available_hints(hints)
        assert len(result) == 1
        assert result[0]["title"] == "Subgoal Highlighting"
        assert "subgoal" in result[0]["description"].lower()
        assert result[0]["unlocked"] is True


class TestTransformHintForDisplay:
    """Tests for transform_hint_for_display()."""

    def test_subgoal_highlight_has_correct_display_name_and_emoji(self):
        hint = {"type": "subgoal_highlight", "id": 1, "available": True}
        result = HintDisplayService.transform_hint_for_display(hint)
        assert result["display_name"] == "Subgoal Highlighting"
        assert result["emoji"] == "🎯"
        assert result["type"] == "subgoal_highlight"


class TestHintDisplayServiceModelConsistency:
    """
    Regression gate: service dictionaries must stay in sync with ProblemHint.HINT_TYPE_CHOICES.

    If someone adds a hint type to the model or introduces a typo, these tests fail.
    """

    def _model_hint_types(self):
        return {choice[0] for choice in ProblemHint.HINT_TYPE_CHOICES}

    def test_display_names_match_model(self):
        assert (
            set(HintDisplayService.HINT_TYPE_DISPLAY_NAMES.keys())
            == self._model_hint_types()
        )

    def test_emojis_match_model(self):
        assert (
            set(HintDisplayService.HINT_TYPE_EMOJIS.keys()) == self._model_hint_types()
        )

    def test_descriptions_match_model(self):
        assert (
            set(HintDisplayService.HINT_TYPE_DESCRIPTIONS.keys())
            == self._model_hint_types()
        )
