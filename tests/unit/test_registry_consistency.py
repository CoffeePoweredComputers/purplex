"""
Unit tests for registry consistency across the activity type system.

These tests verify that:
- All expected problem types have registered handlers
- All handlers implement required interfaces
- Handler registry is the source of truth for problem types
"""

import os

import django
import pytest

# Configure Django settings before setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "purplex.settings")
django.setup()

from purplex.problems_app.handlers import (  # noqa: E402
    get_handler,
    get_registered_types,
    is_registered,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Expected problem types - the handler registry is the source of truth
EXPECTED_PROBLEM_TYPES = [
    "debug_fix",
    "eipl",
    "mcq",
    "probeable_code",
    "probeable_spec",
    "prompt",
    "refute",
]


class TestHandlerRegistryConsistency:
    """Tests for handler registry consistency."""

    def test_all_expected_types_are_registered(self):
        """All expected problem types should have registered handlers."""
        for type_key in EXPECTED_PROBLEM_TYPES:
            assert is_registered(
                type_key
            ), f"Expected problem type '{type_key}' has no registered handler"

    def test_no_unexpected_handlers_registered(self):
        """All registered handlers should be in expected types list."""
        registered_types = get_registered_types()

        for handler_type in registered_types:
            assert handler_type in EXPECTED_PROBLEM_TYPES, (
                f"Handler '{handler_type}' is registered but not in EXPECTED_PROBLEM_TYPES. "
                f"Update the test if this is intentional."
            )

    def test_registered_types_count(self):
        """Should have exactly 7 registered types."""
        types = get_registered_types()
        assert len(types) == 7, f"Expected 7 types, got {len(types)}: {types}"


class TestHandlerSubmitMethod:
    """Tests for handler submit() method implementation.

    Each handler owns its execution model (sync vs async) via the submit() method.
    This replaced the previous PIPELINE_TASKS dict approach.
    """

    def test_all_handlers_have_submit_method(self):
        """All registered handlers should have a submit() method."""
        registered_types = get_registered_types()

        for handler_type in registered_types:
            handler = get_handler(handler_type)
            assert hasattr(
                handler, "submit"
            ), f"Handler '{handler_type}' has no submit() method"
            assert callable(
                handler.submit
            ), f"Handler '{handler_type}' submit is not callable"

    def test_submit_method_signature(self):
        """All handler submit() methods should have consistent signature."""
        import inspect

        registered_types = get_registered_types()

        for handler_type in registered_types:
            handler = get_handler(handler_type)
            sig = inspect.signature(handler.submit)
            params = list(sig.parameters.keys())

            # Expected params: self, submission, raw_input, problem, context
            expected_params = ["submission", "raw_input", "problem", "context"]
            for param in expected_params:
                assert (
                    param in params
                ), f"Handler '{handler_type}' submit() missing parameter '{param}'"


class TestHandlerTypeNames:
    """Tests for handler type_name consistency."""

    def test_handler_type_name_matches_registration(self):
        """Each handler's type_name should match its registration key."""
        registered_types = get_registered_types()

        for type_key in registered_types:
            handler = get_handler(type_key)
            assert (
                handler.type_name == type_key
            ), f"Handler registered as '{type_key}' has type_name '{handler.type_name}'"


class TestHandlerConfigConsistency:
    """Tests for handler config structure consistency."""

    @pytest.fixture
    def all_handlers(self):
        """Get instances of all registered handlers."""
        return {type_key: get_handler(type_key) for type_key in get_registered_types()}

    def test_all_handlers_have_get_problem_config(self, all_handlers):
        """All handlers should implement get_problem_config."""
        from unittest.mock import MagicMock

        for type_key, handler in all_handlers.items():
            mock_problem = MagicMock()
            # Core attributes used by most handlers
            mock_problem.segmentation_enabled = False
            mock_problem.options = []
            mock_problem.allow_multiple = False
            mock_problem.prompt_config = {}
            mock_problem.function_signature = "def example(x: int) -> int:"
            mock_problem.function_name = "example"
            # Probeable handler attributes
            mock_problem.probe_mode = "explore"
            mock_problem.max_probes = 5
            mock_problem.cooldown_attempts = 3
            mock_problem.cooldown_refill = 2
            mock_problem.show_function_signature = True
            # Debug fix handler attributes
            mock_problem.buggy_code = ""
            mock_problem.bug_hints = []
            # Refute handler attributes
            mock_problem.claim_text = ""
            # Make polymorphic lookups return the same mock (for _ensure_*_problem functions)
            mock_problem.refuteproblem = mock_problem

            # Should not raise
            config = handler.get_problem_config(mock_problem)

            # Should have required structure
            assert "display" in config, f"{type_key} config missing 'display'"
            assert "input" in config, f"{type_key} config missing 'input'"
            assert "hints" in config, f"{type_key} config missing 'hints'"
            assert "feedback" in config, f"{type_key} config missing 'feedback'"

    def test_all_handlers_have_get_admin_config(self, all_handlers):
        """All handlers should implement get_admin_config."""
        for type_key, handler in all_handlers.items():
            # Should not raise
            config = handler.get_admin_config()

            # Should have required structure
            assert (
                "hidden_sections" in config
            ), f"{type_key} admin config missing 'hidden_sections'"
            assert (
                "required_fields" in config
            ), f"{type_key} admin config missing 'required_fields'"
            assert "supports" in config, f"{type_key} admin config missing 'supports'"

    def test_feedback_config_has_show_segmentation(self, all_handlers):
        """All handler feedback configs should have show_segmentation field."""
        from unittest.mock import MagicMock

        for type_key, handler in all_handlers.items():
            mock_problem = MagicMock()
            # Core attributes used by most handlers
            mock_problem.segmentation_enabled = False
            mock_problem.options = []
            mock_problem.allow_multiple = False
            mock_problem.prompt_config = {}
            mock_problem.function_signature = "def example(x: int) -> int:"
            mock_problem.function_name = "example"
            # Probeable handler attributes
            mock_problem.probe_mode = "explore"
            mock_problem.max_probes = 5
            mock_problem.cooldown_attempts = 3
            mock_problem.cooldown_refill = 2
            mock_problem.show_function_signature = True
            # Debug fix handler attributes
            mock_problem.buggy_code = ""
            mock_problem.bug_hints = []
            # Refute handler attributes
            mock_problem.claim_text = ""
            # Make polymorphic lookups return the same mock (for _ensure_*_problem functions)
            mock_problem.refuteproblem = mock_problem

            config = handler.get_problem_config(mock_problem)

            assert (
                "show_segmentation" in config["feedback"]
            ), f"{type_key} feedback config missing 'show_segmentation'"

    def test_admin_config_supports_structure(self, all_handlers):
        """All handler admin configs should have consistent supports structure."""
        expected_keys = {"hints", "segmentation", "test_cases"}

        for type_key, handler in all_handlers.items():
            config = handler.get_admin_config()
            supports = config["supports"]

            for key in expected_keys:
                assert (
                    key in supports
                ), f"{type_key} admin config 'supports' missing '{key}'"
                assert isinstance(
                    supports[key], bool
                ), f"{type_key} admin config 'supports.{key}' should be boolean"
