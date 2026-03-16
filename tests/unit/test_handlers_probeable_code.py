"""
Unit tests for the Probeable Code handler.
"""

from unittest.mock import MagicMock

import pytest

from purplex.problems_app.handlers import get_handler
from purplex.problems_app.handlers.base import ActivityHandler

pytestmark = pytest.mark.unit


class TestProbeableCodeHandler:
    """Tests for Probeable Code handler basics."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_code")

    def test_type_name(self, handler):
        assert handler.type_name == "probeable_code"

    def test_min_max_code_length_constants(self, handler):
        assert handler.MIN_CODE_LENGTH == 10
        assert handler.MAX_CODE_LENGTH == 10000

    def test_inherits_from_activity_handler(self, handler):
        assert isinstance(handler, ActivityHandler)


class TestProbeableCodeValidation:
    """Tests for Probeable Code input validation."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_code")

    def test_validate_input_too_short(self, handler):
        result = handler.validate_input("x = 1", None)
        assert not result.is_valid
        assert "10 characters" in result.error

    def test_validate_input_at_minimum(self, handler):
        result = handler.validate_input("x" * 10, None)
        assert result.is_valid

    def test_validate_input_valid_code(self, handler):
        result = handler.validate_input("def solve(x):\n    return x * 2\n", None)
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


class TestProbeableCodeGrading:
    """Tests for Probeable Code grading logic."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_code")

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


class TestProbeableCodeCompletion:
    """Tests for Probeable Code completion evaluation."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_code")

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


class TestProbeableCodeDataExtraction:
    """Tests for Probeable Code data extraction methods."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_code")

    def test_extract_variations_with_code(self, handler):
        submission = MagicMock()
        submission.processed_code = "def f(x):\n    return x * 2"
        result = handler.extract_variations(submission)
        assert result == ["def f(x):\n    return x * 2"]

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


class TestProbeableCodeExtractTestResults:
    """Tests for Probeable Code test result extraction."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_code")

    def test_extract_test_results_with_data(self, handler):
        """Should extract test results from code variations."""
        test_exec = MagicMock()
        test_exec.passed = True
        test_exec.input_values = [5]
        test_exec.expected_output = "10"
        test_exec.actual_output = "10"
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
        problem.function_name = "double"

        results = handler.extract_test_results(submission, problem)
        assert len(results) == 1
        assert results[0]["success"] is True
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
        submission = MagicMock(spec=[])
        problem = MagicMock()
        results = handler.extract_test_results(submission, problem)
        assert results == []

    def test_extract_test_results_duplicate_keys(self, handler):
        """Should include both 'test_results' and 'results' keys."""
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
        assert results[0]["test_results"] is results[0]["results"]


class TestProbeableCodeConfig:
    """Tests for Probeable Code problem configuration."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_code")

    @pytest.fixture
    def mock_problem(self):
        problem = MagicMock()
        problem.function_signature = "f(x: int) -> int"
        problem.function_name = "f"
        problem.show_function_signature = True
        problem.probe_mode = "explore"
        problem.max_probes = 10
        problem.cooldown_attempts = 3
        problem.cooldown_refill = 5
        return problem

    def test_get_problem_config_structure(self, handler, mock_problem):
        config = handler.get_problem_config(mock_problem)
        assert "display" in config
        assert "input" in config
        assert "probe" in config
        assert "hints" in config
        assert "feedback" in config

    def test_get_problem_config_display(self, handler, mock_problem):
        config = handler.get_problem_config(mock_problem)
        assert config["display"]["show_reference_code"] is False
        assert config["display"]["code_read_only"] is False

    def test_get_problem_config_input(self, handler, mock_problem):
        config = handler.get_problem_config(mock_problem)
        assert config["input"]["type"] == "probeable_code"
        assert config["input"]["language"] == "python"
        assert config["input"]["min_length"] == 10
        assert config["input"]["max_length"] == 10000

    def test_get_problem_config_probe_settings(self, handler):
        problem = MagicMock()
        problem.show_function_signature = True
        problem.probe_mode = "cooldown"
        problem.max_probes = 15
        problem.cooldown_attempts = 5
        problem.cooldown_refill = 3
        problem.function_signature = "solve(x: int) -> int"
        problem.function_name = "solve"

        config = handler.get_problem_config(problem)
        assert config["probe"]["enabled"] is True
        assert config["probe"]["mode"] == "cooldown"
        assert config["probe"]["max_probes"] == 15
        assert config["probe"]["cooldown_attempts"] == 5
        assert config["probe"]["cooldown_refill"] == 3
        assert config["probe"]["function_signature"] == "solve(x: int) -> int"
        assert config["probe"]["function_name"] == "solve"

    def test_get_problem_config_signature_hidden(self, handler):
        problem = MagicMock()
        problem.show_function_signature = False
        problem.function_signature = "solve(x: int) -> int"
        config = handler.get_problem_config(problem)
        assert config["probe"]["function_signature"] is None

    def test_get_problem_config_hints_disabled(self, handler, mock_problem):
        config = handler.get_problem_config(mock_problem)
        assert config["hints"]["enabled"] is False
        assert config["hints"]["available"] == []

    def test_get_admin_config_supports(self, handler):
        config = handler.get_admin_config()
        assert config["supports"]["hints"] is False
        assert config["supports"]["segmentation"] is False
        assert config["supports"]["test_cases"] is True
        assert "probeable_code_config" == config["type_specific_section"]


class TestProbeableCodeSerializeResult:
    """Tests for Probeable Code result serialization."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_code")

    def test_serialize_result_with_code(self, handler):
        submission = MagicMock()
        submission.processed_code = "def f(x):\n    return x * 2"
        submission.problem = MagicMock()
        submission.problem.function_name = "f"

        mock_cv = MagicMock()
        mock_cv.exists.return_value = False
        submission.code_variations = mock_cv

        result = handler.serialize_result(submission)
        assert result["student_code"] == "def f(x):\n    return x * 2"
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
        assert result["student_code"] == ""

    def test_serialize_result_has_test_results(self, handler):
        submission = MagicMock()
        submission.processed_code = "code"
        submission.problem = MagicMock()
        submission.problem.function_name = "f"

        mock_cv = MagicMock()
        mock_cv.exists.return_value = False
        submission.code_variations = mock_cv

        result = handler.serialize_result(submission)
        assert isinstance(result["test_results"], list)
