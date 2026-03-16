"""
Unit tests for the Prompt handler.
"""

from unittest.mock import MagicMock

import pytest

from purplex.problems_app.handlers import (
    get_handler,
    get_registered_types,
    is_registered,
)
from purplex.problems_app.handlers.base import ActivityHandler

pytestmark = pytest.mark.unit


class TestPromptHandlerRegistry:
    """Tests for Prompt handler registration."""

    def test_prompt_handler_registered(self):
        """Prompt handler should be registered on import."""
        assert is_registered("prompt")

    def test_get_registered_types_includes_prompt(self):
        """get_registered_types should include 'prompt'."""
        types = get_registered_types()
        assert "prompt" in types

    def test_handler_inherits_from_activity_handler(self):
        """Handler should inherit from ActivityHandler."""
        handler = get_handler("prompt")
        assert isinstance(handler, ActivityHandler)


class TestPromptHandler:
    """Tests for the Prompt handler implementation."""

    @pytest.fixture
    def handler(self):
        """Create a Prompt handler instance."""
        return get_handler("prompt")

    def test_type_name(self, handler):
        """Handler type_name should be 'prompt'."""
        assert handler.type_name == "prompt"

    def test_min_max_input_length_constants(self, handler):
        """Handler should have MIN and MAX input length constants (same as EiPL)."""
        assert handler.MIN_INPUT_LENGTH == 10
        assert handler.MAX_INPUT_LENGTH == 1000


class TestPromptValidation:
    """Tests for Prompt input validation."""

    @pytest.fixture
    def handler(self):
        """Create a Prompt handler instance."""
        return get_handler("prompt")

    def test_validate_input_too_short(self, handler):
        """Input shorter than MIN_INPUT_LENGTH should be invalid."""
        result = handler.validate_input("short", None)
        assert not result.is_valid
        assert "10 characters" in result.error

    def test_validate_input_valid(self, handler):
        """Valid input should pass validation."""
        result = handler.validate_input(
            "This is a valid description of what the image represents", None
        )
        assert result.is_valid
        assert result.error is None

    def test_validate_input_too_long(self, handler):
        """Input longer than MAX_INPUT_LENGTH should be invalid."""
        result = handler.validate_input("x" * 1001, None)
        assert not result.is_valid
        assert "1000 characters" in result.error


class TestPromptGrading:
    """Tests for Prompt grading logic (same as EiPL)."""

    @pytest.fixture
    def handler(self):
        """Create a Prompt handler instance."""
        return get_handler("prompt")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock Problem."""
        problem = MagicMock()
        problem.segmentation_enabled = True
        problem.segmentation_threshold = 2
        problem.get_segmentation_threshold = 2  # Property access for handlers
        return problem

    @pytest.fixture
    def mock_submission(self, mock_problem):
        """Create a mock Submission."""
        submission = MagicMock()
        submission.submission_id = "test-uuid"
        submission.passed_all_tests = True
        submission.problem = mock_problem
        submission.score = 100

        segmentation = MagicMock()
        segmentation.segment_count = 2
        segmentation.passed = True
        submission.segmentation = segmentation

        return submission

    def test_calculate_grade_incomplete_when_tests_fail(self, handler, mock_submission):
        """Submission with failed tests should be incomplete."""
        mock_submission.passed_all_tests = False
        result = handler.calculate_grade(mock_submission)
        assert result == "incomplete"

    def test_calculate_grade_complete_when_segmentation_disabled(
        self, handler, mock_submission
    ):
        """Submission should be complete when segmentation is disabled."""
        mock_submission.problem.segmentation_enabled = False
        result = handler.calculate_grade(mock_submission)
        assert result == "complete"

    def test_is_correct_when_all_tests_pass(self, handler, mock_submission):
        """is_correct should return True when all tests pass."""
        mock_submission.passed_all_tests = True
        assert handler.is_correct(mock_submission) is True


class TestPromptConfig:
    """Tests for Prompt problem configuration."""

    @pytest.fixture
    def handler(self):
        """Create a Prompt handler instance."""
        return get_handler("prompt")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock Problem with image_url and image_alt_text."""
        problem = MagicMock()
        problem.segmentation_enabled = True
        # Handler reads image_url and image_alt_text directly from the model
        problem.image_url = "https://example.com/image.png"
        problem.image_alt_text = "A flowchart"
        return problem

    def test_get_problem_config_structure(self, handler, mock_problem):
        """Config should have expected structure."""
        config = handler.get_problem_config(mock_problem)

        assert "display" in config
        assert "input" in config
        assert "hints" in config
        assert "feedback" in config

    def test_get_problem_config_display_shows_image(self, handler, mock_problem):
        """Display config should show image instead of code."""
        config = handler.get_problem_config(mock_problem)

        assert config["display"]["show_reference_code"] is False
        assert config["display"]["show_image"] is True
        assert config["display"]["image_url"] == "https://example.com/image.png"
        assert config["display"]["image_alt_text"] == "A flowchart"

    def test_get_problem_config_input(self, handler, mock_problem):
        """Input config should have expected fields (same as EiPL)."""
        config = handler.get_problem_config(mock_problem)

        assert config["input"]["type"] == "textarea"
        assert config["input"]["min_length"] == 10
        assert config["input"]["max_length"] == 1000

    def test_get_admin_config_requires_image_url(self, handler):
        """Admin config should require image_url field."""
        config = handler.get_admin_config()

        assert "image_url" in config["required_fields"]
        assert config["type_specific_section"] == "prompt_image"
