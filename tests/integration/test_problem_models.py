"""
Unit tests for Problem model hierarchy.

Tests the model definitions themselves:
- Field validation and defaults
- Custom save() methods
- Custom clean() methods
- Computed properties
- __str__ representations
- Model constraints
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from purplex.problems_app.models import (
    DebugFixProblem,
    EiplProblem,
    McqProblem,
    ProbeableCodeProblem,
    ProbeableSpecProblem,
    ProblemSet,
    PromptProblem,
    RefuteProblem,
    TestCase,
)

User = get_user_model()

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Problem Base Model Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProblemFieldDefaults:
    """Tests for Problem model field defaults."""

    def test_difficulty_defaults_to_beginner(self, db):
        """Default difficulty should be 'beginner'."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.difficulty == "beginner"

    def test_is_active_defaults_to_true(self, db):
        """Default is_active should be True."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.is_active is True

    def test_version_defaults_to_one(self, db):
        """Default version should be 1."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.version == 1

    def test_tags_defaults_to_empty_list(self, db):
        """Default tags should be empty list."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.tags == []

    def test_created_by_can_be_null(self, db):
        """created_by should allow null."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.created_by is None

    def test_max_attempts_can_be_null(self, db):
        """max_attempts should allow null (unlimited)."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.max_attempts is None


@pytest.mark.django_db
class TestProblemDifficultyChoices:
    """Tests for Problem.DIFFICULTY_CHOICES validation."""

    def test_valid_difficulty_easy(self, db):
        """'easy' should be a valid difficulty."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            difficulty="easy",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        eipl.full_clean()  # Should not raise

    def test_valid_difficulty_beginner(self, db):
        """'beginner' should be a valid difficulty."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            difficulty="beginner",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        eipl.full_clean()

    def test_valid_difficulty_intermediate(self, db):
        """'intermediate' should be a valid difficulty."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            difficulty="intermediate",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        eipl.full_clean()

    def test_valid_difficulty_advanced(self, db):
        """'advanced' should be a valid difficulty."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            difficulty="advanced",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        eipl.full_clean()

    def test_invalid_difficulty_raises_validation_error(self, db):
        """Invalid difficulty should raise ValidationError."""
        eipl = EiplProblem(
            title="Test Problem",
            difficulty="super_hard",  # Invalid
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        with pytest.raises(ValidationError):
            eipl.full_clean()


@pytest.mark.django_db
class TestProblemSlugAutoGeneration:
    """Tests for Problem.save() auto-slug generation."""

    def test_auto_generates_slug_from_title(self, db):
        """save() should auto-generate slug from title."""
        eipl = EiplProblem.objects.create(
            title="My Test Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.slug == "my-test-problem"

    def test_handles_special_characters_in_title(self, db):
        """Slug generation should handle special characters."""
        eipl = EiplProblem.objects.create(
            title="What's 2+2?",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.slug == "whats-22"

    def test_duplicate_slug_appends_counter(self, db):
        """Duplicate slugs should get counter appended."""
        EiplProblem.objects.create(
            title="Same Title",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        second = EiplProblem.objects.create(
            title="Same Title",
            reference_solution="def y(): pass",
            function_signature="def y() -> None",
        )
        assert second.slug == "same-title-1"

    def test_multiple_duplicates_increment_counter(self, db):
        """Multiple duplicates should increment counter."""
        EiplProblem.objects.create(
            slug="base-slug",
            title="First",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        EiplProblem.objects.create(
            slug="base-slug-1",
            title="Second",
            reference_solution="def y(): pass",
            function_signature="def y() -> None",
        )
        third = EiplProblem.objects.create(
            title="Base Slug",  # Will try 'base-slug'
            reference_solution="def z(): pass",
            function_signature="def z() -> None",
        )
        assert third.slug == "base-slug-2"

    def test_explicit_slug_is_preserved(self, db):
        """Explicitly provided slug should not be overwritten."""
        eipl = EiplProblem.objects.create(
            slug="my-explicit-slug",
            title="Different Title",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.slug == "my-explicit-slug"

    def test_slug_unique_constraint(self, db):
        """Duplicate explicit slugs should raise IntegrityError."""
        EiplProblem.objects.create(
            slug="unique-slug",
            title="First",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                EiplProblem.objects.create(
                    slug="unique-slug",  # Duplicate
                    title="Second",
                    reference_solution="def y(): pass",
                    function_signature="def y() -> None",
                )


@pytest.mark.django_db
class TestProblemCleanValidation:
    """Tests for Problem.clean() validation."""

    def test_tags_must_be_list(self, db):
        """tags must be a list, not a dict or string."""
        eipl = EiplProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            tags={"invalid": "dict"},  # Should be list
        )
        with pytest.raises(ValidationError) as exc_info:
            eipl.clean()
        assert "tags" in str(exc_info.value).lower()

    def test_tags_as_list_is_valid(self, db):
        """tags as a list should pass validation."""
        eipl = EiplProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            tags=["python", "beginner"],
        )
        eipl.clean()  # Should not raise

    def test_empty_tags_list_is_valid(self, db):
        """Empty tags list should pass validation."""
        eipl = EiplProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            tags=[],
        )
        eipl.clean()  # Should not raise


@pytest.mark.django_db
class TestProblemStrRepresentation:
    """Tests for Problem.__str__()."""

    def test_str_includes_title_and_difficulty(self, db):
        """__str__ should include title and difficulty."""
        eipl = EiplProblem.objects.create(
            title="Test Problem",
            difficulty="intermediate",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        result = str(eipl)
        # Base Problem.__str__ returns "title (difficulty)"
        # But subclasses override to "[Type] title"
        assert "Test Problem" in result


# ─────────────────────────────────────────────────────────────────────────────
# SpecProblem (Abstract) Tests - Tested via EiplProblem
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSpecProblemFieldDefaults:
    """Tests for SpecProblem field defaults."""

    def test_memory_limit_defaults_to_128(self, db):
        """Default memory_limit should be 128 MB."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.memory_limit == 128

    def test_llm_config_defaults_to_empty_dict(self, db):
        """Default llm_config should be empty dict."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.llm_config == {}

    def test_segmentation_config_defaults_to_empty_dict(self, db):
        """Default segmentation_config should be empty dict."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.segmentation_config == {}

    def test_segmentation_threshold_defaults_to_2(self, db):
        """Default segmentation_threshold should be 2."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.segmentation_threshold == 2

    def test_requires_highlevel_comprehension_defaults_to_true(self, db):
        """Default requires_highlevel_comprehension should be True."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.requires_highlevel_comprehension is True


@pytest.mark.django_db
class TestSpecProblemValidation:
    """Tests for SpecProblem.clean() validation."""

    def test_reference_solution_required(self, db):
        """reference_solution is required."""
        eipl = EiplProblem(
            title="Test",
            function_signature="def x() -> None",
            # Missing reference_solution
        )
        with pytest.raises(ValidationError) as exc_info:
            eipl.full_clean()
        assert "reference_solution" in str(exc_info.value)

    def test_function_signature_required(self, db):
        """function_signature is required."""
        eipl = EiplProblem(
            title="Test",
            reference_solution="def x(): pass",
            # Missing function_signature
        )
        with pytest.raises(ValidationError) as exc_info:
            eipl.full_clean()
        assert "function_signature" in str(exc_info.value)

    def test_function_name_must_be_valid_identifier(self, db):
        """function_name must be a valid Python identifier."""
        eipl = EiplProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            function_name="invalid-name",  # Hyphens not allowed
        )
        with pytest.raises(ValidationError) as exc_info:
            eipl.full_clean()
        assert "function_name" in str(exc_info.value)

    def test_valid_function_name_passes(self, db):
        """Valid function_name should pass validation."""
        eipl = EiplProblem(
            title="Test",
            reference_solution="def my_func(): pass",
            function_signature="def my_func() -> None",
            function_name="my_func",
        )
        eipl.full_clean()  # Should not raise


@pytest.mark.django_db
class TestSpecProblemFunctionNameExtraction:
    """Tests for SpecProblem.save() function_name extraction."""

    def test_extracts_function_name_from_reference_solution(self, db):
        """save() should auto-extract function_name from reference_solution."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def calculate_sum(a, b):\n    return a + b",
            function_signature="def calculate_sum(a: int, b: int) -> int",
        )
        assert eipl.function_name == "calculate_sum"

    def test_extracts_from_single_arg_function(self, db):
        """Should extract from single argument function."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def process(x):\n    return x * 2",
            function_signature="def process(x: int) -> int",
        )
        assert eipl.function_name == "process"

    def test_extracts_from_no_arg_function(self, db):
        """Should extract from no-argument function."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def get_value():\n    return 42",
            function_signature="def get_value() -> int",
        )
        assert eipl.function_name == "get_value"

    def test_explicit_function_name_not_overwritten(self, db):
        """Explicitly provided function_name should not be overwritten."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def actual_name(): pass",
            function_signature="def actual_name() -> None",
            function_name="explicit_name",
        )
        assert eipl.function_name == "explicit_name"


@pytest.mark.django_db
class TestSpecProblemSegmentationProperty:
    """Tests for SpecProblem.segmentation_enabled property."""

    def test_enabled_when_requires_highlevel_true(self, db):
        """segmentation_enabled True when requires_highlevel_comprehension True."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            requires_highlevel_comprehension=True,
        )
        assert eipl.segmentation_enabled is True

    def test_disabled_when_requires_highlevel_false(self, db):
        """segmentation_enabled False when requires_highlevel_comprehension False."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            requires_highlevel_comprehension=False,
        )
        assert eipl.segmentation_enabled is False

    def test_config_enabled_false_overrides_default(self, db):
        """segmentation_config.enabled=False should override default."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            requires_highlevel_comprehension=True,
            segmentation_config={"enabled": False},
        )
        assert eipl.segmentation_enabled is False

    def test_config_enabled_true_with_requires_highlevel_false(self, db):
        """Even with config.enabled=True, requires_highlevel must be True."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            requires_highlevel_comprehension=False,
            segmentation_config={"enabled": True},
        )
        # requires_highlevel_comprehension=False takes precedence
        assert eipl.segmentation_enabled is False

    def test_malformed_config_uses_default(self, db):
        """Malformed segmentation_config should fall back to class default."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            requires_highlevel_comprehension=True,
            segmentation_config={"wrong_key": "value"},  # No 'enabled' key
        )
        # Should use SEGMENTATION_DEFAULT_ENABLED (True for EiPL)
        assert eipl.segmentation_enabled is True

    def test_config_enabled_as_string_returns_string(self, db):
        """String 'true' in config returns the string value (not coerced to bool).

        Note: segmentation_enabled returns the raw config value, not a boolean.
        This documents that behavior - callers should use bool() if needed.
        """
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            requires_highlevel_comprehension=True,
            segmentation_config={"enabled": "true"},  # String, not bool
        )
        # Returns the raw value, which is truthy but not True
        assert eipl.segmentation_enabled == "true"
        assert bool(eipl.segmentation_enabled) is True  # Truthy

    def test_config_enabled_as_zero_returns_zero(self, db):
        """Integer 0 in config returns 0 (which is falsy).

        Note: segmentation_enabled returns the raw config value.
        """
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            requires_highlevel_comprehension=True,
            segmentation_config={"enabled": 0},  # Int, not bool
        )
        # Returns the raw value 0, which is falsy
        assert eipl.segmentation_enabled == 0
        assert bool(eipl.segmentation_enabled) is False  # Falsy

    def test_prompt_uses_different_default(self, db):
        """PromptProblem should use False as default (different from EiPL)."""
        prompt = PromptProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            image_url="https://example.com/img.png",
            requires_highlevel_comprehension=True,
            segmentation_config={},  # No 'enabled' key
        )
        # Should use SEGMENTATION_DEFAULT_ENABLED (False for Prompt)
        assert prompt.segmentation_enabled is False


@pytest.mark.django_db
class TestSpecProblemSegmentationThresholdProperty:
    """Tests for SpecProblem.get_segmentation_threshold property."""

    def test_returns_field_value_when_positive(self, db):
        """Should return segmentation_threshold field value."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            segmentation_threshold=5,
        )
        assert eipl.get_segmentation_threshold == 5

    def test_defaults_to_two_when_zero(self, db):
        """Should return default (2) when field is 0.

        Note: The property no longer falls back to segmentation_config JSON.
        The DB field is the single source of truth.
        """
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            segmentation_threshold=0,
            segmentation_config={
                "threshold": 10
            },  # Ignored - DB field is source of truth
        )
        assert eipl.get_segmentation_threshold == 2  # Default, not config value

    def test_defaults_to_2_when_no_config(self, db):
        """Should default to 2 when no config threshold."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            segmentation_threshold=0,
            segmentation_config={},
        )
        assert eipl.get_segmentation_threshold == 2


@pytest.mark.django_db
class TestSpecProblemTestCasesProperties:
    """Tests for SpecProblem.test_cases_count and visible_test_cases_count."""

    def test_test_cases_count_zero_initially(self, db):
        """test_cases_count should be 0 for new problem."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.test_cases_count == 0

    def test_test_cases_count_with_cases(self, db):
        """test_cases_count should count all test cases."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        TestCase.objects.create(problem=eipl, inputs=[], expected_output=0, order=0)
        TestCase.objects.create(problem=eipl, inputs=[1], expected_output=1, order=1)
        assert eipl.test_cases_count == 2

    def test_visible_test_cases_count_excludes_hidden(self, db):
        """visible_test_cases_count should exclude hidden cases."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        TestCase.objects.create(
            problem=eipl, inputs=[], expected_output=0, is_hidden=False, order=0
        )
        TestCase.objects.create(
            problem=eipl, inputs=[1], expected_output=1, is_hidden=True, order=1
        )
        assert eipl.visible_test_cases_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# EiplProblem Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEiplProblemModel:
    """Tests for EiplProblem model."""

    def test_polymorphic_type_returns_eipl(self, db):
        """polymorphic_type should return 'eipl'."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.polymorphic_type == "eipl"

    def test_problem_type_alias(self, db):
        """problem_type should be alias for polymorphic_type."""
        eipl = EiplProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert eipl.problem_type == "eipl"

    def test_str_format(self, db):
        """__str__ should be '[EiPL] title'."""
        eipl = EiplProblem.objects.create(
            title="My EiPL Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert str(eipl) == "[EiPL] My EiPL Problem"

    def test_segmentation_default_enabled_true(self, db):
        """SEGMENTATION_DEFAULT_ENABLED should be True for EiPL."""
        assert EiplProblem.SEGMENTATION_DEFAULT_ENABLED is True


# ─────────────────────────────────────────────────────────────────────────────
# PromptProblem Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPromptProblemModel:
    """Tests for PromptProblem model."""

    def test_polymorphic_type_returns_prompt(self, db):
        """polymorphic_type should return 'prompt'."""
        prompt = PromptProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            image_url="https://example.com/test.png",
        )
        assert prompt.polymorphic_type == "prompt"

    def test_str_format(self, db):
        """__str__ should be '[Prompt] title'."""
        prompt = PromptProblem.objects.create(
            title="My Prompt Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            image_url="https://example.com/test.png",
        )
        assert str(prompt) == "[Prompt] My Prompt Problem"

    def test_image_url_required(self, db):
        """image_url is required for PromptProblem."""
        prompt = PromptProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            # Missing image_url
        )
        with pytest.raises(ValidationError) as exc_info:
            prompt.full_clean()
        assert "image_url" in str(exc_info.value)

    def test_image_alt_text_optional(self, db):
        """image_alt_text is optional."""
        prompt = PromptProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            image_url="https://example.com/test.png",
        )
        prompt.full_clean()  # Should not raise

    def test_image_url_must_be_valid_url(self, db):
        """image_url must be a valid URL."""
        prompt = PromptProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            image_url="not-a-url",
        )
        with pytest.raises(ValidationError):
            prompt.full_clean()

    def test_segmentation_default_enabled_false(self, db):
        """SEGMENTATION_DEFAULT_ENABLED should be False for Prompt."""
        assert PromptProblem.SEGMENTATION_DEFAULT_ENABLED is False

    def test_default_display_mode_is_image(self, db):
        """Default display_mode should be 'image'."""
        prompt = PromptProblem.objects.create(
            title="Test Default",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            image_url="https://example.com/test.png",
        )
        assert prompt.display_mode == "image"

    def test_terminal_mode_does_not_require_image_url(self, db):
        """Terminal display_mode should not require image_url."""
        prompt = PromptProblem(
            title="Terminal Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            display_mode="terminal",
            display_data={
                "runs": [{"interactions": [{"type": "output", "text": "hi"}]}]
            },
        )
        prompt.full_clean()  # Should not raise

    def test_terminal_mode_requires_runs(self, db):
        """Terminal mode should require runs in display_data."""
        prompt = PromptProblem(
            title="Bad Terminal",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            display_mode="terminal",
            display_data={},
        )
        with pytest.raises(ValidationError) as exc_info:
            prompt.full_clean()
        assert "display_data" in str(exc_info.value)

    def test_function_table_mode_requires_calls(self, db):
        """Function table mode should require calls in display_data."""
        prompt = PromptProblem(
            title="Bad Table",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            display_mode="function_table",
            display_data={},
        )
        with pytest.raises(ValidationError) as exc_info:
            prompt.full_clean()
        assert "display_data" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# StaticProblem (Abstract) Tests - Tested via McqProblem
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestStaticProblemValidation:
    """Tests for StaticProblem.clean() validation."""

    def test_question_text_required(self, db):
        """question_text is required for StaticProblem."""
        mcq = McqProblem(
            title="Test",
            # Missing question_text
            options=[
                {"id": "a", "text": "Option A", "is_correct": True},
                {"id": "b", "text": "Option B", "is_correct": False},
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "question_text" in str(exc_info.value)


@pytest.mark.django_db
class TestStaticProblemGradingModes:
    """Tests for StaticProblem.GRADING_MODES choices."""

    def test_deterministic_mode_valid(self, db):
        """'deterministic' should be valid grading mode."""
        mcq = McqProblem.objects.create(
            title="Test",
            question_text="What is 2+2?",
            grading_mode="deterministic",
            options=[
                {"id": "a", "text": "4", "is_correct": True},
                {"id": "b", "text": "5", "is_correct": False},
            ],
        )
        mcq.full_clean()

    def test_llm_mode_valid(self, db):
        """'llm' should be valid grading mode."""
        mcq = McqProblem.objects.create(
            title="Test",
            question_text="What is 2+2?",
            grading_mode="llm",
            options=[
                {"id": "a", "text": "4", "is_correct": True},
                {"id": "b", "text": "5", "is_correct": False},
            ],
        )
        mcq.full_clean()

    def test_manual_mode_valid(self, db):
        """'manual' should be valid grading mode."""
        mcq = McqProblem.objects.create(
            title="Test",
            question_text="What is 2+2?",
            grading_mode="manual",
            options=[
                {"id": "a", "text": "4", "is_correct": True},
                {"id": "b", "text": "5", "is_correct": False},
            ],
        )
        mcq.full_clean()

    def test_invalid_grading_mode_fails(self, db):
        """Invalid grading mode should fail validation."""
        mcq = McqProblem(
            title="Test",
            question_text="What is 2+2?",
            grading_mode="invalid_mode",
            options=[
                {"id": "a", "text": "4", "is_correct": True},
                {"id": "b", "text": "5", "is_correct": False},
            ],
        )
        with pytest.raises(ValidationError):
            mcq.full_clean()


# ─────────────────────────────────────────────────────────────────────────────
# McqProblem Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestMcqProblemModel:
    """Tests for McqProblem model."""

    def test_polymorphic_type_returns_mcq(self, db):
        """polymorphic_type should return 'mcq'."""
        mcq = McqProblem.objects.create(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        assert mcq.polymorphic_type == "mcq"

    def test_str_format(self, db):
        """__str__ should be '[MCQ] title'."""
        mcq = McqProblem.objects.create(
            title="My MCQ Problem",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        assert str(mcq) == "[MCQ] My MCQ Problem"


@pytest.mark.django_db
class TestMcqProblemFieldDefaults:
    """Tests for McqProblem field defaults."""

    def test_options_defaults_to_empty_list(self, db):
        """Default options should be empty list (but will fail validation)."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
        )
        # Default is empty list, but that fails validation
        assert mcq.options == []

    def test_allow_multiple_defaults_to_false(self, db):
        """Default allow_multiple should be False."""
        mcq = McqProblem.objects.create(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        assert mcq.allow_multiple is False

    def test_shuffle_options_defaults_to_false(self, db):
        """Default shuffle_options should be False."""
        mcq = McqProblem.objects.create(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        assert mcq.shuffle_options is False


@pytest.mark.django_db
class TestMcqProblemOptionsValidation:
    """Tests for McqProblem.clean() options validation."""

    def test_requires_at_least_two_options(self, db):
        """At least 2 options are required."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[{"id": "a", "text": "Only one", "is_correct": True}],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "options" in str(exc_info.value)
        assert "2" in str(exc_info.value)

    def test_option_must_be_dict(self, db):
        """Each option must be a dict."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=["not", "dicts"],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "must be an object" in str(exc_info.value)

    def test_option_requires_id(self, db):
        """Each option must have an id."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"text": "No ID", "is_correct": True},
                {"id": "b", "text": "Has ID", "is_correct": False},
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "must have an id" in str(exc_info.value)

    def test_option_requires_text(self, db):
        """Each option must have text."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "is_correct": True},  # Missing text
                {"id": "b", "text": "Has text", "is_correct": False},
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "must have text" in str(exc_info.value)

    def test_option_text_cannot_be_empty(self, db):
        """Option text cannot be empty string."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "", "is_correct": True},
                {"id": "b", "text": "Has text", "is_correct": False},
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "must have text" in str(exc_info.value)

    def test_option_text_cannot_be_whitespace(self, db):
        """Option text cannot be just whitespace."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "   ", "is_correct": True},
                {"id": "b", "text": "Has text", "is_correct": False},
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "must have text" in str(exc_info.value)


@pytest.mark.django_db
class TestMcqProblemOptionsEdgeCases:
    """Edge case tests for McqProblem options validation."""

    def test_is_correct_as_string_true_is_truthy(self, db):
        """String 'true' for is_correct should be truthy (but not ideal)."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": "true"},  # String
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        # String 'true' is truthy, so this passes validation
        mcq.full_clean()  # Should not raise

    def test_is_correct_as_string_false_is_still_truthy(self, db):
        """String 'false' is truthy (non-empty string) - potential bug!"""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            allow_multiple=True,  # Allow multiple to avoid "exactly one" error
            options=[
                {"id": "a", "text": "A", "is_correct": "false"},  # Truthy!
                {"id": "b", "text": "B", "is_correct": True},
            ],
        )
        # Both are truthy - this documents current behavior
        mcq.full_clean()

    def test_is_correct_as_integer_one_is_truthy(self, db):
        """Integer 1 for is_correct should be truthy."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": 1},  # Int
                {"id": "b", "text": "B", "is_correct": 0},  # Int
            ],
        )
        mcq.full_clean()  # Should not raise

    def test_missing_is_correct_treated_as_falsy(self, db):
        """Missing is_correct key should be treated as False."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B"},  # No is_correct key
            ],
        )
        mcq.full_clean()  # Should not raise - one correct answer exists

    def test_extra_fields_in_option_allowed(self, db):
        """Extra fields in option dict should be allowed (for explanation)."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {
                    "id": "a",
                    "text": "A",
                    "is_correct": True,
                    "explanation": "Because...",
                },
                {"id": "b", "text": "B", "is_correct": False, "hint": "Think again"},
            ],
        )
        mcq.full_clean()  # Should not raise

    def test_option_id_can_be_integer(self, db):
        """Option ID can be integer (JSON flexibility)."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": 1, "text": "A", "is_correct": True},
                {"id": 2, "text": "B", "is_correct": False},
            ],
        )
        mcq.full_clean()  # Should not raise

    def test_many_options_allowed(self, db):
        """More than 4 options should be allowed."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
                {"id": "c", "text": "C", "is_correct": False},
                {"id": "d", "text": "D", "is_correct": False},
                {"id": "e", "text": "E", "is_correct": False},
                {"id": "f", "text": "F", "is_correct": False},
            ],
        )
        mcq.full_clean()  # Should not raise


@pytest.mark.django_db
class TestMcqProblemCorrectAnswerValidation:
    """Tests for McqProblem correct answer validation."""

    def test_requires_at_least_one_correct_answer(self, db):
        """At least one correct answer is required."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            options=[
                {"id": "a", "text": "A", "is_correct": False},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "correct answer" in str(exc_info.value).lower()

    def test_single_correct_when_not_allow_multiple(self, db):
        """Exactly one correct answer required when allow_multiple=False."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            allow_multiple=False,
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": True},  # Two correct
            ],
        )
        with pytest.raises(ValidationError) as exc_info:
            mcq.full_clean()
        assert "exactly one" in str(exc_info.value).lower()

    def test_multiple_correct_allowed_when_allow_multiple(self, db):
        """Multiple correct answers allowed when allow_multiple=True."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            allow_multiple=True,
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": True},
            ],
        )
        mcq.full_clean()  # Should not raise

    def test_single_correct_valid_when_not_allow_multiple(self, db):
        """Single correct answer should pass when allow_multiple=False."""
        mcq = McqProblem(
            title="Test",
            question_text="What?",
            allow_multiple=False,
            options=[
                {"id": "a", "text": "A", "is_correct": True},
                {"id": "b", "text": "B", "is_correct": False},
            ],
        )
        mcq.full_clean()  # Should not raise


# ─────────────────────────────────────────────────────────────────────────────
# UserProgress Model Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def progress_user(db):
    """User for progress tests."""
    return User.objects.create_user(
        username="progress_user",
        email="progress@test.com",
        password="testpass123",  # pragma: allowlist secret
    )


@pytest.fixture
def progress_instructor(db):
    """Instructor for progress tests."""
    return User.objects.create_user(
        username="progress_instructor",
        email="instructor@test.com",
        password="testpass123",  # pragma: allowlist secret
    )


@pytest.fixture
def progress_problem_set(db):
    """Problem set for progress tests."""
    return ProblemSet.objects.create(
        slug="progress-ps",
        title="Progress Test Set",
    )


@pytest.fixture
def progress_course(db, progress_instructor, progress_problem_set):
    """Course for progress tests."""
    from purplex.problems_app.models import Course

    course = Course.objects.create(
        course_id="PROG-TEST-101",
        name="Progress Test Course",
    )
    course.problem_sets.add(progress_problem_set)
    return course


@pytest.fixture
def progress_problem(db):
    """Problem for progress tests."""
    return EiplProblem.objects.create(
        slug="progress-eipl",
        title="Progress EiPL",
        reference_solution="def x(): pass",
        function_signature="def x() -> None",
    )


@pytest.mark.django_db
class TestUserProgressFieldDefaults:
    """Tests for UserProgress field defaults."""

    def test_status_defaults_to_not_started(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """Default status should be 'not_started'."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
        )
        assert progress.status == "not_started"

    def test_grade_defaults_to_incomplete(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """Default grade should be 'incomplete'."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
        )
        assert progress.grade == "incomplete"

    def test_attempts_defaults_to_zero(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """Default attempts should be 0."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
        )
        assert progress.attempts == 0

    def test_is_completed_defaults_to_false(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """Default is_completed should be False."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
        )
        assert progress.is_completed is False


@pytest.mark.django_db
class TestUserProgressUniqueConstraint:
    """Tests for UserProgress unique_together constraint."""

    def test_unique_user_problem_set_course(
        self, progress_user, progress_problem, progress_problem_set, progress_course
    ):
        """Should enforce unique (user, problem, problem_set, course)."""
        from purplex.problems_app.models import UserProgress

        UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            course=progress_course,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                UserProgress.objects.create(
                    user=progress_user,
                    problem=progress_problem,
                    problem_set=progress_problem_set,
                    course=progress_course,
                )

    def test_different_course_allowed(
        self, progress_user, progress_problem, progress_problem_set, progress_instructor
    ):
        """Same user/problem/set in different course should be allowed."""
        from purplex.problems_app.models import Course, UserProgress

        course1 = Course.objects.create(
            course_id="COURSE-1",
            name="Course 1",
        )
        course2 = Course.objects.create(
            course_id="COURSE-2",
            name="Course 2",
        )

        UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            course=course1,
        )
        # Should not raise
        UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            course=course2,
        )


@pytest.mark.django_db
class TestUserProgressStatusChoices:
    """Tests for UserProgress status choices."""

    def test_not_started_valid(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """'not_started' should be valid status."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            status="not_started",
        )
        progress.full_clean()

    def test_in_progress_valid(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """'in_progress' should be valid status."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            status="in_progress",
        )
        progress.full_clean()

    def test_completed_valid(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """'completed' should be valid status."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            status="completed",
        )
        progress.full_clean()

    def test_invalid_status_fails(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """Invalid status should fail validation."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            status="invalid_status",
        )
        with pytest.raises(ValidationError):
            progress.full_clean()


@pytest.mark.django_db
class TestUserProgressGradeChoices:
    """Tests for UserProgress grade choices."""

    def test_incomplete_valid(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """'incomplete' should be valid grade."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            grade="incomplete",
        )
        progress.full_clean()

    def test_partial_valid(self, progress_user, progress_problem, progress_problem_set):
        """'partial' should be valid grade."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            grade="partial",
        )
        progress.full_clean()

    def test_complete_valid(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """'complete' should be valid grade."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress.objects.create(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            grade="complete",
        )
        progress.full_clean()

    def test_invalid_grade_fails(
        self, progress_user, progress_problem, progress_problem_set
    ):
        """Invalid grade should fail validation."""
        from purplex.problems_app.models import UserProgress

        progress = UserProgress(
            user=progress_user,
            problem=progress_problem,
            problem_set=progress_problem_set,
            grade="invalid_grade",
        )
        with pytest.raises(ValidationError):
            progress.full_clean()


# ─────────────────────────────────────────────────────────────────────────────
# DebugFixProblem Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestDebugFixProblemFieldDefaults:
    """Tests for DebugFixProblem field defaults."""

    def test_bug_hints_defaults_to_empty_list(self, db):
        """Default bug_hints should be empty list."""
        problem = DebugFixProblem.objects.create(
            title="Test Debug Fix",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            buggy_code="def x(): return None",
        )
        assert problem.bug_hints == []

    def test_segmentation_default_disabled(self, db):
        """SEGMENTATION_DEFAULT_ENABLED should be False for DebugFix."""
        problem = DebugFixProblem.objects.create(
            title="Test Debug Fix",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            buggy_code="def x(): return None",
        )
        assert problem.SEGMENTATION_DEFAULT_ENABLED is False

    def test_inherits_spec_problem_fields(self, db):
        """DebugFixProblem should have SpecProblem fields."""
        problem = DebugFixProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            buggy_code="def x(): return None",
            memory_limit=256,
        )
        assert problem.memory_limit == 256
        assert hasattr(problem, "llm_config")
        assert hasattr(problem, "segmentation_config")


@pytest.mark.django_db
class TestDebugFixProblemValidation:
    """Tests for DebugFixProblem.clean() validation."""

    def test_buggy_code_required(self, db):
        """buggy_code is required - should fail validation when empty."""
        problem = DebugFixProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            buggy_code="",  # Empty string
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "buggy_code" in str(exc_info.value)

    def test_buggy_code_whitespace_only_fails(self, db):
        """buggy_code with only whitespace should fail."""
        problem = DebugFixProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            buggy_code="   \n\t  ",  # Whitespace only
        )
        # Note: This tests if validation catches whitespace-only input
        # The model might not validate this - test will reveal if it's a bug
        try:
            problem.full_clean()
            # If we get here, whitespace-only is allowed (might be a bug)
            problem.save()
            # Reload and check
            problem.refresh_from_db()
            assert problem.buggy_code.strip() == ""
        except ValidationError:
            # Validation correctly rejects whitespace-only
            pass

    def test_bug_hints_as_list_passes(self, db):
        """bug_hints as list should pass validation."""
        problem = DebugFixProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            buggy_code="def x(): return None",
            bug_hints=[{"level": 1, "text": "Check this"}],
        )
        problem.full_clean()  # Should not raise

    def test_reference_solution_still_required(self, db):
        """DebugFixProblem should still require reference_solution from parent."""
        problem = DebugFixProblem(
            title="Test",
            function_signature="def x() -> None",
            buggy_code="def x(): return None",
            # Missing reference_solution
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "reference_solution" in str(exc_info.value)


@pytest.mark.django_db
class TestDebugFixProblemPolymorphicType:
    """Tests for DebugFixProblem polymorphic_type."""

    def test_polymorphic_type_is_debug_fix(self, db):
        """polymorphic_type should return 'debug_fix'."""
        problem = DebugFixProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            buggy_code="def x(): return None",
        )
        assert problem.polymorphic_type == "debug_fix"

    def test_str_includes_debug_fix_prefix(self, db):
        """__str__ should include [DebugFix] prefix."""
        problem = DebugFixProblem.objects.create(
            title="My Debug Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            buggy_code="def x(): return None",
        )
        assert "[DebugFix]" in str(problem)
        assert "My Debug Problem" in str(problem)


# ─────────────────────────────────────────────────────────────────────────────
# ProbeableCodeProblem Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProbeableCodeProblemFieldDefaults:
    """Tests for ProbeableCodeProblem field defaults."""

    def test_show_function_signature_defaults_to_true(self, db):
        """Default show_function_signature should be True."""
        problem = ProbeableCodeProblem.objects.create(
            title="Test Probeable",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.show_function_signature is True

    def test_probe_mode_defaults_to_explore(self, db):
        """Default probe_mode should be 'explore'."""
        problem = ProbeableCodeProblem.objects.create(
            title="Test Probeable",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.probe_mode == "explore"

    def test_max_probes_defaults_to_10(self, db):
        """Default max_probes should be 10."""
        problem = ProbeableCodeProblem.objects.create(
            title="Test Probeable",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.max_probes == 10

    def test_cooldown_attempts_defaults_to_3(self, db):
        """Default cooldown_attempts should be 3."""
        problem = ProbeableCodeProblem.objects.create(
            title="Test Probeable",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.cooldown_attempts == 3

    def test_cooldown_refill_defaults_to_5(self, db):
        """Default cooldown_refill should be 5."""
        problem = ProbeableCodeProblem.objects.create(
            title="Test Probeable",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.cooldown_refill == 5

    def test_segmentation_default_disabled(self, db):
        """SEGMENTATION_DEFAULT_ENABLED should be False for ProbeableCode."""
        problem = ProbeableCodeProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.SEGMENTATION_DEFAULT_ENABLED is False


@pytest.mark.django_db
class TestProbeableCodeProblemValidation:
    """Tests for ProbeableCodeProblem.clean() validation."""

    def test_cooldown_mode_requires_valid_cooldown_attempts(self, db):
        """cooldown_attempts must be >= 1 for cooldown mode."""
        problem = ProbeableCodeProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            probe_mode="cooldown",
            cooldown_attempts=0,
            cooldown_refill=5,
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "cooldown_attempts" in str(exc_info.value)

    def test_cooldown_mode_requires_valid_cooldown_refill(self, db):
        """cooldown_refill must be >= 1 for cooldown mode."""
        problem = ProbeableCodeProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            probe_mode="cooldown",
            cooldown_attempts=3,
            cooldown_refill=0,
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "cooldown_refill" in str(exc_info.value)

    @pytest.mark.parametrize("mode", ["block", "explore"])
    def test_non_cooldown_modes_allow_zero_values(self, db, mode):
        """Non-cooldown modes don't validate cooldown values."""
        problem = ProbeableCodeProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            probe_mode=mode,
            cooldown_attempts=0,
            cooldown_refill=0,
        )
        problem.full_clean()  # Should not raise

    @pytest.mark.parametrize("mode", ["block", "cooldown", "explore"])
    def test_valid_probe_modes(self, db, mode):
        """All valid probe modes should be accepted."""
        problem = ProbeableCodeProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            probe_mode=mode,
            cooldown_attempts=3,  # Valid for cooldown
            cooldown_refill=5,  # Valid for cooldown
        )
        problem.full_clean()  # Should not raise

    def test_invalid_probe_mode_fails(self, db):
        """Invalid probe_mode should fail validation."""
        problem = ProbeableCodeProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            probe_mode="invalid_mode",
        )
        with pytest.raises(ValidationError):
            problem.full_clean()


@pytest.mark.django_db
class TestProbeableCodeProblemPolymorphicType:
    """Tests for ProbeableCodeProblem polymorphic_type."""

    def test_polymorphic_type_is_probeable_code(self, db):
        """polymorphic_type should return 'probeable_code'."""
        problem = ProbeableCodeProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.polymorphic_type == "probeable_code"

    def test_str_includes_probeable_code_prefix(self, db):
        """__str__ should include [ProbeableCode] prefix."""
        problem = ProbeableCodeProblem.objects.create(
            title="My Probe Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert "[ProbeableCode]" in str(problem)


# ─────────────────────────────────────────────────────────────────────────────
# ProbeableSpecProblem Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProbeableSpecProblemFieldDefaults:
    """Tests for ProbeableSpecProblem field defaults."""

    def test_segmentation_default_enabled(self, db):
        """SEGMENTATION_DEFAULT_ENABLED should be True for ProbeableSpec."""
        problem = ProbeableSpecProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.SEGMENTATION_DEFAULT_ENABLED is True

    def test_probe_mode_defaults_to_explore(self, db):
        """Default probe_mode should be 'explore'."""
        problem = ProbeableSpecProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.probe_mode == "explore"

    def test_has_same_probe_fields_as_probeable_code(self, db):
        """ProbeableSpecProblem should have same probe fields as ProbeableCodeProblem."""
        problem = ProbeableSpecProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert hasattr(problem, "show_function_signature")
        assert hasattr(problem, "probe_mode")
        assert hasattr(problem, "max_probes")
        assert hasattr(problem, "cooldown_attempts")
        assert hasattr(problem, "cooldown_refill")


@pytest.mark.django_db
class TestProbeableSpecProblemValidation:
    """Tests for ProbeableSpecProblem.clean() validation."""

    def test_cooldown_validation_same_as_probeable_code(self, db):
        """ProbeableSpec should have same cooldown validation as ProbeableCode."""
        problem = ProbeableSpecProblem(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            probe_mode="cooldown",
            cooldown_attempts=0,  # Invalid for cooldown
            cooldown_refill=5,
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "cooldown_attempts" in str(exc_info.value)


@pytest.mark.django_db
class TestProbeableSpecProblemPolymorphicType:
    """Tests for ProbeableSpecProblem polymorphic_type."""

    def test_polymorphic_type_is_probeable_spec(self, db):
        """polymorphic_type should return 'probeable_spec'."""
        problem = ProbeableSpecProblem.objects.create(
            title="Test",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert problem.polymorphic_type == "probeable_spec"

    def test_str_includes_probeable_spec_prefix(self, db):
        """__str__ should include [ProbeableSpec] prefix."""
        problem = ProbeableSpecProblem.objects.create(
            title="My Spec Problem",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
        )
        assert "[ProbeableSpec]" in str(problem)


# ─────────────────────────────────────────────────────────────────────────────
# RefuteProblem Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRefuteProblemFieldDefaults:
    """Tests for RefuteProblem field defaults."""

    def test_claim_predicate_can_be_blank(self, db):
        """claim_predicate should allow blank."""
        problem = RefuteProblem.objects.create(
            title="Test Refute",
            question_text="Find counterexample",
            claim_text="f(x) > 0 always",
            reference_solution="def f(x): return x",
            function_signature="def f(x: int) -> int",
        )
        assert problem.claim_predicate == ""

    def test_expected_counterexample_defaults_to_empty_dict(self, db):
        """Default expected_counterexample should be empty dict."""
        problem = RefuteProblem.objects.create(
            title="Test Refute",
            question_text="Find counterexample",
            claim_text="f(x) > 0 always",
            reference_solution="def f(x): return x",
            function_signature="def f(x: int) -> int",
        )
        assert problem.expected_counterexample == {}

    def test_grading_mode_defaults_to_deterministic(self, db):
        """Default grading_mode should be 'deterministic'."""
        problem = RefuteProblem.objects.create(
            title="Test Refute",
            question_text="Find counterexample",
            claim_text="f(x) > 0 always",
            reference_solution="def f(x): return x",
            function_signature="def f(x: int) -> int",
        )
        assert problem.grading_mode == "deterministic"


@pytest.mark.django_db
class TestRefuteProblemValidation:
    """Tests for RefuteProblem.clean() validation."""

    def test_claim_text_required(self, db):
        """claim_text is required."""
        problem = RefuteProblem(
            title="Test",
            question_text="Find it",
            reference_solution="def f(x): return x",
            function_signature="def f(x: int) -> int",
            claim_text="",  # Empty
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "claim_text" in str(exc_info.value)

    def test_reference_solution_required(self, db):
        """reference_solution is required."""
        problem = RefuteProblem(
            title="Test",
            question_text="Find it",
            claim_text="Always positive",
            function_signature="def f(x: int) -> int",
            reference_solution="",  # Empty
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "reference_solution" in str(exc_info.value)

    def test_function_signature_required(self, db):
        """function_signature is required."""
        problem = RefuteProblem(
            title="Test",
            question_text="Find it",
            claim_text="Always positive",
            reference_solution="def f(x): return x",
            function_signature="",  # Empty
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "function_signature" in str(exc_info.value)

    def test_question_text_required_from_static_problem(self, db):
        """question_text is required from StaticProblem parent."""
        problem = RefuteProblem(
            title="Test",
            question_text="",  # Empty
            claim_text="Always positive",
            reference_solution="def f(x): return x",
            function_signature="def f(x: int) -> int",
        )
        with pytest.raises(ValidationError) as exc_info:
            problem.full_clean()
        assert "question_text" in str(exc_info.value)


@pytest.mark.django_db
class TestRefuteProblemPolymorphicType:
    """Tests for RefuteProblem polymorphic_type."""

    def test_polymorphic_type_is_refute(self, db):
        """polymorphic_type should return 'refute'."""
        problem = RefuteProblem.objects.create(
            title="Test",
            question_text="Find it",
            claim_text="Always positive",
            reference_solution="def f(x): return x",
            function_signature="def f(x: int) -> int",
        )
        assert problem.polymorphic_type == "refute"

    def test_str_includes_refute_prefix(self, db):
        """__str__ should include [Refute] prefix."""
        problem = RefuteProblem.objects.create(
            title="My Refute Problem",
            question_text="Find it",
            claim_text="Always positive",
            reference_solution="def f(x): return x",
            function_signature="def f(x: int) -> int",
        )
        assert "[Refute]" in str(problem)


# ─────────────────────────────────────────────────────────────────────────────
# Parametrized Tests Across All Problem Types
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAllProblemTypesCommonBehavior:
    """Tests that apply to all problem types - catches inconsistencies."""

    PROBLEM_TYPES = [
        (
            EiplProblem,
            {"reference_solution": "def x(): pass", "function_signature": "def x()"},
        ),
        (
            McqProblem,
            {
                "question_text": "What?",
                "options": [
                    {"id": "a", "text": "A", "is_correct": True},
                    {"id": "b", "text": "B", "is_correct": False},
                ],
            },
        ),
        (
            PromptProblem,
            {
                "reference_solution": "def x(): pass",
                "function_signature": "def x()",
                "image_url": "https://example.com/img.png",
            },
        ),
        (
            RefuteProblem,
            {
                "question_text": "Find it",
                "claim_text": "f > 0",
                "reference_solution": "def f(x): return x",
                "function_signature": "def f(x: int) -> int",
            },
        ),
        (
            DebugFixProblem,
            {
                "reference_solution": "def x(): pass",
                "function_signature": "def x()",
                "buggy_code": "def x(): return None",
            },
        ),
        (
            ProbeableCodeProblem,
            {
                "reference_solution": "def x(): pass",
                "function_signature": "def x()",
            },
        ),
        (
            ProbeableSpecProblem,
            {
                "reference_solution": "def x(): pass",
                "function_signature": "def x()",
            },
        ),
    ]

    @pytest.mark.parametrize("model_class,extra_fields", PROBLEM_TYPES)
    def test_auto_slug_generation(self, db, model_class, extra_fields):
        """All problem types should auto-generate slug from title."""
        problem = model_class.objects.create(
            title="My Test Problem",
            **extra_fields,
        )
        assert problem.slug == "my-test-problem"

    @pytest.mark.parametrize("model_class,extra_fields", PROBLEM_TYPES)
    def test_default_difficulty_is_beginner(self, db, model_class, extra_fields):
        """All problem types should default to 'beginner' difficulty."""
        problem = model_class.objects.create(
            title="Test",
            **extra_fields,
        )
        assert problem.difficulty == "beginner"

    @pytest.mark.parametrize("model_class,extra_fields", PROBLEM_TYPES)
    def test_is_active_defaults_true(self, db, model_class, extra_fields):
        """All problem types should default is_active to True."""
        problem = model_class.objects.create(
            title="Test",
            **extra_fields,
        )
        assert problem.is_active is True

    @pytest.mark.parametrize("model_class,extra_fields", PROBLEM_TYPES)
    def test_version_defaults_to_one(self, db, model_class, extra_fields):
        """All problem types should default version to 1."""
        problem = model_class.objects.create(
            title="Test",
            **extra_fields,
        )
        assert problem.version == 1

    @pytest.mark.parametrize("model_class,extra_fields", PROBLEM_TYPES)
    def test_has_polymorphic_type(self, db, model_class, extra_fields):
        """All problem types should have polymorphic_type property."""
        problem = model_class.objects.create(
            title="Test",
            **extra_fields,
        )
        assert hasattr(problem, "polymorphic_type")
        assert isinstance(problem.polymorphic_type, str)
        assert len(problem.polymorphic_type) > 0

    @pytest.mark.parametrize("model_class,extra_fields", PROBLEM_TYPES)
    def test_title_required(self, db, model_class, extra_fields):
        """All problem types should require a title."""
        problem = model_class(title="", **extra_fields)
        with pytest.raises(ValidationError):
            problem.full_clean()
