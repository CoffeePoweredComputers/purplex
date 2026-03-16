"""
Unit tests for the Probeable Spec handler.
"""

from unittest.mock import MagicMock

import pytest

from purplex.problems_app.handlers import get_handler
from purplex.problems_app.handlers.base import ActivityHandler

pytestmark = pytest.mark.unit


class TestProbeableSpecHandler:
    """Tests for Probeable Spec handler basics."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

    def test_type_name(self, handler):
        assert handler.type_name == "probeable_spec"

    def test_min_max_input_length_constants(self, handler):
        assert handler.MIN_INPUT_LENGTH == 10
        assert handler.MAX_INPUT_LENGTH == 1000

    def test_inherits_from_activity_handler(self, handler):
        assert isinstance(handler, ActivityHandler)


class TestProbeableSpecValidation:
    """Tests for Probeable Spec input validation."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

    def test_validate_input_too_short(self, handler):
        result = handler.validate_input("short", None)
        assert not result.is_valid
        assert "10 characters" in result.error

    def test_validate_input_at_minimum(self, handler):
        result = handler.validate_input("x" * 10, None)
        assert result.is_valid

    def test_validate_input_valid(self, handler):
        result = handler.validate_input(
            "This function takes a number and returns its double", None
        )
        assert result.is_valid

    def test_validate_input_too_long(self, handler):
        result = handler.validate_input("x" * 1001, None)
        assert not result.is_valid
        assert "1000 characters" in result.error

    def test_validate_input_at_maximum(self, handler):
        result = handler.validate_input("x" * 1000, None)
        assert result.is_valid

    def test_validate_input_strips_whitespace(self, handler):
        result = handler.validate_input("  abc  ", None)
        assert not result.is_valid


class TestProbeableSpecGrading:
    """Tests for Probeable Spec grading logic (3-level with segmentation)."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

    @pytest.fixture
    def mock_problem(self):
        problem = MagicMock()
        problem.segmentation_enabled = True
        problem.get_segmentation_threshold = 2
        return problem

    @pytest.fixture
    def mock_submission(self, mock_problem):
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
        mock_submission.passed_all_tests = False
        assert handler.calculate_grade(mock_submission) == "incomplete"

    def test_calculate_grade_complete_when_segmentation_disabled(
        self, handler, mock_submission
    ):
        mock_submission.problem.segmentation_enabled = False
        assert handler.calculate_grade(mock_submission) == "complete"

    def test_calculate_grade_incomplete_when_segmentation_missing(
        self, handler, mock_submission
    ):
        del mock_submission.segmentation
        assert handler.calculate_grade(mock_submission) == "incomplete"

    def test_calculate_grade_complete_when_segments_at_threshold(
        self, handler, mock_submission
    ):
        mock_submission.segmentation.segment_count = 2
        assert handler.calculate_grade(mock_submission) == "complete"

    def test_calculate_grade_complete_when_segments_below_threshold(
        self, handler, mock_submission
    ):
        mock_submission.segmentation.segment_count = 1
        assert handler.calculate_grade(mock_submission) == "complete"

    def test_calculate_grade_partial_when_segments_exceed_threshold(
        self, handler, mock_submission
    ):
        mock_submission.segmentation.segment_count = 3
        assert handler.calculate_grade(mock_submission) == "partial"

    def test_is_correct_true(self, handler, mock_submission):
        mock_submission.passed_all_tests = True
        assert handler.is_correct(mock_submission) is True

    def test_is_correct_false(self, handler, mock_submission):
        mock_submission.passed_all_tests = False
        assert handler.is_correct(mock_submission) is False


class TestProbeableSpecCompletion:
    """Tests for Probeable Spec completion evaluation."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

    @pytest.fixture
    def mock_problem(self):
        problem = MagicMock()
        problem.segmentation_enabled = True
        return problem

    @pytest.fixture
    def mock_submission(self, mock_problem):
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
        mock_submission.score = 80
        assert (
            handler.evaluate_completion(mock_submission, mock_problem) == "incomplete"
        )

    def test_evaluate_completion_complete_segmentation_disabled(
        self, handler, mock_submission, mock_problem
    ):
        mock_problem.segmentation_enabled = False
        assert handler.evaluate_completion(mock_submission, mock_problem) == "complete"

    def test_evaluate_completion_complete_segmentation_passed(
        self, handler, mock_submission, mock_problem
    ):
        mock_submission.segmentation.passed = True
        assert handler.evaluate_completion(mock_submission, mock_problem) == "complete"

    def test_evaluate_completion_partial_segmentation_failed(
        self, handler, mock_submission, mock_problem
    ):
        mock_submission.segmentation.passed = False
        assert handler.evaluate_completion(mock_submission, mock_problem) == "partial"

    def test_evaluate_completion_incomplete_missing_segmentation(
        self, handler, mock_submission, mock_problem
    ):
        del mock_submission.segmentation
        assert (
            handler.evaluate_completion(mock_submission, mock_problem) == "incomplete"
        )


class TestProbeableSpecDataExtraction:
    """Tests for Probeable Spec data extraction methods."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

    def test_extract_variations(self, handler):
        var1 = MagicMock()
        var1.generated_code = "def f(x): return x"
        var2 = MagicMock()
        var2.generated_code = "def f(x): return x * 2"

        mock_qs = MagicMock()
        mock_qs.order_by.return_value = [var1, var2]

        submission = MagicMock()
        submission.code_variations.all.return_value = mock_qs

        result = handler.extract_variations(submission)
        assert result == ["def f(x): return x", "def f(x): return x * 2"]

    def test_extract_variations_empty(self, handler):
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = []

        submission = MagicMock()
        submission.code_variations.all.return_value = mock_qs

        result = handler.extract_variations(submission)
        assert result == []

    def test_count_variations(self, handler):
        submission = MagicMock()
        submission.code_variations.count.return_value = 3
        assert handler.count_variations(submission) == 3

    def test_count_passing_variations(self, handler):
        submission = MagicMock()
        submission.code_variations.filter.return_value.count.return_value = 2
        assert handler.count_passing_variations(submission) == 2

    def test_count_passing_variations_none(self, handler):
        submission = MagicMock()
        submission.code_variations.filter.return_value.count.return_value = 0
        assert handler.count_passing_variations(submission) == 0


class TestProbeableSpecExtractTestResults:
    """Tests for Probeable Spec test result extraction."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

    def test_extract_test_results_with_test_executions(self, handler):
        """Should format test execution records."""
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
        variation.variation_index = 0
        variation.tests_passed = 1
        variation.tests_total = 1
        variation.test_executions.all.return_value = mock_test_execs

        mock_qs = MagicMock()
        mock_qs.order_by.return_value = [variation]

        submission = MagicMock()
        submission.code_variations.all.return_value = mock_qs

        problem = MagicMock()
        problem.function_name = "double"

        results = handler.extract_test_results(submission, problem)
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["testsPassed"] == 1
        assert results[0]["totalTests"] == 1
        assert results[0]["test_results"][0]["isSuccessful"] is True

    def test_extract_test_results_fallback_placeholder(self, handler):
        """Should create placeholder results when no TestExecution records exist."""
        mock_test_execs = MagicMock()
        mock_test_execs.order_by.return_value = mock_test_execs
        mock_test_execs.exists.return_value = False

        variation = MagicMock()
        variation.variation_index = 0
        variation.tests_passed = 2
        variation.tests_total = 3
        variation.test_executions.all.return_value = mock_test_execs

        mock_qs = MagicMock()
        mock_qs.order_by.return_value = [variation]

        submission = MagicMock()
        submission.code_variations.all.return_value = mock_qs

        problem = MagicMock()
        problem.function_name = "solve"

        results = handler.extract_test_results(submission, problem)
        assert len(results) == 1
        assert results[0]["success"] is False  # 2/3 != all
        assert len(results[0]["test_results"]) == 3
        # First 2 should be passing (tests_passed=2), last should fail
        assert results[0]["test_results"][0]["isSuccessful"] is True
        assert results[0]["test_results"][1]["isSuccessful"] is True
        assert results[0]["test_results"][2]["isSuccessful"] is False

    def test_extract_test_results_empty(self, handler):
        """Should return empty list when no variations."""
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = []

        submission = MagicMock()
        submission.code_variations.all.return_value = mock_qs

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
        variation.variation_index = 0
        variation.tests_passed = 1
        variation.tests_total = 1
        variation.test_executions.all.return_value = mock_test_execs

        mock_qs = MagicMock()
        mock_qs.order_by.return_value = [variation]

        submission = MagicMock()
        submission.code_variations.all.return_value = mock_qs

        problem = MagicMock()
        problem.function_name = "f"

        results = handler.extract_test_results(submission, problem)
        assert results[0]["test_results"] is results[0]["results"]


class TestProbeableSpecConfig:
    """Tests for Probeable Spec problem configuration."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

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
        problem.segmentation_enabled = True
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
        assert config["display"]["code_read_only"] is True

    def test_get_problem_config_input(self, handler, mock_problem):
        config = handler.get_problem_config(mock_problem)
        assert config["input"]["type"] == "probeable_spec"
        assert config["input"]["min_length"] == 10
        assert config["input"]["max_length"] == 1000

    def test_get_problem_config_probe_settings(self, handler):
        problem = MagicMock()
        problem.show_function_signature = True
        problem.probe_mode = "explore"
        problem.max_probes = 10
        problem.cooldown_attempts = 3
        problem.cooldown_refill = 5
        problem.function_signature = "f(x: int) -> int"
        problem.function_name = "f"

        config = handler.get_problem_config(problem)
        assert config["probe"]["enabled"] is True
        assert config["probe"]["mode"] == "explore"
        assert config["probe"]["max_probes"] == 10
        assert config["probe"]["function_signature"] == "f(x: int) -> int"

    def test_get_problem_config_segmentation_enabled(self, handler, mock_problem):
        mock_problem.segmentation_enabled = True
        config = handler.get_problem_config(mock_problem)
        assert config["feedback"]["show_segmentation"] is True
        assert config["feedback"]["show_variations"] is True

    def test_get_problem_config_segmentation_disabled(self, handler, mock_problem):
        mock_problem.segmentation_enabled = False
        config = handler.get_problem_config(mock_problem)
        assert config["feedback"]["show_segmentation"] is False

    def test_get_admin_config_supports(self, handler):
        config = handler.get_admin_config()
        assert config["supports"]["hints"] is False
        assert config["supports"]["segmentation"] is True
        assert config["supports"]["test_cases"] is True
        assert config["type_specific_section"] == "probeable_spec_config"


class TestProbeableSpecSerializeResult:
    """Tests for Probeable Spec result serialization."""

    @pytest.fixture
    def handler(self):
        return get_handler("probeable_spec")

    @pytest.fixture
    def mock_submission(self):
        submission = MagicMock()
        submission.problem = MagicMock()
        submission.problem.get_segmentation_threshold = 2
        submission.problem.function_name = "solve"

        # Mock variations
        var1 = MagicMock()
        var1.generated_code = "def solve(x): return x"
        var1.score = 100
        var1.tests_passed = 3
        var1.tests_total = 3
        var1.is_selected = True

        mock_test_execs = MagicMock()
        mock_test_execs.order_by.return_value = mock_test_execs
        mock_test_execs.exists.return_value = False
        mock_test_execs.__iter__ = lambda self: iter([])
        var1.test_executions.all.return_value = mock_test_execs

        mock_qs = MagicMock()
        mock_qs.order_by.return_value = [var1]
        mock_qs.__iter__ = lambda self: iter([var1])
        submission.code_variations.all.return_value = mock_qs

        # Mock segmentation
        seg = MagicMock()
        seg.segment_count = 2
        seg.comprehension_level = "relational"
        seg.passed = True
        seg.segments = [{"id": 1}]
        seg.code_mappings = [{"seg": 1}]
        seg.feedback_message = "Good"
        seg.confidence_score = 0.9
        seg.suggested_improvements = []
        submission.segmentation = seg

        return submission

    def test_serialize_result_structure(self, handler, mock_submission):
        result = handler.serialize_result(mock_submission)
        assert "variations" in result
        assert "test_results" in result
        assert "segmentation" in result

    def test_serialize_result_variations(self, handler, mock_submission):
        result = handler.serialize_result(mock_submission)
        assert len(result["variations"]) == 1
        assert result["variations"][0]["code"] == "def solve(x): return x"
        assert result["variations"][0]["score"] == 100

    def test_serialize_result_segmentation(self, handler, mock_submission):
        result = handler.serialize_result(mock_submission)
        seg = result["segmentation"]
        assert seg["segment_count"] == 2
        assert seg["comprehension_level"] == "relational"
        assert seg["passed"] is True
        assert seg["threshold"] == 2

    def test_serialize_result_no_segmentation(self, handler):
        submission = MagicMock()
        submission.problem = MagicMock()
        submission.problem.function_name = "f"

        mock_qs = MagicMock()
        mock_qs.order_by.return_value = []
        mock_qs.__iter__ = lambda self: iter([])
        submission.code_variations.all.return_value = mock_qs

        del submission.segmentation

        result = handler.serialize_result(submission)
        assert result["segmentation"] is None

    def test_serialize_result_segmentation_details(self, handler, mock_submission):
        """Segmentation should include full data for SegmentAnalysisModal."""
        result = handler.serialize_result(mock_submission)
        seg = result["segmentation"]
        assert "segments" in seg
        assert "code_mappings" in seg
        assert "feedback_message" in seg
        assert "confidence_score" in seg
        assert "suggested_improvements" in seg
