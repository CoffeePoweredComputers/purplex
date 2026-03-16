"""Unit tests for counterexample hint type wired to Refute problems."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from purplex.problems_app.models.hint import ProblemHint
from purplex.problems_app.services.hint_display_service import HintDisplayService
from tests.factories import ProblemHintFactory, RefuteProblemFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# =============================================================================
# Model: counterexample hint type
# =============================================================================


class TestCounterexampleHintModel:
    """Test ProblemHint with counterexample type."""

    def test_create_counterexample_hint(self):
        problem = RefuteProblemFactory()
        hint = ProblemHintFactory(
            problem=problem,
            hint_type="counterexample",
            content={"input": {"x": -5}, "explanation": "Try x = -5"},
        )
        hint.full_clean()
        assert hint.hint_type == "counterexample"
        assert hint.content["input"] == {"x": -5}

    def test_valid_content_with_input_only(self):
        problem = RefuteProblemFactory()
        hint = ProblemHintFactory(
            problem=problem,
            hint_type="counterexample",
            content={"input": {"x": -5}},
        )
        hint.full_clean()  # Should not raise

    def test_valid_content_multiple_params(self):
        problem = RefuteProblemFactory()
        hint = ProblemHintFactory(
            problem=problem,
            hint_type="counterexample",
            content={"input": {"x": -5, "y": 10}, "explanation": "edge case"},
        )
        hint.full_clean()

    def test_missing_input_raises_validation_error(self):
        problem = RefuteProblemFactory()
        hint = ProblemHintFactory(
            problem=problem,
            hint_type="counterexample",
            content={"explanation": "no input provided"},
        )
        with pytest.raises(ValidationError, match="must contain input"):
            hint.full_clean()

    def test_non_dict_input_raises_validation_error(self):
        problem = RefuteProblemFactory()
        hint = ProblemHintFactory(
            problem=problem,
            hint_type="counterexample",
            content={"input": [-5]},
        )
        with pytest.raises(ValidationError, match="must be a dict"):
            hint.full_clean()

    def test_string_input_raises_validation_error(self):
        problem = RefuteProblemFactory()
        hint = ProblemHintFactory(
            problem=problem,
            hint_type="counterexample",
            content={"input": "x=-5"},
        )
        with pytest.raises(ValidationError, match="must be a dict"):
            hint.full_clean()

    def test_uniqueness_one_counterexample_per_problem(self):
        problem = RefuteProblemFactory()
        ProblemHintFactory(
            problem=problem,
            hint_type="counterexample",
            content={"input": {"x": -5}},
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProblemHintFactory(
                    problem=problem,
                    hint_type="counterexample",
                    content={"input": {"x": -10}},
                )

    def test_counterexample_in_hint_type_choices(self):
        types = [choice[0] for choice in ProblemHint.HINT_TYPE_CHOICES]
        assert "counterexample" in types


# =============================================================================
# Display service: counterexample mappings
# =============================================================================


class TestCounterexampleDisplayService:
    """Test HintDisplayService has counterexample mappings."""

    def test_display_name(self):
        assert HintDisplayService.get_display_name("counterexample") == "Counterexample"

    def test_emoji(self):
        emoji = HintDisplayService.get_emoji("counterexample")
        assert emoji  # has a value (not the fallback empty case)

    def test_description(self):
        desc = HintDisplayService.get_description("counterexample")
        assert "input" in desc.lower() or "claim" in desc.lower()

    def test_validate_hint_type(self):
        assert HintDisplayService.validate_hint_type("counterexample") is True

    def test_model_consistency_regression_gate(self):
        """Display service dicts must include every type in HINT_TYPE_CHOICES."""
        model_types = {choice[0] for choice in ProblemHint.HINT_TYPE_CHOICES}
        display_types = set(HintDisplayService.HINT_TYPE_DISPLAY_NAMES.keys())
        assert model_types == display_types, (
            f"Mismatch: model has {model_types - display_types}, "
            f"display has {display_types - model_types}"
        )


# =============================================================================
# Refute handler: get_problem_config
# =============================================================================


class TestRefuteHandlerHintConfig:
    """Test RefuteHandler.get_problem_config() declares counterexample hint."""

    def test_hints_available_when_counterexample_set(self, refute_problem):
        from purplex.problems_app.handlers.refute.handler import RefuteHandler

        handler = RefuteHandler()
        config = handler.get_problem_config(refute_problem)

        assert "counterexample" in config["hints"]["available"]
        assert config["hints"]["enabled"] is True

    def test_hints_empty_when_no_counterexample(self):
        from purplex.problems_app.handlers.refute.handler import RefuteHandler

        problem = RefuteProblemFactory(expected_counterexample={})
        handler = RefuteHandler()
        config = handler.get_problem_config(problem)

        assert config["hints"]["available"] == []
        assert config["hints"]["enabled"] is False

    def test_hints_empty_when_counterexample_is_empty_dict(self):
        from purplex.problems_app.handlers.refute.handler import RefuteHandler

        problem = RefuteProblemFactory(expected_counterexample={})
        handler = RefuteHandler()
        config = handler.get_problem_config(problem)

        assert config["hints"]["available"] == []
        assert config["hints"]["enabled"] is False
