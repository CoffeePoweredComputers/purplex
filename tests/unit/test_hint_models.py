"""
Test suite for ProblemHint model functionality and validation.

Converted from Django TestCase to pytest style.
"""

import pytest
from django.core.exceptions import ValidationError

from purplex.problems_app.models import ProblemHint
from tests.factories import EiplProblemFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestProblemHintCreation:
    """Tests for creating different hint types."""

    def test_variable_fade_hint_creation(self):
        """Test creating a valid variable fade hint."""
        problem = EiplProblemFactory()
        hint = ProblemHint.objects.create(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            min_attempts=3,
            content={
                "mappings": [{"from": "x", "to": "count"}, {"from": "y", "to": "total"}]
            },
        )

        assert hint.hint_type == "variable_fade"
        assert len(hint.content["mappings"]) == 2
        assert hint.content["mappings"][0]["from"] == "x"

    def test_subgoal_highlight_hint_creation(self):
        """Test creating a valid subgoal highlight hint."""
        problem = EiplProblemFactory()
        hint = ProblemHint.objects.create(
            problem=problem,
            hint_type="subgoal_highlight",
            is_enabled=True,
            min_attempts=2,
            content={
                "subgoals": [
                    {
                        "line_start": 1,
                        "line_end": 3,
                        "title": "Initialize variables",
                        "explanation": "Set up the initial state",
                    },
                    {
                        "line_start": 4,
                        "line_end": 6,
                        "title": "Process data",
                        "explanation": "Perform the main calculation",
                    },
                ]
            },
        )

        assert hint.hint_type == "subgoal_highlight"
        assert len(hint.content["subgoals"]) == 2
        assert hint.content["subgoals"][0]["title"] == "Initialize variables"

    def test_suggested_trace_hint_creation(self):
        """Test creating a valid suggested trace hint."""
        problem = EiplProblemFactory()
        hint = ProblemHint.objects.create(
            problem=problem,
            hint_type="suggested_trace",
            is_enabled=True,
            min_attempts=1,
            content={
                "suggested_call": "test_function()",
                "explanation": "Try tracing this function call",
            },
        )

        assert hint.hint_type == "suggested_trace"
        assert hint.content["suggested_call"] == "test_function()"


class TestProblemHintUniqueness:
    """Tests for hint type uniqueness constraints."""

    def test_hint_type_uniqueness(self):
        """Test that each hint type can only exist once per problem."""
        problem = EiplProblemFactory()
        ProblemHint.objects.create(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            content={"mappings": []},
        )

        # Attempting to create another variable_fade hint should fail
        with pytest.raises(Exception):  # IntegrityError due to unique_together
            ProblemHint.objects.create(
                problem=problem,
                hint_type="variable_fade",
                is_enabled=False,
                content={"mappings": []},
            )


class TestVariableFadeValidation:
    """Tests for variable fade hint validation."""

    def test_validation_missing_mappings(self):
        """Test validation fails when variable fade hint missing mappings."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            content={},  # Missing mappings
        )

        with pytest.raises(ValidationError) as exc_info:
            hint.clean()

        assert "Variable fade hint must contain mappings" in str(exc_info.value)

    def test_validation_invalid_mappings_format(self):
        """Test validation fails when mappings is not a list."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            content={"mappings": "not a list"},
        )

        with pytest.raises(ValidationError) as exc_info:
            hint.clean()

        assert "Mappings must be a list" in str(exc_info.value)

    def test_validation_invalid_mapping_structure(self):
        """Test validation fails when mapping lacks required fields."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            content={
                "mappings": [
                    {"from": "x"},  # Missing 'to' field
                    {"to": "total"},  # Missing 'from' field
                ]
            },
        )

        with pytest.raises(ValidationError) as exc_info:
            hint.clean()

        assert 'Each mapping must have "from" and "to" fields' in str(exc_info.value)


class TestSubgoalHighlightValidation:
    """Tests for subgoal highlight hint validation."""

    def test_validation_missing_subgoals(self):
        """Test validation fails when subgoal highlight hint missing subgoals."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem,
            hint_type="subgoal_highlight",
            is_enabled=True,
            content={},  # Missing subgoals
        )

        with pytest.raises(ValidationError) as exc_info:
            hint.clean()

        assert "Subgoal highlight hint must contain subgoals" in str(exc_info.value)

    def test_validation_invalid_subgoals_format(self):
        """Test validation fails when subgoals is not a list."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem,
            hint_type="subgoal_highlight",
            is_enabled=True,
            content={"subgoals": "not a list"},
        )

        with pytest.raises(ValidationError) as exc_info:
            hint.clean()

        assert "Subgoals must be a list" in str(exc_info.value)

    def test_validation_missing_required_fields(self):
        """Test validation fails when subgoal lacks required fields."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem,
            hint_type="subgoal_highlight",
            is_enabled=True,
            content={
                "subgoals": [
                    {
                        "line_start": 1,
                        "title": "Step 1",
                        # Missing line_end and explanation
                    }
                ]
            },
        )

        with pytest.raises(ValidationError) as exc_info:
            hint.clean()

        assert (
            "Each subgoal must have: line_start, line_end, title, explanation"
            in str(exc_info.value)
        )


class TestSuggestedTraceValidation:
    """Tests for suggested trace hint validation."""

    def test_validation_missing_suggested_call(self):
        """Test validation fails when suggested trace hint missing suggested_call."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem,
            hint_type="suggested_trace",
            is_enabled=True,
            content={},  # Missing suggested_call
        )

        with pytest.raises(ValidationError) as exc_info:
            hint.clean()

        assert "Suggested trace hint must contain suggested_call" in str(exc_info.value)

    def test_validation_invalid_suggested_call_type(self):
        """Test validation fails when suggested_call is not a string."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem,
            hint_type="suggested_trace",
            is_enabled=True,
            content={"suggested_call": 123},  # Not a string
        )

        with pytest.raises(ValidationError) as exc_info:
            hint.clean()

        assert "Suggested call must be a string" in str(exc_info.value)


class TestProblemHintOrdering:
    """Tests for hint ordering and string representation."""

    def test_hint_ordering_by_type(self):
        """Test that hints are ordered by hint_type."""
        problem = EiplProblemFactory()

        ProblemHint.objects.create(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            content={"mappings": []},
        )

        ProblemHint.objects.create(
            problem=problem,
            hint_type="subgoal_highlight",
            is_enabled=True,
            content={"subgoals": []},
        )

        ProblemHint.objects.create(
            problem=problem,
            hint_type="suggested_trace",
            is_enabled=True,
            content={"suggested_call": "test()"},
        )

        hints = list(ProblemHint.objects.filter(problem=problem))

        # Should be ordered alphabetically by hint_type
        expected_order = ["subgoal_highlight", "suggested_trace", "variable_fade"]
        actual_order = [hint.hint_type for hint in hints]

        assert actual_order == expected_order

    def test_hint_str_representation(self):
        """Test string representation of hint."""
        problem = EiplProblemFactory()
        hint = ProblemHint.objects.create(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            content={"mappings": []},
        )

        expected_str = f"{problem.title} - Variable Fade"
        assert str(hint) == expected_str


class TestProblemHintEdgeCases:
    """Tests for edge cases and special content scenarios."""

    def test_edge_case_empty_content(self):
        """Test hint creation with empty content (should fail validation)."""
        problem = EiplProblemFactory()
        hint = ProblemHint(
            problem=problem, hint_type="variable_fade", is_enabled=True, content={}
        )

        with pytest.raises(ValidationError):
            hint.clean()

    def test_edge_case_none_content(self):
        """Test hint creation with None content (should use default)."""
        problem = EiplProblemFactory()
        hint = ProblemHint.objects.create(
            problem=problem,
            hint_type="suggested_trace",
            is_enabled=False,
            # content will default to empty dict
        )

        # Should save but fail validation when cleaned
        with pytest.raises(ValidationError):
            hint.clean()

    def test_unicode_variable_names(self):
        """Test variable fade with Unicode variable names."""
        problem = EiplProblemFactory()
        hint = ProblemHint.objects.create(
            problem=problem,
            hint_type="variable_fade",
            is_enabled=True,
            content={
                "mappings": [
                    {"from": "α", "to": "alpha"},
                    {"from": "β", "to": "beta"},
                    {"from": "variable_名前", "to": "variable_name"},
                ]
            },
        )

        # Should not raise validation error
        hint.clean()
        assert len(hint.content["mappings"]) == 3

    def test_large_subgoal_list(self):
        """Test subgoal hint with many subgoals (performance consideration)."""
        problem = EiplProblemFactory()
        large_subgoals = []
        for i in range(100):
            large_subgoals.append(
                {
                    "line_start": i * 2 + 1,
                    "line_end": i * 2 + 2,
                    "title": f"Step {i + 1}",
                    "explanation": f"Explanation for step {i + 1}",
                }
            )

        hint = ProblemHint.objects.create(
            problem=problem,
            hint_type="subgoal_highlight",
            is_enabled=True,
            content={"subgoals": large_subgoals},
        )

        # Should not raise validation error
        hint.clean()
        assert len(hint.content["subgoals"]) == 100

    def test_concurrent_hint_creation(self):
        """Test creating hints concurrently (race condition simulation)."""
        from django.db import transaction

        problem = EiplProblemFactory()

        def create_hint():
            with transaction.atomic():
                return ProblemHint.objects.create(
                    problem=problem,
                    hint_type="variable_fade",
                    is_enabled=True,
                    content={"mappings": []},
                )

        # First creation should succeed
        hint1 = create_hint()
        assert hint1 is not None

        # Second creation should fail due to unique constraint
        with pytest.raises(Exception):
            create_hint()
