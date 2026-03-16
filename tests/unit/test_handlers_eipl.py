"""
Unit tests for the EiPL handler.
"""

from unittest.mock import MagicMock

import pytest

from purplex.problems_app.handlers import get_handler

pytestmark = pytest.mark.unit


class TestEiPLHandler:
    """Tests for the EiPL handler implementation."""

    @pytest.fixture
    def handler(self):
        """Create an EiPL handler instance."""
        return get_handler("eipl")

    def test_type_name(self, handler):
        """Handler type_name should be 'eipl'."""
        assert handler.type_name == "eipl"

    def test_min_max_input_length_constants(self, handler):
        """Handler should have MIN and MAX input length constants."""
        assert handler.MIN_INPUT_LENGTH == 10
        assert handler.MAX_INPUT_LENGTH == 1000


class TestEiPLValidation:
    """Tests for EiPL input validation."""

    @pytest.fixture
    def handler(self):
        """Create an EiPL handler instance."""
        return get_handler("eipl")

    def test_validate_input_too_short(self, handler):
        """Input shorter than MIN_INPUT_LENGTH should be invalid."""
        result = handler.validate_input("short", None)
        assert not result.is_valid
        assert "10 characters" in result.error

    def test_validate_input_at_minimum(self, handler):
        """Input exactly at MIN_INPUT_LENGTH should be valid."""
        result = handler.validate_input("x" * 10, None)
        assert result.is_valid
        assert result.error is None

    def test_validate_input_valid(self, handler):
        """Valid input should pass validation."""
        result = handler.validate_input(
            "This is a valid description of what the code does", None
        )
        assert result.is_valid
        assert result.error is None

    def test_validate_input_too_long(self, handler):
        """Input longer than MAX_INPUT_LENGTH should be invalid."""
        result = handler.validate_input("x" * 1001, None)
        assert not result.is_valid
        assert "1000 characters" in result.error

    def test_validate_input_at_maximum(self, handler):
        """Input exactly at MAX_INPUT_LENGTH should be valid."""
        result = handler.validate_input("x" * 1000, None)
        assert result.is_valid
        assert result.error is None

    def test_validate_input_strips_whitespace(self, handler):
        """Validation should strip leading/trailing whitespace."""
        # 5 chars + whitespace = should fail (less than 10 after strip)
        result = handler.validate_input("  abc  ", None)
        assert not result.is_valid


class TestEiPLGrading:
    """Tests for EiPL grading logic."""

    @pytest.fixture
    def handler(self):
        """Create an EiPL handler instance."""
        return get_handler("eipl")

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

        # Mock segmentation with good result
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

    def test_calculate_grade_incomplete_when_segmentation_missing(
        self, handler, mock_submission
    ):
        """Submission should be incomplete when segmentation is missing."""
        # Remove segmentation attribute
        del mock_submission.segmentation
        result = handler.calculate_grade(mock_submission)
        assert result == "incomplete"

    def test_calculate_grade_complete_when_segments_at_threshold(
        self, handler, mock_submission
    ):
        """Submission should be complete when segments <= threshold."""
        mock_submission.segmentation.segment_count = 2
        result = handler.calculate_grade(mock_submission)
        assert result == "complete"

    def test_calculate_grade_partial_when_segments_exceed_threshold(
        self, handler, mock_submission
    ):
        """Submission should be partial when segments > threshold."""
        mock_submission.segmentation.segment_count = 3
        result = handler.calculate_grade(mock_submission)
        assert result == "partial"

    def test_is_correct_when_all_tests_pass(self, handler, mock_submission):
        """is_correct should return True when all tests pass."""
        mock_submission.passed_all_tests = True
        assert handler.is_correct(mock_submission) is True

    def test_is_correct_when_tests_fail(self, handler, mock_submission):
        """is_correct should return False when tests fail."""
        mock_submission.passed_all_tests = False
        assert handler.is_correct(mock_submission) is False


class TestEiPLCompletion:
    """Tests for EiPL completion evaluation."""

    @pytest.fixture
    def handler(self):
        """Create an EiPL handler instance."""
        return get_handler("eipl")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock Problem."""
        problem = MagicMock()
        problem.segmentation_enabled = True
        return problem

    @pytest.fixture
    def mock_submission(self, mock_problem):
        """Create a mock Submission."""
        submission = MagicMock()
        submission.score = 100
        submission.problem = mock_problem

        segmentation = MagicMock()
        segmentation.passed = True
        submission.segmentation = segmentation

        return submission

    def test_evaluate_completion_incomplete_low_score(
        self, handler, mock_submission, mock_problem
    ):
        """Completion should be incomplete with score < 100."""
        mock_submission.score = 80
        result = handler.evaluate_completion(mock_submission, mock_problem)
        assert result == "incomplete"

    def test_evaluate_completion_complete_segmentation_disabled(
        self, handler, mock_submission, mock_problem
    ):
        """Completion should be complete when segmentation disabled."""
        mock_problem.segmentation_enabled = False
        result = handler.evaluate_completion(mock_submission, mock_problem)
        assert result == "complete"

    def test_evaluate_completion_complete_segmentation_passed(
        self, handler, mock_submission, mock_problem
    ):
        """Completion should be complete when segmentation passes."""
        mock_submission.segmentation.passed = True
        result = handler.evaluate_completion(mock_submission, mock_problem)
        assert result == "complete"

    def test_evaluate_completion_partial_segmentation_failed(
        self, handler, mock_submission, mock_problem
    ):
        """Completion should be partial when segmentation fails."""
        mock_submission.segmentation.passed = False
        result = handler.evaluate_completion(mock_submission, mock_problem)
        assert result == "partial"

    def test_evaluate_completion_incomplete_missing_segmentation(
        self, handler, mock_submission, mock_problem
    ):
        """Completion should be incomplete when segmentation is missing."""
        del mock_submission.segmentation
        result = handler.evaluate_completion(mock_submission, mock_problem)
        assert result == "incomplete"


class TestEiPLConfig:
    """Tests for EiPL problem configuration."""

    @pytest.fixture
    def handler(self):
        """Create an EiPL handler instance."""
        return get_handler("eipl")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock Problem."""
        problem = MagicMock()
        problem.segmentation_enabled = True
        return problem

    def test_get_problem_config_structure(self, handler, mock_problem):
        """Config should have expected structure."""
        config = handler.get_problem_config(mock_problem)

        assert "display" in config
        assert "input" in config
        assert "hints" in config
        assert "feedback" in config

    def test_get_problem_config_display(self, handler, mock_problem):
        """Display config should have expected fields."""
        config = handler.get_problem_config(mock_problem)

        assert config["display"]["show_reference_code"] is True
        assert config["display"]["code_read_only"] is True
        assert config["display"]["show_function_signature"] is True

    def test_get_problem_config_input(self, handler, mock_problem):
        """Input config should have expected fields."""
        config = handler.get_problem_config(mock_problem)

        assert config["input"]["type"] == "textarea"
        assert config["input"]["min_length"] == 10
        assert config["input"]["max_length"] == 1000

    def test_get_problem_config_hints(self, handler, mock_problem):
        """Hints config should have expected fields."""
        config = handler.get_problem_config(mock_problem)

        assert "variable_fade" in config["hints"]["available"]
        assert "subgoal_highlight" in config["hints"]["available"]
        assert "suggested_trace" in config["hints"]["available"]

    def test_get_problem_config_feedback_segmentation_enabled(
        self, handler, mock_problem
    ):
        """Feedback config should reflect segmentation_enabled."""
        mock_problem.segmentation_enabled = True
        config = handler.get_problem_config(mock_problem)
        assert config["feedback"]["show_segmentation"] is True

    def test_get_problem_config_feedback_segmentation_disabled(
        self, handler, mock_problem
    ):
        """Feedback config should reflect segmentation_enabled=False."""
        mock_problem.segmentation_enabled = False
        config = handler.get_problem_config(mock_problem)
        assert config["feedback"]["show_segmentation"] is False


class TestEiPLFormatFunctionCall:
    """Tests for the _format_function_call helper."""

    @pytest.fixture
    def handler(self):
        """Create an EiPL handler instance."""
        return get_handler("eipl")

    def test_format_with_list_of_integers(self, handler):
        """Should format list of integers correctly."""
        result = handler._format_function_call("foo", [1, 2, 3])
        assert result == "foo(1, 2, 3)"

    def test_format_with_list_of_strings(self, handler):
        """Should format list of strings with quotes."""
        result = handler._format_function_call("foo", ["a", "b"])
        assert result == 'foo("a", "b")'

    def test_format_with_mixed_types(self, handler):
        """Should format mixed types correctly."""
        result = handler._format_function_call("foo", [1, "hello", True])
        assert result == 'foo(1, "hello", True)'

    def test_format_with_single_value(self, handler):
        """Should format single value correctly."""
        result = handler._format_function_call("foo", 42)
        assert result == "foo(42)"

    def test_format_with_single_string(self, handler):
        """Should format single string with quotes."""
        result = handler._format_function_call("foo", "bar")
        assert result == 'foo("bar")'


class TestEiPLSerializeResult:
    """Tests for EiPL result serialization."""

    @pytest.fixture
    def handler(self):
        """Create an EiPL handler instance."""
        return get_handler("eipl")

    @pytest.fixture
    def mock_submission(self):
        """Create a mock submission with variations and segmentation."""
        submission = MagicMock()
        submission.problem = MagicMock()
        submission.problem.segmentation_threshold = 2
        submission.problem.get_segmentation_threshold = (
            2  # Property access for handlers
        )
        submission.problem.function_name = "fib"

        # Mock variations
        variation1 = MagicMock()
        variation1.generated_code = "def fib(n): pass"
        variation1.score = 100
        variation1.tests_passed = 5
        variation1.tests_total = 5
        variation1.is_selected = True

        # Mock test_executions for variation (empty for this test)
        mock_test_execs = MagicMock()
        mock_test_execs.order_by.return_value = mock_test_execs
        mock_test_execs.exists.return_value = False
        mock_test_execs.__iter__ = lambda self: iter([])
        variation1.test_executions.all.return_value = mock_test_execs

        # Mock code_variations with chainable queryset
        variations_list = [variation1]
        mock_variations_qs = MagicMock()
        mock_variations_qs.order_by.return_value = variations_list
        mock_variations_qs.__iter__ = lambda self: iter(variations_list)
        submission.code_variations.all.return_value = mock_variations_qs

        # Mock segmentation
        segmentation = MagicMock()
        segmentation.segment_count = 2
        segmentation.comprehension_level = "relational"
        segmentation.passed = True
        submission.segmentation = segmentation

        return submission

    def test_serialize_result_structure(self, handler, mock_submission):
        """Serialized result should have expected structure."""
        result = handler.serialize_result(mock_submission)

        assert "variations" in result
        assert "segmentation" in result

    def test_serialize_result_variations(self, handler, mock_submission):
        """Should serialize variations correctly."""
        result = handler.serialize_result(mock_submission)

        assert len(result["variations"]) == 1
        var = result["variations"][0]
        assert var["code"] == "def fib(n): pass"
        assert var["score"] == 100
        assert var["tests_passed"] == 5
        assert var["tests_total"] == 5
        assert var["is_selected"] is True

    def test_serialize_result_segmentation(self, handler, mock_submission):
        """Should serialize segmentation correctly."""
        result = handler.serialize_result(mock_submission)

        seg = result["segmentation"]
        assert seg["segment_count"] == 2
        assert seg["comprehension_level"] == "relational"
        assert seg["passed"] is True
        assert seg["threshold"] == 2

    def test_serialize_result_no_segmentation(self, handler):
        """Should handle missing segmentation gracefully."""
        submission = MagicMock()
        submission.problem = MagicMock()
        submission.problem.function_name = "test_func"

        # Mock code_variations with chainable queryset (empty)
        mock_variations_qs = MagicMock()
        mock_variations_qs.order_by.return_value = []
        mock_variations_qs.__iter__ = lambda self: iter([])
        submission.code_variations.all.return_value = mock_variations_qs

        # No segmentation attribute
        del submission.segmentation

        result = handler.serialize_result(submission)

        assert result["segmentation"] is None
