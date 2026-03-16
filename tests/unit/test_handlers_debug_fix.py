"""
Unit tests for the Debug Fix handler.
"""

from unittest.mock import MagicMock

import pytest

from purplex.problems_app.handlers import get_handler
from purplex.problems_app.handlers.base import ActivityHandler

pytestmark = pytest.mark.unit


class TestDebugFixHandler:
    """Tests for Debug Fix handler basics."""

    @pytest.fixture
    def handler(self):
        return get_handler("debug_fix")

    def test_type_name(self, handler):
        assert handler.type_name == "debug_fix"

    def test_min_max_code_length_constants(self, handler):
        assert handler.MIN_CODE_LENGTH == 10
        assert handler.MAX_CODE_LENGTH == 10000

    def test_inherits_from_activity_handler(self, handler):
        assert isinstance(handler, ActivityHandler)


class TestDebugFixValidation:
    """Tests for Debug Fix input validation."""

    @pytest.fixture
    def handler(self):
        return get_handler("debug_fix")

    def test_validate_input_too_short(self, handler):
        result = handler.validate_input("x = 1", None)
        assert not result.is_valid
        assert "10 characters" in result.error

    def test_validate_input_at_minimum(self, handler):
        result = handler.validate_input("x" * 10, None)
        assert result.is_valid
        assert result.error is None

    def test_validate_input_valid_code(self, handler):
        result = handler.validate_input("def fix(x):\n    return x + 1\n", None)
        assert result.is_valid

    def test_validate_input_too_long(self, handler):
        result = handler.validate_input("x" * 10001, None)
        assert not result.is_valid
        assert "10000 characters" in result.error

    def test_validate_input_at_maximum(self, handler):
        result = handler.validate_input("x" * 10000, None)
        assert result.is_valid

    def test_validate_input_syntax_error(self, handler):
        result = handler.validate_input("def broken(:\n    pass\n", None)
        assert not result.is_valid
        assert "Syntax error" in result.error

    def test_validate_input_strips_whitespace(self, handler):
        result = handler.validate_input("  abc  ", None)
        assert not result.is_valid


class TestDebugFixGrading:
    """Tests for Debug Fix grading logic."""

    @pytest.fixture
    def handler(self):
        return get_handler("debug_fix")

    def test_calculate_grade_complete(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = True
        assert handler.calculate_grade(submission) == "complete"

    def test_calculate_grade_incomplete(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = False
        assert handler.calculate_grade(submission) == "incomplete"

    def test_is_correct_true(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = True
        assert handler.is_correct(submission) is True

    def test_is_correct_false(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = False
        assert handler.is_correct(submission) is False


class TestDebugFixCompletion:
    """Tests for Debug Fix completion evaluation."""

    @pytest.fixture
    def handler(self):
        return get_handler("debug_fix")

    def test_evaluate_completion_complete(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = True
        problem = MagicMock()
        assert handler.evaluate_completion(submission, problem) == "complete"

    def test_evaluate_completion_incomplete(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = False
        problem = MagicMock()
        assert handler.evaluate_completion(submission, problem) == "incomplete"


class TestDebugFixDataExtraction:
    """Tests for Debug Fix data extraction methods."""

    @pytest.fixture
    def handler(self):
        return get_handler("debug_fix")

    def test_extract_variations_with_code(self, handler):
        submission = MagicMock()
        submission.processed_code = "def f(x):\n    return x + 1"
        result = handler.extract_variations(submission)
        assert result == ["def f(x):\n    return x + 1"]

    def test_extract_variations_empty(self, handler):
        submission = MagicMock()
        submission.processed_code = None
        result = handler.extract_variations(submission)
        assert result == []

    def test_count_variations_with_code(self, handler):
        submission = MagicMock()
        submission.processed_code = "def f(x): return x"
        assert handler.count_variations(submission) == 1

    def test_count_variations_no_code(self, handler):
        submission = MagicMock()
        submission.processed_code = None
        assert handler.count_variations(submission) == 0

    def test_count_passing_variations_passed(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = True
        assert handler.count_passing_variations(submission) == 1

    def test_count_passing_variations_failed(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = False
        assert handler.count_passing_variations(submission) == 0


class TestDebugFixExtractTestResults:
    """Tests for Debug Fix test result extraction."""

    @pytest.fixture
    def handler(self):
        return get_handler("debug_fix")

    def test_extract_test_results_with_data(self, handler):
        """Should extract test results from code variations."""
        # Mock test execution
        test_exec = MagicMock()
        test_exec.passed = True
        test_exec.input_values = [1, 2]
        test_exec.expected_output = "3"
        test_exec.actual_output = "3"
        test_exec.error_message = None

        # Mock test_executions queryset
        mock_test_execs = MagicMock()
        mock_test_execs.order_by.return_value = mock_test_execs
        mock_test_execs.exists.return_value = True
        mock_test_execs.__iter__ = lambda self: iter([test_exec])

        # Mock variation
        variation = MagicMock()
        variation.tests_passed = 1
        variation.tests_total = 1
        variation.test_executions.all.return_value = mock_test_execs

        # Mock code_variations queryset
        mock_cv = MagicMock()
        mock_cv.exists.return_value = True
        mock_cv.first.return_value = variation

        submission = MagicMock()
        submission.code_variations = mock_cv

        problem = MagicMock()
        problem.function_name = "add"

        results = handler.extract_test_results(submission, problem)
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["testsPassed"] == 1
        assert results[0]["totalTests"] == 1
        assert len(results[0]["test_results"]) == 1
        assert results[0]["test_results"][0]["isSuccessful"] is True

    def test_extract_test_results_no_variations(self, handler):
        """Should return empty list when no code variations exist."""
        submission = MagicMock()
        mock_cv = MagicMock()
        mock_cv.exists.return_value = False
        submission.code_variations = mock_cv

        problem = MagicMock()
        results = handler.extract_test_results(submission, problem)
        assert results == []

    def test_extract_test_results_no_code_variations_attr(self, handler):
        """Should return empty list when submission has no code_variations."""
        submission = MagicMock(spec=[])  # No attributes
        problem = MagicMock()
        results = handler.extract_test_results(submission, problem)
        assert results == []

    def test_extract_test_results_duplicate_keys(self, handler):
        """Should include both 'test_results' and 'results' keys for frontend compat."""
        test_exec = MagicMock()
        test_exec.passed = True
        test_exec.input_values = [1]
        test_exec.expected_output = "1"
        test_exec.actual_output = "1"
        test_exec.error_message = None

        mock_test_execs = MagicMock()
        mock_test_execs.order_by.return_value = mock_test_execs
        mock_test_execs.exists.return_value = True
        mock_test_execs.__iter__ = lambda self: iter([test_exec])

        variation = MagicMock()
        variation.tests_passed = 1
        variation.tests_total = 1
        variation.test_executions.all.return_value = mock_test_execs

        mock_cv = MagicMock()
        mock_cv.exists.return_value = True
        mock_cv.first.return_value = variation

        submission = MagicMock()
        submission.code_variations = mock_cv

        problem = MagicMock()
        problem.function_name = "f"

        results = handler.extract_test_results(submission, problem)
        assert "test_results" in results[0]
        assert "results" in results[0]
        assert results[0]["test_results"] is results[0]["results"]


class TestDebugFixConfig:
    """Tests for Debug Fix problem configuration."""

    @pytest.fixture
    def handler(self):
        return get_handler("debug_fix")

    def test_get_problem_config_structure(self, handler):
        problem = MagicMock()
        config = handler.get_problem_config(problem)
        assert "display" in config
        assert "input" in config
        assert "hints" in config
        assert "feedback" in config

    def test_get_problem_config_display(self, handler):
        problem = MagicMock()
        config = handler.get_problem_config(problem)
        assert config["display"]["show_reference_code"] is False
        assert config["display"]["show_buggy_code"] is True
        assert config["display"]["code_read_only"] is False

    def test_get_problem_config_input(self, handler):
        problem = MagicMock()
        problem.buggy_code = "def f(x):\n    return x + 1"
        config = handler.get_problem_config(problem)
        assert config["input"]["type"] == "code"
        assert config["input"]["language"] == "python"
        assert config["input"]["initial_code"] == "def f(x):\n    return x + 1"
        assert config["input"]["min_length"] == 10
        assert config["input"]["max_length"] == 10000

    def test_get_problem_config_hints(self, handler):
        problem = MagicMock()
        problem.bug_hints = ["Look at the return value"]
        config = handler.get_problem_config(problem)
        assert config["hints"]["enabled"] is True
        assert "bug_hint" in config["hints"]["available"]
        assert config["hints"]["bug_hints"] == ["Look at the return value"]

    def test_get_problem_config_feedback(self, handler):
        problem = MagicMock()
        config = handler.get_problem_config(problem)
        assert config["feedback"]["show_variations"] is False
        assert config["feedback"]["show_segmentation"] is False
        assert config["feedback"]["show_test_results"] is True

    def test_get_admin_config_structure(self, handler):
        config = handler.get_admin_config()
        assert "hidden_sections" in config
        assert "required_fields" in config
        assert "optional_fields" in config
        assert "type_specific_section" in config
        assert "supports" in config

    def test_get_admin_config_supports(self, handler):
        config = handler.get_admin_config()
        assert config["supports"]["hints"] is True
        assert config["supports"]["segmentation"] is False
        assert config["supports"]["test_cases"] is True


class TestDebugFixSerializeResult:
    """Tests for Debug Fix result serialization."""

    @pytest.fixture
    def handler(self):
        return get_handler("debug_fix")

    def test_serialize_result_with_code(self, handler):
        submission = MagicMock()
        submission.processed_code = "def f(x):\n    return x + 1"
        submission.problem = MagicMock()
        submission.problem.function_name = "f"

        # Mock empty code_variations
        mock_cv = MagicMock()
        mock_cv.exists.return_value = False
        submission.code_variations = mock_cv

        result = handler.serialize_result(submission)
        assert result["fixed_code"] == "def f(x):\n    return x + 1"
        assert "test_results" in result

    def test_serialize_result_no_code(self, handler):
        submission = MagicMock()
        submission.processed_code = None
        submission.problem = MagicMock()
        submission.problem.function_name = "f"

        mock_cv = MagicMock()
        mock_cv.exists.return_value = False
        submission.code_variations = mock_cv

        result = handler.serialize_result(submission)
        assert result["fixed_code"] == ""

    def test_serialize_result_problem_type(self, handler):
        """serialize_result should include test_results key."""
        submission = MagicMock()
        submission.processed_code = "code"
        submission.problem = MagicMock()
        submission.problem.function_name = "f"

        mock_cv = MagicMock()
        mock_cv.exists.return_value = False
        submission.code_variations = mock_cv

        result = handler.serialize_result(submission)
        assert "test_results" in result
        assert isinstance(result["test_results"], list)
