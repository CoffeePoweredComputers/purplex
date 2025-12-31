"""
Unit tests for serializer validation logic.

Tests:
- MCQ problem validation (options, correct answers, unique IDs)
- Refute problem validation (required fields)
- Probeable code problem validation (probe modes)
- Probeable spec problem validation (probe modes, cooldown config)
- Admin problem validation (function signature type hints)
- Prompt problem validation (image_url required)
- DebugFix problem validation (buggy_code required)
"""

import pytest
from rest_framework.exceptions import ValidationError

from purplex.problems_app.serializers import (
    AdminDebugFixProblemSerializer,
    AdminMcqProblemSerializer,
    AdminProbeableCodeProblemSerializer,
    AdminProbeableSpecProblemSerializer,
    AdminProblemSerializer,
    AdminPromptProblemSerializer,
    AdminRefuteProblemSerializer,
    McqProblemSerializer,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────────
# MCQ Problem Serializer Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestMcqProblemSerializerValidation:
    """Tests for MCQ problem validation rules."""

    def test_valid_mcq_options(self):
        """Valid MCQ options should pass validation."""
        options = [
            {"id": "a", "text": "Option A", "is_correct": False},
            {"id": "b", "text": "Option B", "is_correct": True},
            {"id": "c", "text": "Option C", "is_correct": False},
        ]
        serializer = McqProblemSerializer()
        result = serializer.validate_options(options)
        assert result == options

    def test_options_missing_is_correct_treated_as_false(self):
        """Options without is_correct are treated as False (key not added).

        Note: The serializer doesn't explicitly default is_correct to False,
        it just treats missing is_correct as falsy during validation.
        """
        options = [
            {"id": "a", "text": "Option A"},
            {"id": "b", "text": "Option B", "is_correct": True},
        ]
        serializer = McqProblemSerializer()
        result = serializer.validate_options(options)
        # The key is not added - it's just treated as falsy during validation
        assert "is_correct" not in result[0]
        assert result[1]["is_correct"] is True

    def test_options_require_minimum_count(self):
        """At least 2 options should be required."""
        options = [{"id": "a", "text": "Only One Option", "is_correct": True}]
        serializer = McqProblemSerializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_options(options)
        assert "at least 2" in str(exc_info.value).lower()

    def test_options_require_correct_answer(self):
        """At least one correct answer is required."""
        options = [
            {"id": "a", "text": "Option A", "is_correct": False},
            {"id": "b", "text": "Option B", "is_correct": False},
            {"id": "c", "text": "Option C", "is_correct": False},
        ]
        serializer = McqProblemSerializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_options(options)
        assert "correct" in str(exc_info.value).lower()

    def test_options_require_unique_ids(self):
        """Option IDs must be unique."""
        options = [
            {"id": "a", "text": "First", "is_correct": True},
            {"id": "a", "text": "Duplicate ID", "is_correct": False},
        ]
        serializer = McqProblemSerializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_options(options)
        assert "unique" in str(exc_info.value).lower()

    def test_options_require_text(self):
        """Each option must have text."""
        options = [
            {"id": "a", "text": "", "is_correct": True},
            {"id": "b", "text": "Valid option", "is_correct": False},
        ]
        serializer = McqProblemSerializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_options(options)
        assert "text" in str(exc_info.value).lower()

    def test_options_require_id(self):
        """Each option must have an ID."""
        options = [
            {"id": "", "text": "No ID", "is_correct": True},
            {"id": "b", "text": "Has ID", "is_correct": False},
        ]
        serializer = McqProblemSerializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_options(options)
        assert "id" in str(exc_info.value).lower()


# ─────────────────────────────────────────────────────────────────────────────
# MCQ Serializer Full Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestMcqProblemSerializerFullValidation:
    """Tests for full MCQ serializer validation flow."""

    def test_valid_mcq_problem_data(self):
        """Valid complete MCQ data should pass validation."""
        data = {
            "title": "Test MCQ",
            "question_text": "What is the answer?",
            "options": [
                {"id": "a", "text": "Wrong", "is_correct": False},
                {"id": "b", "text": "Correct", "is_correct": True},
            ],
            "allow_multiple": False,
            "difficulty": "beginner",
        }
        serializer = AdminMcqProblemSerializer(data=data)
        assert serializer.is_valid()

    def test_mcq_missing_question_text(self):
        """MCQ without question_text should fail."""
        data = {
            "title": "Test MCQ",
            "options": [
                {"id": "a", "text": "Option A", "is_correct": True},
                {"id": "b", "text": "Option B", "is_correct": False},
            ],
        }
        serializer = AdminMcqProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "question_text" in serializer.errors

    def test_mcq_options_field_is_optional(self):
        """MCQ options field is not required at serializer level.

        Note: The options field has required=False in the serializer.
        The model uses a JSONField that may have a default value.
        Validation only runs if options are provided.
        """
        data = {
            "title": "Test MCQ",
            "question_text": "What is the answer?",
        }
        serializer = AdminMcqProblemSerializer(data=data)
        # Options not required - serializer is valid without them
        assert serializer.is_valid(), serializer.errors


# ─────────────────────────────────────────────────────────────────────────────
# Refute Problem Serializer Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestRefuteProblemSerializerValidation:
    """Tests for Refute problem validation rules."""

    def test_valid_refute_problem_data(self):
        """Valid Refute problem data should pass validation."""
        data = {
            "title": "Test Refute",
            "question_text": "Find a counterexample",
            "claim_text": "The function always returns positive",
            "claim_predicate": "result > 0",
            "reference_solution": "def f(x):\n    return x * 2",
            "function_signature": "def f(x: int) -> int",
            "grading_mode": "deterministic",
            "expected_counterexample": {"x": -5},
            "difficulty": "advanced",
        }
        serializer = AdminRefuteProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_refute_requires_claim_text(self):
        """Refute problem must have claim_text."""
        data = {
            "title": "Test Refute",
            "question_text": "Find a counterexample",
            "claim_predicate": "result > 0",
            "reference_solution": "def f(x): return x",
            "function_signature": "def f(x: int) -> int",
        }
        serializer = AdminRefuteProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "claim_text" in serializer.errors

    def test_refute_requires_function_signature(self):
        """Refute problem must have function_signature."""
        data = {
            "title": "Test Refute",
            "question_text": "Find a counterexample",
            "claim_text": "Returns positive",
            "claim_predicate": "result > 0",
            "reference_solution": "def f(x): return x",
        }
        serializer = AdminRefuteProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "function_signature" in serializer.errors


# ─────────────────────────────────────────────────────────────────────────────
# Probeable Code Serializer Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestProbeableCodeSerializerValidation:
    """Tests for Probeable Code problem validation rules."""

    def test_valid_probeable_code_data(self):
        """Valid Probeable Code data should pass validation."""
        data = {
            "title": "Test Probeable",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": "explore",
            "max_probes": 10,
            "difficulty": "intermediate",
        }
        serializer = AdminProbeableCodeProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_probeable_code_with_cooldown_mode(self):
        """Probeable Code in cooldown mode should pass validation."""
        data = {
            "title": "Cooldown Probeable",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": "cooldown",
            "max_probes": 10,
            "cooldown_attempts": 3,
            "cooldown_refill": 5,
            "difficulty": "intermediate",
        }
        serializer = AdminProbeableCodeProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_probeable_code_requires_reference_solution(self):
        """Probeable Code must have reference_solution."""
        data = {
            "title": "Test Probeable",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": "explore",
        }
        serializer = AdminProbeableCodeProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "reference_solution" in serializer.errors


# ─────────────────────────────────────────────────────────────────────────────
# Admin Problem Serializer (Type Hint Validation)
# ─────────────────────────────────────────────────────────────────────────────


class TestAdminProblemSerializerValidation:
    """Tests for Admin Problem serializer validation (EiPL type)."""

    def test_valid_eipl_problem_data(self):
        """Valid EiPL problem data should pass validation."""
        data = {
            "title": "Test EiPL Problem",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": "beginner",
        }
        serializer = AdminProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_function_signature_requires_type_hints(self):
        """Function signature without type hints should fail validation."""
        data = {
            "title": "No Type Hints",
            "reference_solution": "def test(): return 1",
            "function_signature": "def test() -> int",  # No param type hints
            "function_name": "test",
            "difficulty": "beginner",
        }
        serializer = AdminProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

    def test_function_signature_with_type_hints_passes(self):
        """Function signature with proper type hints should pass."""
        data = {
            "title": "Has Type Hints",
            "reference_solution": "def add(x, y): return x + y",
            "function_signature": "def add(x: int, y: int) -> int",
            "function_name": "add",
            "difficulty": "beginner",
        }
        serializer = AdminProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_missing_title_fails(self):
        """Problem without title should fail."""
        data = {
            "reference_solution": "def test(): return 1",
            "function_signature": "def test(x: int) -> int",
            "function_name": "test",
        }
        serializer = AdminProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_missing_reference_solution_fails(self):
        """Problem without reference_solution should fail."""
        data = {
            "title": "No Solution",
            "function_signature": "def test(x: int) -> int",
            "function_name": "test",
        }
        serializer = AdminProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "reference_solution" in serializer.errors


# ─────────────────────────────────────────────────────────────────────────────
# Edge Cases and Error Messages
# ─────────────────────────────────────────────────────────────────────────────


class TestSerializerErrorMessages:
    """Tests for clear, helpful error messages."""

    def test_mcq_error_message_mentions_options(self):
        """MCQ validation error should clearly mention options issue."""
        options = [{"id": "a", "text": "Only one"}]  # Missing is_correct, only 1 option
        serializer = McqProblemSerializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_options(options)
        error_msg = str(exc_info.value)
        assert "option" in error_msg.lower() or "2" in error_msg

    def test_empty_title_fails_validation(self):
        """Empty title should fail with clear message."""
        data = {
            "title": "",
            "reference_solution": "def x(a: int): return a",
            "function_signature": "def x(a: int) -> int",
            "function_name": "x",
        }
        serializer = AdminProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "title" in serializer.errors


# ─────────────────────────────────────────────────────────────────────────────
# Difficulty Level Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestDifficultyValidation:
    """Tests for difficulty level validation."""

    @pytest.mark.parametrize("difficulty", ["beginner", "intermediate", "advanced"])
    def test_valid_difficulty_levels(self, difficulty):
        """All valid difficulty levels should pass."""
        data = {
            "title": f"Test {difficulty}",
            "reference_solution": "def add(a, b): return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": difficulty,
        }
        serializer = AdminProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_invalid_difficulty_fails(self):
        """Invalid difficulty level should fail."""
        data = {
            "title": "Invalid Difficulty",
            "reference_solution": "def add(a, b): return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": "super_hard",  # Invalid
        }
        serializer = AdminProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "difficulty" in serializer.errors


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Problem Serializer Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestAdminPromptProblemSerializerValidation:
    """Tests for Prompt problem validation rules.

    Prompt problems have image_url (required) and image_alt_text (optional).
    """

    def test_valid_prompt_problem_data_with_all_fields(self):
        """Valid Prompt problem data with all optional fields should pass."""
        data = {
            "title": "Complete Prompt Problem",
            "description": "A detailed description",
            "reference_solution": "def analyze(img):\n    return 'result'",
            "function_signature": "def analyze(img: str) -> str",
            "function_name": "analyze",
            "image_url": "https://example.com/image.png",
            "image_alt_text": "Description of the image",
            "difficulty": "intermediate",
            "tags": ["python", "images"],
            "is_active": True,
        }
        serializer = AdminPromptProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_prompt_requires_title(self):
        """Prompt problem must have title."""
        data = {
            "reference_solution": "def analyze(img):\n    return 'result'",
            "function_signature": "def analyze(img: str) -> str",
            "function_name": "analyze",
            "image_url": "https://example.com/image.png",
            "difficulty": "intermediate",
        }
        serializer = AdminPromptProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_valid_prompt_problem_data(self):
        """Valid Prompt problem data should pass validation."""
        data = {
            "title": "Test Prompt Problem",
            "reference_solution": "def analyze(img):\n    return 'result'",
            "function_signature": "def analyze(img: str) -> str",
            "function_name": "analyze",
            "image_url": "https://example.com/image.png",
            "difficulty": "intermediate",
        }
        serializer = AdminPromptProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_prompt_requires_image_url(self):
        """Prompt problem must have image_url."""
        data = {
            "title": "Test Prompt Problem",
            "reference_solution": "def analyze(img):\n    return 'result'",
            "function_signature": "def analyze(img: str) -> str",
            "function_name": "analyze",
            "difficulty": "intermediate",
        }
        serializer = AdminPromptProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "image_url" in serializer.errors

    def test_prompt_requires_reference_solution(self):
        """Prompt problem must have reference_solution."""
        data = {
            "title": "Test Prompt Problem",
            "function_signature": "def analyze(img: str) -> str",
            "function_name": "analyze",
            "image_url": "https://example.com/image.png",
            "difficulty": "intermediate",
        }
        serializer = AdminPromptProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "reference_solution" in serializer.errors

    def test_prompt_requires_function_signature(self):
        """Prompt problem must have function_signature."""
        data = {
            "title": "Test Prompt Problem",
            "reference_solution": "def analyze(img):\n    return 'result'",
            "function_name": "analyze",
            "image_url": "https://example.com/image.png",
            "difficulty": "intermediate",
        }
        serializer = AdminPromptProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "function_signature" in serializer.errors

    def test_prompt_image_url_must_be_valid_url(self):
        """Prompt problem image_url must be a valid URL."""
        data = {
            "title": "Test Prompt Problem",
            "reference_solution": "def analyze(img):\n    return 'result'",
            "function_signature": "def analyze(img: str) -> str",
            "function_name": "analyze",
            "image_url": "not-a-valid-url",
            "difficulty": "intermediate",
        }
        serializer = AdminPromptProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "image_url" in serializer.errors

    def test_prompt_optional_image_alt_text(self):
        """Prompt problem should work without image_alt_text."""
        data = {
            "title": "Test Prompt Problem",
            "reference_solution": "def analyze(img):\n    return 'result'",
            "function_signature": "def analyze(img: str) -> str",
            "function_name": "analyze",
            "image_url": "https://example.com/image.png",
            "difficulty": "intermediate",
            # No image_alt_text - should still be valid
        }
        serializer = AdminPromptProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


# ─────────────────────────────────────────────────────────────────────────────
# DebugFix Problem Serializer Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestAdminDebugFixProblemSerializerValidation:
    """Tests for DebugFix problem validation rules.

    DebugFix problems have buggy_code (required), bug_hints (optional),
    and allow_complete_rewrite (optional, default True).
    """

    def test_valid_debug_fix_problem_data_with_all_fields(self):
        """Valid DebugFix problem data with all optional fields should pass."""
        data = {
            "title": "Complete DebugFix Problem",
            "description": "Fix the bug in this code",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "buggy_code": "def add(a, b):\n    return a - b  # Bug!",
            "bug_hints": [
                {"level": 1, "text": "Check the operator"},
                {"level": 2, "text": "Should add, not subtract"},
            ],
            "allow_complete_rewrite": False,
            "difficulty": "intermediate",
            "tags": ["python", "debugging"],
            "is_active": True,
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_debug_fix_requires_title(self):
        """DebugFix problem must have title."""
        data = {
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "buggy_code": "def add(a, b):\n    return a - b  # Bug!",
            "difficulty": "intermediate",
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_valid_debug_fix_problem_data(self):
        """Valid DebugFix problem data should pass validation."""
        data = {
            "title": "Test DebugFix Problem",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "buggy_code": "def add(a, b):\n    return a - b  # Bug!",
            "difficulty": "intermediate",
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_debug_fix_requires_buggy_code(self):
        """DebugFix problem must have buggy_code."""
        data = {
            "title": "Test DebugFix Problem",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": "intermediate",
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "buggy_code" in serializer.errors

    def test_debug_fix_requires_reference_solution(self):
        """DebugFix problem must have reference_solution."""
        data = {
            "title": "Test DebugFix Problem",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "buggy_code": "def add(a, b):\n    return a - b  # Bug!",
            "difficulty": "intermediate",
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "reference_solution" in serializer.errors

    def test_debug_fix_requires_function_signature(self):
        """DebugFix problem must have function_signature."""
        data = {
            "title": "Test DebugFix Problem",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_name": "add",
            "buggy_code": "def add(a, b):\n    return a - b  # Bug!",
            "difficulty": "intermediate",
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "function_signature" in serializer.errors

    def test_debug_fix_optional_bug_hints(self):
        """DebugFix problem should work without bug_hints."""
        data = {
            "title": "Test DebugFix Problem",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "buggy_code": "def add(a, b):\n    return a - b  # Bug!",
            "difficulty": "intermediate",
            # No bug_hints - should still be valid
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_debug_fix_optional_allow_complete_rewrite(self):
        """DebugFix problem should work without allow_complete_rewrite."""
        data = {
            "title": "Test DebugFix Problem",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "buggy_code": "def add(a, b):\n    return a - b  # Bug!",
            "difficulty": "intermediate",
            # No allow_complete_rewrite - should still be valid
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_debug_fix_bug_hints_accepts_valid_format(self):
        """DebugFix problem should accept valid bug_hints array."""
        data = {
            "title": "Test DebugFix Problem",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "buggy_code": "def add(a, b):\n    return a - b  # Bug!",
            "bug_hints": [
                {"level": 1, "text": "Check the operator"},
                {"level": 2, "text": "Should add, not subtract"},
            ],
            "allow_complete_rewrite": False,
            "difficulty": "intermediate",
        }
        serializer = AdminDebugFixProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors


# ─────────────────────────────────────────────────────────────────────────────
# ProbeableSpec Problem Serializer Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestAdminProbeableSpecProblemSerializerValidation:
    """Tests for ProbeableSpec problem validation rules.

    ProbeableSpec problems have probe_mode (explore/block/cooldown),
    max_probes, cooldown_attempts, and cooldown_refill.

    Note: Model-level validation (cooldown_attempts >= 1, cooldown_refill >= 1
    when probe_mode == "cooldown") is tested in integration tests because
    it requires database access (runs on .save(), not .is_valid()).
    """

    def test_valid_probeable_spec_problem_data_with_all_fields(self):
        """Valid ProbeableSpec problem data with all optional fields should pass."""
        data = {
            "title": "Complete ProbeableSpec Problem",
            "description": "Discover the function behavior",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "show_function_signature": False,
            "probe_mode": "cooldown",
            "max_probes": 15,
            "cooldown_attempts": 5,
            "cooldown_refill": 3,
            "difficulty": "advanced",
            "tags": ["python", "exploration"],
            "is_active": True,
        }
        serializer = AdminProbeableSpecProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_probeable_spec_requires_title(self):
        """ProbeableSpec problem must have title."""
        data = {
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": "explore",
            "difficulty": "intermediate",
        }
        serializer = AdminProbeableSpecProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "title" in serializer.errors

    def test_valid_probeable_spec_problem_data(self):
        """Valid ProbeableSpec problem data should pass validation."""
        data = {
            "title": "Test ProbeableSpec Problem",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": "explore",
            "difficulty": "intermediate",
        }
        serializer = AdminProbeableSpecProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_probeable_spec_requires_reference_solution(self):
        """ProbeableSpec problem must have reference_solution."""
        data = {
            "title": "Test ProbeableSpec Problem",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": "explore",
            "difficulty": "intermediate",
        }
        serializer = AdminProbeableSpecProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "reference_solution" in serializer.errors

    def test_probeable_spec_requires_function_signature(self):
        """ProbeableSpec problem must have function_signature."""
        data = {
            "title": "Test ProbeableSpec Problem",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_name": "mystery",
            "probe_mode": "explore",
            "difficulty": "intermediate",
        }
        serializer = AdminProbeableSpecProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "function_signature" in serializer.errors

    @pytest.mark.parametrize("probe_mode", ["block", "cooldown", "explore"])
    def test_probeable_spec_valid_probe_modes(self, probe_mode):
        """ProbeableSpec should accept all valid probe modes."""
        data = {
            "title": f"Test ProbeableSpec {probe_mode}",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": probe_mode,
            "difficulty": "intermediate",
        }
        serializer = AdminProbeableSpecProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_probeable_spec_invalid_probe_mode(self):
        """ProbeableSpec should reject invalid probe mode."""
        data = {
            "title": "Test ProbeableSpec Invalid",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": "invalid_mode",
            "difficulty": "intermediate",
        }
        serializer = AdminProbeableSpecProblemSerializer(data=data)
        assert not serializer.is_valid()
        assert "probe_mode" in serializer.errors

    def test_probeable_spec_with_cooldown_config(self):
        """ProbeableSpec in cooldown mode should accept cooldown fields."""
        data = {
            "title": "Cooldown ProbeableSpec",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "probe_mode": "cooldown",
            "max_probes": 15,
            "cooldown_attempts": 5,
            "cooldown_refill": 3,
            "show_function_signature": False,
            "difficulty": "advanced",
        }
        serializer = AdminProbeableSpecProblemSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
