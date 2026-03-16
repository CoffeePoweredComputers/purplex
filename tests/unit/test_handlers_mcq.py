"""
Unit tests for the MCQ handler.
"""

import json
from unittest.mock import MagicMock

import pytest

from purplex.problems_app.handlers import (
    get_handler,
    get_registered_types,
    is_registered,
)
from purplex.problems_app.handlers.base import ActivityHandler

pytestmark = pytest.mark.unit


class TestMCQHandlerRegistry:
    """Tests for MCQ handler registration."""

    def test_mcq_handler_registered(self):
        """MCQ handler should be registered on import."""
        assert is_registered("mcq")

    def test_get_registered_types_includes_mcq(self):
        """get_registered_types should include 'mcq'."""
        types = get_registered_types()
        assert "mcq" in types

    def test_handler_inherits_from_activity_handler(self):
        """Handler should inherit from ActivityHandler."""
        handler = get_handler("mcq")
        assert isinstance(handler, ActivityHandler)


class TestMCQHandler:
    """Tests for the MCQ handler implementation."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    def test_type_name(self, handler):
        """Handler type_name should be 'mcq'."""
        assert handler.type_name == "mcq"


class TestMCQValidation:
    """Tests for MCQ input validation."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock McqProblem with options."""
        problem = MagicMock()
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {"id": "2", "text": "Option B", "is_correct": True},
            {"id": "3", "text": "Option C", "is_correct": False},
            {"id": "4", "text": "Option D", "is_correct": False},
        ]
        problem.allow_multiple = False
        return problem

    def test_validate_input_empty(self, handler, mock_problem):
        """Empty input should be invalid."""
        result = handler.validate_input("", mock_problem)
        assert not result.is_valid
        assert "select an answer" in result.error.lower()

    def test_validate_input_whitespace_only(self, handler, mock_problem):
        """Whitespace-only input should be invalid."""
        result = handler.validate_input("   ", mock_problem)
        assert not result.is_valid
        assert "select an answer" in result.error.lower()

    def test_validate_input_valid_option(self, handler, mock_problem):
        """Valid option ID should pass validation."""
        result = handler.validate_input("2", mock_problem)
        assert result.is_valid
        assert result.error is None

    def test_validate_input_invalid_option(self, handler, mock_problem):
        """Invalid option ID should fail validation."""
        result = handler.validate_input("99", mock_problem)
        assert not result.is_valid
        assert "Invalid option" in result.error

    def test_validate_input_no_options_configured(self, handler):
        """Should fail when problem has no MCQ options."""
        problem = MagicMock()
        problem.options = []
        problem.allow_multiple = False
        result = handler.validate_input("1", problem)
        assert not result.is_valid
        assert "no answer options" in result.error.lower()

    def test_validate_input_strips_whitespace(self, handler, mock_problem):
        """Validation should strip leading/trailing whitespace."""
        result = handler.validate_input("  2  ", mock_problem)
        assert result.is_valid


class TestMCQProcessSubmission:
    """Tests for MCQ submission processing."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock McqProblem with options."""
        problem = MagicMock()
        problem.slug = "test-mcq"
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {"id": "2", "text": "Option B", "is_correct": True},
            {"id": "3", "text": "Option C", "is_correct": False},
        ]
        problem.allow_multiple = False
        return problem

    @pytest.fixture
    def mock_submission(self, mock_problem):
        """Create a mock Submission."""
        submission = MagicMock()
        submission.submission_id = "test-uuid"
        submission.problem = mock_problem
        return submission

    def test_process_correct_answer(self, handler, mock_submission, mock_problem):
        """Processing correct answer should return success with is_correct=True."""
        result = handler.process_submission(mock_submission, "2", mock_problem)
        assert result.success is True
        assert result.type_specific_data["is_correct"] is True
        assert result.type_specific_data["selected_option"] == "2"
        assert result.type_specific_data["correct_option"] == "2"

    def test_process_incorrect_answer(self, handler, mock_submission, mock_problem):
        """Processing incorrect answer should return success with is_correct=False."""
        result = handler.process_submission(mock_submission, "1", mock_problem)
        assert result.success is True
        assert result.type_specific_data["is_correct"] is False
        assert result.type_specific_data["selected_option"] == "1"
        assert result.type_specific_data["correct_option"] == "2"

    def test_process_no_correct_answer_defined(self, handler, mock_submission):
        """Processing should fail when no correct answer is defined."""
        problem = MagicMock()
        problem.slug = "broken-mcq"
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {"id": "2", "text": "Option B", "is_correct": False},
        ]
        problem.allow_multiple = False
        result = handler.process_submission(mock_submission, "1", problem)
        assert result.success is False
        assert "no correct answer" in result.error.lower()


class TestMCQMultiSelectProcessSubmission:
    """Tests for MCQ multi-select grading logic."""

    pytestmark = [pytest.mark.unit]

    @pytest.fixture
    def handler(self):
        return get_handler("mcq")

    @pytest.fixture
    def multi_select_problem(self):
        """MCQ problem with allow_multiple=True, correct answers are 1 and 3."""
        problem = MagicMock()
        problem.slug = "multi-mcq"
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": True},
            {"id": "2", "text": "Option B", "is_correct": False},
            {"id": "3", "text": "Option C", "is_correct": True},
        ]
        problem.allow_multiple = True
        return problem

    @pytest.fixture
    def mock_submission(self, multi_select_problem):
        submission = MagicMock()
        submission.submission_id = "test-uuid"
        submission.problem = multi_select_problem
        return submission

    def test_all_correct_none_wrong(
        self, handler, mock_submission, multi_select_problem
    ):
        """Selecting exactly the correct options gives score 100 and passed=True."""
        result = handler.process_submission(
            mock_submission, json.dumps(["1", "3"]), multi_select_problem
        )
        assert result.success is True
        assert result.type_specific_data["is_correct"] is True
        assert result.type_specific_data["partial_score"] == 1.0
        assert set(result.type_specific_data["selected_options"]) == {"1", "3"}

    def test_partial_one_of_two(self, handler, mock_submission, multi_select_problem):
        """Selecting 1 of 2 correct gives score 50 and passed=False."""
        result = handler.process_submission(
            mock_submission, json.dumps(["1"]), multi_select_problem
        )
        assert result.success is True
        assert result.type_specific_data["is_correct"] is False
        assert result.type_specific_data["partial_score"] == 0.5

    def test_all_correct_plus_wrong(
        self, handler, mock_submission, multi_select_problem
    ):
        """Selecting all correct + one wrong: score 100% of correct selected, but not exact match."""
        result = handler.process_submission(
            mock_submission, json.dumps(["1", "2", "3"]), multi_select_problem
        )
        assert result.success is True
        assert result.type_specific_data["is_correct"] is False
        assert result.type_specific_data["partial_score"] == 1.0

    def test_none_correct_only_wrong(
        self, handler, mock_submission, multi_select_problem
    ):
        """Selecting only wrong options gives score 0."""
        result = handler.process_submission(
            mock_submission, json.dumps(["2"]), multi_select_problem
        )
        assert result.success is True
        assert result.type_specific_data["is_correct"] is False
        assert result.type_specific_data["partial_score"] == 0.0

    def test_single_select_backwards_compat(self, handler, mock_submission):
        """Plain string input still works for single-select MCQ."""
        problem = MagicMock()
        problem.slug = "single-mcq"
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {"id": "2", "text": "Option B", "is_correct": True},
        ]
        problem.allow_multiple = False
        result = handler.process_submission(mock_submission, "2", problem)
        assert result.success is True
        assert result.type_specific_data["is_correct"] is True

    def test_validation_empty_json_array(self, handler, multi_select_problem):
        """Empty JSON array should be rejected."""
        result = handler.validate_input(json.dumps([]), multi_select_problem)
        assert result.is_valid is False

    def test_validation_invalid_id_in_array(self, handler, multi_select_problem):
        """JSON array with an invalid option ID should be rejected."""
        result = handler.validate_input(json.dumps(["1", "99"]), multi_select_problem)
        assert result.is_valid is False
        assert "99" in result.error


class TestMCQGrading:
    """Tests for MCQ grading logic."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    @pytest.fixture
    def mock_submission(self):
        """Create a mock Submission."""
        submission = MagicMock()
        submission.passed_all_tests = True
        return submission

    def test_calculate_grade_complete_when_correct(self, handler, mock_submission):
        """Correct answer should be graded as complete."""
        mock_submission.passed_all_tests = True
        result = handler.calculate_grade(mock_submission)
        assert result == "complete"

    def test_calculate_grade_incomplete_when_incorrect(self, handler, mock_submission):
        """Incorrect answer should be graded as incomplete."""
        mock_submission.passed_all_tests = False
        result = handler.calculate_grade(mock_submission)
        assert result == "incomplete"

    def test_is_correct_when_passed(self, handler, mock_submission):
        """is_correct should return True when passed_all_tests is True."""
        mock_submission.passed_all_tests = True
        assert handler.is_correct(mock_submission) is True

    def test_is_correct_when_failed(self, handler, mock_submission):
        """is_correct should return False when passed_all_tests is False."""
        mock_submission.passed_all_tests = False
        assert handler.is_correct(mock_submission) is False


class TestMCQCompletion:
    """Tests for MCQ completion evaluation."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock Problem."""
        return MagicMock()

    @pytest.fixture
    def mock_submission(self, mock_problem):
        """Create a mock Submission."""
        submission = MagicMock()
        submission.problem = mock_problem
        submission.passed_all_tests = True
        return submission

    def test_evaluate_completion_complete_when_correct(
        self, handler, mock_submission, mock_problem
    ):
        """Completion should be complete when answer is correct."""
        mock_submission.passed_all_tests = True
        result = handler.evaluate_completion(mock_submission, mock_problem)
        assert result == "complete"

    def test_evaluate_completion_incomplete_when_incorrect(
        self, handler, mock_submission, mock_problem
    ):
        """Completion should be incomplete when answer is incorrect."""
        mock_submission.passed_all_tests = False
        result = handler.evaluate_completion(mock_submission, mock_problem)
        assert result == "incomplete"


class TestMCQDataExtraction:
    """Tests for MCQ data extraction methods."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock McqProblem with options."""
        problem = MagicMock()
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {
                "id": "2",
                "text": "Option B",
                "is_correct": True,
                "explanation": "B is correct because...",
            },
        ]
        problem.allow_multiple = False
        return problem

    @pytest.fixture
    def mock_submission(self, mock_problem):
        """Create a mock Submission."""
        submission = MagicMock()
        submission.raw_input = "2"
        submission.passed_all_tests = True
        submission.problem = mock_problem
        return submission

    def test_extract_variations(self, handler, mock_submission):
        """extract_variations should return selected answer."""
        result = handler.extract_variations(mock_submission)
        assert result == ["2"]

    def test_extract_variations_empty_input(self, handler):
        """extract_variations should handle empty input."""
        submission = MagicMock()
        submission.raw_input = ""
        result = handler.extract_variations(submission)
        assert result == []

    def test_count_variations(self, handler, mock_submission):
        """count_variations should always return 1 for MCQ."""
        assert handler.count_variations(mock_submission) == 1

    def test_count_passing_variations_correct(self, handler, mock_submission):
        """count_passing_variations should return 1 when correct."""
        mock_submission.passed_all_tests = True
        assert handler.count_passing_variations(mock_submission) == 1

    def test_count_passing_variations_incorrect(self, handler, mock_submission):
        """count_passing_variations should return 0 when incorrect."""
        mock_submission.passed_all_tests = False
        assert handler.count_passing_variations(mock_submission) == 0

    def test_extract_test_results(self, handler, mock_submission, mock_problem):
        """extract_test_results should return MCQ result structure."""
        results = handler.extract_test_results(mock_submission, mock_problem)
        assert len(results) == 1
        assert results[0]["isSuccessful"] is True
        assert results[0]["selected_answer"] == "Option B"
        assert results[0]["correct_answer"] == "Option B"
        assert "explanation" in results[0]


class TestMCQConfig:
    """Tests for MCQ problem configuration."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock McqProblem with options."""
        problem = MagicMock()
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {"id": "2", "text": "Option B", "is_correct": True},
        ]
        problem.allow_multiple = False
        problem.shuffle_options = False
        return problem

    def test_get_problem_config_structure(self, handler, mock_problem):
        """Config should have expected structure."""
        config = handler.get_problem_config(mock_problem)

        assert "display" in config
        assert "input" in config
        assert "hints" in config
        assert "feedback" in config

    def test_get_problem_config_display(self, handler, mock_problem):
        """Display config should hide code for MCQ."""
        config = handler.get_problem_config(mock_problem)

        assert config["display"]["show_reference_code"] is False
        assert config["display"]["show_function_signature"] is False

    def test_get_problem_config_input_type(self, handler, mock_problem):
        """Input config should be radio type for MCQ."""
        config = handler.get_problem_config(mock_problem)

        assert config["input"]["type"] == "radio"

    def test_get_problem_config_input_options(self, handler, mock_problem):
        """Input config should include MCQ options."""
        config = handler.get_problem_config(mock_problem)

        options = config["input"]["options"]
        assert len(options) == 2
        assert options[0]["id"] == "1"
        assert options[0]["text"] == "Option A"
        assert options[1]["id"] == "2"
        assert options[1]["text"] == "Option B"

    def test_get_problem_config_hints_disabled(self, handler, mock_problem):
        """Hints should be disabled for MCQ."""
        config = handler.get_problem_config(mock_problem)

        assert config["hints"]["available"] == []
        assert config["hints"]["enabled"] is False

    def test_get_problem_config_feedback(self, handler, mock_problem):
        """Feedback config should be appropriate for MCQ."""
        config = handler.get_problem_config(mock_problem)

        assert config["feedback"]["show_variations"] is False
        assert config["feedback"]["show_segmentation"] is False
        assert config["feedback"]["show_correct_answer"] is True

    def test_get_admin_config_structure(self, handler):
        """Admin config should have expected structure."""
        config = handler.get_admin_config()

        assert "hidden_sections" in config
        assert "required_fields" in config
        assert "optional_fields" in config
        assert "type_specific_section" in config
        assert "supports" in config

    def test_get_admin_config_hidden_sections(self, handler):
        """Admin config should hide irrelevant sections for MCQ."""
        config = handler.get_admin_config()

        assert "code_solution" in config["hidden_sections"]
        assert "test_cases" in config["hidden_sections"]
        assert "segmentation" in config["hidden_sections"]

    def test_get_admin_config_required_fields(self, handler):
        """Admin config should require MCQ-specific fields."""
        config = handler.get_admin_config()

        assert "title" in config["required_fields"]
        assert "options" in config["required_fields"]

    def test_get_admin_config_type_specific_section(self, handler):
        """Admin config should specify options as type-specific section."""
        config = handler.get_admin_config()

        assert config["type_specific_section"] == "options"

    def test_get_admin_config_supports(self, handler):
        """Admin config should indicate MCQ doesn't support hints/segmentation."""
        config = handler.get_admin_config()

        assert config["supports"]["hints"] is False
        assert config["supports"]["segmentation"] is False
        assert config["supports"]["test_cases"] is False


class TestMCQShuffleOptions:
    """Tests for MCQ option shuffling behavior."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    @pytest.fixture
    def mock_problem_no_shuffle(self):
        """MCQ problem with shuffle_options=False."""
        problem = MagicMock()
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {"id": "2", "text": "Option B", "is_correct": True},
            {"id": "3", "text": "Option C", "is_correct": False},
            {"id": "4", "text": "Option D", "is_correct": False},
        ]
        problem.allow_multiple = False
        problem.shuffle_options = False
        return problem

    @pytest.fixture
    def mock_problem_shuffle(self):
        """MCQ problem with shuffle_options=True."""
        problem = MagicMock()
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {"id": "2", "text": "Option B", "is_correct": True},
            {"id": "3", "text": "Option C", "is_correct": False},
            {"id": "4", "text": "Option D", "is_correct": False},
        ]
        problem.allow_multiple = False
        problem.shuffle_options = True
        return problem

    def test_no_shuffle_preserves_order(self, handler, mock_problem_no_shuffle):
        """When shuffle_options=False, options stay in original order."""
        config = handler.get_problem_config(mock_problem_no_shuffle)
        option_ids = [opt["id"] for opt in config["input"]["options"]]
        assert option_ids == ["1", "2", "3", "4"]

    def test_shuffle_preserves_all_options(self, handler, mock_problem_shuffle):
        """When shuffle_options=True, all options are still present."""
        config = handler.get_problem_config(mock_problem_shuffle)
        option_ids = sorted(opt["id"] for opt in config["input"]["options"])
        assert option_ids == ["1", "2", "3", "4"]

    def test_shuffle_changes_order(self, handler, mock_problem_shuffle):
        """When shuffle_options=True, order should differ from original at least sometimes."""
        original_order = ["1", "2", "3", "4"]
        saw_different_order = False
        # With 4 options, probability of same order is 1/24 per call.
        # After 10 calls, probability of never seeing a different order is (1/24)^10.
        for _ in range(10):
            config = handler.get_problem_config(mock_problem_shuffle)
            option_ids = [opt["id"] for opt in config["input"]["options"]]
            if option_ids != original_order:
                saw_different_order = True
                break
        assert saw_different_order, "Options were never shuffled after 10 attempts"

    def test_shuffle_does_not_mutate_original(self, handler, mock_problem_shuffle):
        """Shuffling should not mutate the problem's original options list."""
        original_options = [dict(opt) for opt in mock_problem_shuffle.options]
        handler.get_problem_config(mock_problem_shuffle)
        assert mock_problem_shuffle.options == original_options

    def test_shuffle_does_not_leak_is_correct(self, handler, mock_problem_shuffle):
        """Shuffled options should not expose is_correct to frontend."""
        config = handler.get_problem_config(mock_problem_shuffle)
        for opt in config["input"]["options"]:
            assert "is_correct" not in opt
            assert "explanation" not in opt

    def test_shuffle_with_multiselect(self, handler):
        """Shuffling works correctly with allow_multiple=True."""
        problem = MagicMock()
        problem.options = [
            {"id": "a", "text": "A", "is_correct": True},
            {"id": "b", "text": "B", "is_correct": True},
            {"id": "c", "text": "C", "is_correct": False},
        ]
        problem.allow_multiple = True
        problem.shuffle_options = True

        config = handler.get_problem_config(problem)
        option_ids = sorted(opt["id"] for opt in config["input"]["options"])
        assert option_ids == ["a", "b", "c"]
        assert config["input"]["type"] == "checkbox"


class TestMCQSerializeResult:
    """Tests for MCQ result serialization."""

    @pytest.fixture
    def handler(self):
        """Create an MCQ handler instance."""
        return get_handler("mcq")

    @pytest.fixture
    def mock_problem(self):
        """Create a mock McqProblem with options."""
        problem = MagicMock()
        problem.options = [
            {"id": "1", "text": "Option A", "is_correct": False},
            {
                "id": "2",
                "text": "Option B",
                "is_correct": True,
                "explanation": "B is correct",
            },
        ]
        problem.allow_multiple = False
        return problem

    @pytest.fixture
    def mock_submission(self, mock_problem):
        """Create a mock Submission."""
        submission = MagicMock()
        submission.raw_input = "2"
        submission.passed_all_tests = True
        submission.problem = mock_problem
        return submission

    def test_serialize_result_structure(self, handler, mock_submission):
        """Serialized result should have expected structure."""
        result = handler.serialize_result(mock_submission)

        assert "selected_option" in result
        assert "correct_option" in result
        assert "is_correct" in result

    def test_serialize_result_selected_option(self, handler, mock_submission):
        """Should serialize selected option correctly."""
        result = handler.serialize_result(mock_submission)

        assert result["selected_option"]["id"] == "2"
        assert result["selected_option"]["text"] == "Option B"

    def test_serialize_result_correct_option(self, handler, mock_submission):
        """Should serialize correct option correctly."""
        result = handler.serialize_result(mock_submission)

        assert result["correct_option"]["id"] == "2"
        assert result["correct_option"]["text"] == "Option B"
        assert result["correct_option"]["explanation"] == "B is correct"

    def test_serialize_result_is_correct(self, handler, mock_submission):
        """Should include is_correct flag."""
        result = handler.serialize_result(mock_submission)
        assert result["is_correct"] is True

    def test_serialize_result_incorrect_answer(self, handler, mock_submission):
        """Should handle incorrect answer serialization."""
        mock_submission.raw_input = "1"
        mock_submission.passed_all_tests = False
        result = handler.serialize_result(mock_submission)

        assert result["selected_option"]["id"] == "1"
        assert result["selected_option"]["text"] == "Option A"
        assert result["is_correct"] is False
