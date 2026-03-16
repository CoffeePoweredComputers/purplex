"""
Unit tests for the Refute handler.
"""

import json
from unittest.mock import MagicMock

import pytest

from purplex.problems_app.handlers import get_handler
from purplex.problems_app.handlers.base import ActivityHandler, ProcessingResult

pytestmark = pytest.mark.unit


def _make_refute_problem(**overrides):
    """Create a mock RefuteProblem with sensible defaults."""
    from purplex.problems_app.models import RefuteProblem

    problem = MagicMock(spec=RefuteProblem)
    problem.slug = overrides.get("slug", "test-refute")
    problem.reference_solution = overrides.get(
        "reference_solution", "def f(x):\n    return x * 2"
    )
    problem.function_signature = overrides.get("function_signature", "f(x: int) -> int")
    problem.claim_predicate = overrides.get("claim_predicate", "result > 0")
    problem.claim_text = overrides.get(
        "claim_text", "The function always returns a positive number"
    )
    problem.expected_counterexample = overrides.get("expected_counterexample", "")
    return problem


class TestRefuteHandler:
    """Tests for Refute handler basics."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    def test_type_name(self, handler):
        assert handler.type_name == "refute"

    def test_inherits_from_activity_handler(self, handler):
        assert isinstance(handler, ActivityHandler)


class TestRefuteValidation:
    """Tests for Refute input validation."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    @pytest.fixture
    def mock_problem(self):
        return _make_refute_problem()

    def test_validate_input_empty(self, handler, mock_problem):
        result = handler.validate_input("", mock_problem)
        assert not result.is_valid
        assert "provide input" in result.error.lower()

    def test_validate_input_valid_json(self, handler, mock_problem):
        result = handler.validate_input('{"x": -5}', mock_problem)
        assert result.is_valid

    def test_validate_input_invalid_json(self, handler, mock_problem):
        result = handler.validate_input("not json", mock_problem)
        assert not result.is_valid
        assert "Invalid JSON" in result.error

    def test_validate_input_not_a_dict(self, handler, mock_problem):
        result = handler.validate_input("[1, 2, 3]", mock_problem)
        assert not result.is_valid
        assert "JSON object" in result.error

    def test_validate_input_missing_parameter(self, handler, mock_problem):
        """Should fail when required parameters are missing."""
        result = handler.validate_input("{}", mock_problem)
        assert not result.is_valid
        assert "Missing parameter" in result.error
        assert "x" in result.error

    def test_validate_input_extra_params_allowed(self, handler, mock_problem):
        """Extra parameters should be allowed (JSON is permissive)."""
        result = handler.validate_input('{"x": 5, "extra": 10}', mock_problem)
        assert result.is_valid

    def test_validate_input_multiple_params(self, handler):
        """Should validate all required parameters."""
        problem = _make_refute_problem(function_signature="g(a: int, b: str) -> bool")
        result = handler.validate_input('{"a": 1}', problem)
        assert not result.is_valid
        assert "b" in result.error

    def test_validate_input_all_params_provided(self, handler):
        problem = _make_refute_problem(function_signature="g(a: int, b: str) -> bool")
        result = handler.validate_input('{"a": 1, "b": "test"}', problem)
        assert result.is_valid


class TestRefuteGrading:
    """Tests for Refute grading logic."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

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


class TestRefuteCompletion:
    """Tests for Refute completion evaluation."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    def test_evaluate_completion_complete(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = True
        problem = _make_refute_problem()
        assert handler.evaluate_completion(submission, problem) == "complete"

    def test_evaluate_completion_incomplete(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = False
        problem = _make_refute_problem()
        assert handler.evaluate_completion(submission, problem) == "incomplete"


class TestRefuteDataExtraction:
    """Tests for Refute data extraction methods."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    def test_extract_variations(self, handler):
        submission = MagicMock()
        submission.raw_input = '{"x": -5}'
        result = handler.extract_variations(submission)
        assert result == ['{"x": -5}']

    def test_extract_variations_empty(self, handler):
        submission = MagicMock()
        submission.raw_input = ""
        result = handler.extract_variations(submission)
        assert result == []

    def test_count_variations(self, handler):
        submission = MagicMock()
        assert handler.count_variations(submission) == 1

    def test_count_passing_variations_passed(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = True
        assert handler.count_passing_variations(submission) == 1

    def test_count_passing_variations_failed(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = False
        assert handler.count_passing_variations(submission) == 0

    def test_extract_test_results_with_data(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = True
        submission.type_specific_data = {
            "input_args": {"x": -5},
            "result_value": -10,
            "claim_disproven": True,
            "execution_error": None,
        }

        problem = _make_refute_problem()
        results = handler.extract_test_results(submission, problem)
        assert len(results) == 1
        assert results[0]["isSuccessful"] is True
        assert results[0]["input_args"] == {"x": -5}
        assert results[0]["claim_disproven"] is True

    def test_extract_test_results_no_data(self, handler):
        submission = MagicMock()
        submission.passed_all_tests = False
        submission.type_specific_data = None

        problem = _make_refute_problem()
        results = handler.extract_test_results(submission, problem)
        assert len(results) == 1
        assert results[0]["isSuccessful"] is False
        assert results[0]["claim_disproven"] is False


class TestRefuteProcessSubmission:
    """Tests for Refute process_submission (moved from test_handlers.py)."""

    def test_process_submission_disproven(self):
        """Should detect a valid counterexample."""
        handler = get_handler("refute")
        mock_submission = MagicMock()
        mock_problem = _make_refute_problem()

        # f(-5) = -10, which is NOT > 0, so the claim is disproven
        result = handler.process_submission(
            mock_submission, json.dumps({"x": -5}), mock_problem
        )

        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.type_specific_data["claim_disproven"] is True
        assert result.type_specific_data["execution_success"] is True
        assert result.type_specific_data["result_value"] == -10

    def test_process_submission_not_disproven(self):
        """Should reject non-counterexamples."""
        handler = get_handler("refute")
        mock_submission = MagicMock()
        mock_problem = _make_refute_problem()

        # f(5) = 10, which IS > 0, so the claim holds
        result = handler.process_submission(
            mock_submission, json.dumps({"x": 5}), mock_problem
        )

        assert isinstance(result, ProcessingResult)
        assert result.success is True
        assert result.type_specific_data["claim_disproven"] is False
        assert result.type_specific_data["result_value"] == 10

    def test_process_submission_execution_error(self):
        """Should handle execution errors gracefully."""
        handler = get_handler("refute")
        mock_submission = MagicMock()
        mock_problem = _make_refute_problem(
            reference_solution="def f(x):\n    raise ValueError('boom')"
        )

        result = handler.process_submission(
            mock_submission, json.dumps({"x": 1}), mock_problem
        )

        assert result.success is True
        assert result.type_specific_data["execution_success"] is False
        assert result.type_specific_data["claim_disproven"] is False
        assert result.type_specific_data["execution_error"] is not None

    def test_process_submission_no_predicate_uses_legacy(self):
        """Should fall back to legacy pattern matching when no predicate."""
        handler = get_handler("refute")
        mock_submission = MagicMock()
        mock_problem = _make_refute_problem(
            claim_predicate="",
            claim_text="The function always returns a positive number",
        )

        # f(-5) = -10, which is not positive
        result = handler.process_submission(
            mock_submission, json.dumps({"x": -5}), mock_problem
        )

        assert result.success is True
        assert result.type_specific_data["claim_disproven"] is True


class TestRefuteEvaluateClaim:
    """Tests for _evaluate_claim method."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    def test_predicate_claim_holds(self, handler):
        """Predicate evaluates True => claim holds => not disproven."""
        result = handler._evaluate_claim(
            claim_predicate="result > 0",
            claim_text="always positive",
            result=10,
            input_args={"x": 5},
        )
        assert result is False  # Not disproven

    def test_predicate_claim_disproven(self, handler):
        """Predicate evaluates False => claim disproven."""
        result = handler._evaluate_claim(
            claim_predicate="result > 0",
            claim_text="always positive",
            result=-5,
            input_args={"x": -3},
        )
        assert result is True  # Disproven

    def test_predicate_with_input_args_in_context(self, handler):
        """Predicate should have access to input arguments."""
        result = handler._evaluate_claim(
            claim_predicate="result > x",
            claim_text="result always greater than input",
            result=3,
            input_args={"x": 5},
        )
        assert result is True  # 3 > 5 is False => disproven

    def test_predicate_failure_falls_back_to_legacy(self, handler):
        """Invalid predicate should fall back to legacy pattern matching."""
        result = handler._evaluate_claim(
            claim_predicate="invalid_syntax !!!",
            claim_text="The function always returns a positive number",
            result=-5,
            input_args={},
        )
        # Legacy should catch "always positive" pattern
        assert result is True

    def test_empty_predicate_uses_legacy(self, handler):
        """Empty predicate should use legacy pattern matching."""
        result = handler._evaluate_claim(
            claim_predicate="",
            claim_text="The function always returns a positive number",
            result=-5,
            input_args={},
        )
        assert result is True

    def test_none_predicate_uses_legacy(self, handler):
        """None predicate should use legacy pattern matching."""
        result = handler._evaluate_claim(
            claim_predicate=None,
            claim_text="The function always returns a positive number",
            result=-5,
            input_args={},
        )
        assert result is True


class TestRefuteLegacyEvaluateClaim:
    """Tests for _legacy_evaluate_claim method (all pattern branches)."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    def test_always_positive_disproven(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns a positive number", -5
        )
        assert result is True

    def test_always_positive_holds(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns a positive number", 5
        )
        assert result is False

    def test_always_negative_disproven(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns a negative number", 5
        )
        assert result is True

    def test_always_negative_holds(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns a negative number", -5
        )
        assert result is False

    def test_always_true_disproven(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns True", False
        )
        assert result is True

    def test_always_true_holds(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns True", True
        )
        assert result is False

    def test_always_false_disproven(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns False", True
        )
        assert result is True

    def test_always_false_holds(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns False", False
        )
        assert result is False

    def test_never_none_disproven(self, handler):
        result = handler._legacy_evaluate_claim("The function never returns None", None)
        assert result is True

    def test_never_none_holds(self, handler):
        result = handler._legacy_evaluate_claim("The function never returns None", 42)
        assert result is False

    def test_always_greater_than_disproven(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns a value greater than 10", 5
        )
        assert result is True

    def test_always_greater_than_holds(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns a value greater than 10", 15
        )
        assert result is False

    def test_always_less_than_disproven(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns a value less than 10", 15
        )
        assert result is True

    def test_always_less_than_holds(self, handler):
        result = handler._legacy_evaluate_claim(
            "The function always returns a value less than 10", 5
        )
        assert result is False

    def test_unrecognized_pattern_returns_false(self, handler):
        """Unrecognized claim patterns should return False (not disproven)."""
        result = handler._legacy_evaluate_claim(
            "The function does something unparseable", 42
        )
        assert result is False


class TestRefuteTestCounterexample:
    """Tests for test_counterexample method."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    def test_counterexample_disproven(self, handler):
        problem = _make_refute_problem()
        result = handler.test_counterexample(problem, {"x": -5})
        assert result["success"] is True
        assert result["claim_disproven"] is True
        assert result["result"] == -10

    def test_counterexample_not_disproven(self, handler):
        problem = _make_refute_problem()
        result = handler.test_counterexample(problem, {"x": 5})
        assert result["success"] is True
        assert result["claim_disproven"] is False
        assert result["result"] == 10

    def test_counterexample_execution_error(self, handler):
        problem = _make_refute_problem(
            reference_solution="def f(x):\n    raise ValueError('boom')"
        )
        result = handler.test_counterexample(problem, {"x": 1})
        assert result["success"] is False
        assert result["claim_disproven"] is False
        assert result["error"] is not None


class TestRefuteConfig:
    """Tests for Refute problem configuration."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    def test_get_problem_config_structure(self, handler):
        problem = _make_refute_problem()
        config = handler.get_problem_config(problem)
        assert "display" in config
        assert "input" in config
        assert "hints" in config
        assert "feedback" in config

    def test_get_problem_config_display(self, handler):
        problem = _make_refute_problem()
        config = handler.get_problem_config(problem)
        assert config["display"]["show_reference_code"] is True
        assert config["display"]["show_claim"] is True
        assert config["display"]["claim_text"] == problem.claim_text

    def test_get_problem_config_input_type(self, handler):
        problem = _make_refute_problem()
        config = handler.get_problem_config(problem)
        assert config["input"]["type"] == "json"
        assert len(config["input"]["parameters"]) == 1
        assert config["input"]["parameters"][0]["name"] == "x"

    def test_get_problem_config_placeholder(self, handler):
        problem = _make_refute_problem()
        config = handler.get_problem_config(problem)
        placeholder = config["input"]["placeholder"]
        assert '"x"' in placeholder
        assert "0" in placeholder  # int type default

    def test_get_problem_config_hints_enabled_with_counterexample(self, handler):
        problem = _make_refute_problem(expected_counterexample='{"x": -1}')
        config = handler.get_problem_config(problem)
        assert config["hints"]["enabled"] is True

    def test_get_problem_config_hints_disabled_without_counterexample(self, handler):
        problem = _make_refute_problem(expected_counterexample="")
        config = handler.get_problem_config(problem)
        assert config["hints"]["enabled"] is False

    def test_get_admin_config_structure(self, handler):
        config = handler.get_admin_config()
        assert "hidden_sections" in config
        assert "required_fields" in config
        assert "claim_predicate" in config["required_fields"]
        assert config["type_specific_section"] == "refute_config"

    def test_get_admin_config_supports(self, handler):
        config = handler.get_admin_config()
        assert config["supports"]["hints"] is True
        assert config["supports"]["segmentation"] is False
        assert config["supports"]["test_cases"] is False


class TestRefuteSerializeResult:
    """Tests for Refute result serialization."""

    @pytest.fixture
    def handler(self):
        return get_handler("refute")

    def test_serialize_result_with_data(self, handler):
        problem = _make_refute_problem()
        submission = MagicMock()
        submission.problem = problem
        submission.type_specific_data = {
            "input_args": {"x": -5},
            "result_value": -10,
            "claim_disproven": True,
            "execution_success": True,
            "execution_error": None,
        }

        result = handler.serialize_result(submission)
        assert result["input_args"] == {"x": -5}
        assert result["result_value"] == -10
        assert result["claim_disproven"] is True
        assert result["execution_success"] is True
        assert result["claim_text"] == problem.claim_text
        assert result["function_signature"] == problem.function_signature

    def test_serialize_result_no_data(self, handler):
        problem = _make_refute_problem()
        submission = MagicMock()
        submission.problem = problem
        submission.type_specific_data = None

        result = handler.serialize_result(submission)
        assert result["input_args"] == {}
        assert result["claim_disproven"] is False
        assert result["claim_text"] == problem.claim_text

    def test_serialize_result_execution_error(self, handler):
        problem = _make_refute_problem()
        submission = MagicMock()
        submission.problem = problem
        submission.type_specific_data = {
            "input_args": {"x": 1},
            "result_value": None,
            "claim_disproven": False,
            "execution_success": False,
            "execution_error": "ValueError: boom",
        }

        result = handler.serialize_result(submission)
        assert result["execution_success"] is False
        assert result["execution_error"] == "ValueError: boom"
