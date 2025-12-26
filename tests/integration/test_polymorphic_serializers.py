"""
Integration tests for polymorphic serializer behavior.

DRF serializers must correctly serialize polymorphic Problem instances
with their subclass-specific fields. Uses rest_polymorphic library.

Key serializers tested:
- ProblemPolymorphicListSerializer (maps to type-specific serializers)
- EiplProblemListSerializer
- McqProblemListSerializer
- PromptProblemListSerializer
"""

import pytest
from django.contrib.auth import get_user_model

from purplex.problems_app.models import EiplProblem, McqProblem, Problem, PromptProblem
from purplex.problems_app.serializers import (
    EiplProblemListSerializer,
    McqProblemListSerializer,
    McqProblemSerializer,
    ProblemPolymorphicListSerializer,
    ProblemSerializer,
    PromptProblemListSerializer,
)

User = get_user_model()

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def serializer_eipl(db):
    """EiPL problem for serializer tests."""
    return EiplProblem.objects.create(
        slug="serializer-eipl",
        title="Serializer EiPL",
        reference_solution="def multiply(a, b):\n    return a * b",
        function_signature="def multiply(a: int, b: int) -> int",
        function_name="multiply",
        segmentation_threshold=3,
        requires_highlevel_comprehension=True,
    )


@pytest.fixture
def serializer_mcq(db):
    """MCQ problem for serializer tests."""
    return McqProblem.objects.create(
        slug="serializer-mcq",
        title="Serializer MCQ",
        question_text="Which sorting algorithm is O(n log n)?",
        options=[
            {"id": "a", "text": "Bubble Sort", "is_correct": False},
            {"id": "b", "text": "Merge Sort", "is_correct": True},
            {"id": "c", "text": "Selection Sort", "is_correct": False},
        ],
        allow_multiple=False,
        shuffle_options=True,
    )


@pytest.fixture
def serializer_prompt(db):
    """Prompt problem for serializer tests."""
    return PromptProblem.objects.create(
        slug="serializer-prompt",
        title="Serializer Prompt",
        reference_solution='def describe():\n    return "chart"',
        function_signature="def describe() -> str",
        function_name="describe",
        image_url="https://example.com/chart.png",
        image_alt_text="A chart showing data",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Type-Specific Serializer Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestEiplProblemListSerializer:
    """Tests for EiplProblemListSerializer."""

    def test_serializes_eipl_specific_fields(self, serializer_eipl):
        """EiPL serializer should include function_name (list view optimization)."""
        serializer = EiplProblemListSerializer(serializer_eipl)
        data = serializer.data

        # Base fields
        assert data["slug"] == "serializer-eipl"
        assert data["title"] == "Serializer EiPL"
        assert data["problem_type"] == "eipl"

        # EiPL-specific field in list serializer
        assert data["function_name"] == "multiply"
        # Note: segmentation_enabled intentionally excluded from list view for performance

    def test_serializes_correct_problem_type(self, serializer_eipl):
        """problem_type should be 'eipl'."""
        serializer = EiplProblemListSerializer(serializer_eipl)
        assert serializer.data["problem_type"] == "eipl"


@pytest.mark.django_db
class TestMcqProblemListSerializer:
    """Tests for McqProblemListSerializer."""

    def test_serializes_mcq_specific_fields(self, serializer_mcq):
        """MCQ list serializer has minimal fields (list view optimization)."""
        serializer = McqProblemListSerializer(serializer_mcq)
        data = serializer.data

        # Base fields
        assert data["slug"] == "serializer-mcq"
        assert data["problem_type"] == "mcq"

        # Note: question_text and options intentionally excluded from list view
        # Use McqProblemSerializer for full details
        assert data["is_active"] is True

    def test_does_not_include_eipl_fields(self, serializer_mcq):
        """MCQ serializer should NOT have EiPL fields."""
        serializer = McqProblemListSerializer(serializer_mcq)
        data = serializer.data

        # These are EiPL fields, not MCQ
        assert "function_name" not in data
        assert "reference_solution" not in data


@pytest.mark.django_db
class TestPromptProblemListSerializer:
    """Tests for PromptProblemListSerializer."""

    def test_serializes_prompt_specific_fields(self, serializer_prompt):
        """Prompt serializer should include image_url."""
        serializer = PromptProblemListSerializer(serializer_prompt)
        data = serializer.data

        assert data["slug"] == "serializer-prompt"
        assert data["problem_type"] == "prompt"
        assert data["image_url"] == "https://example.com/chart.png"
        # Note: image_alt_text not in list serializer (only image_url)


# ─────────────────────────────────────────────────────────────────────────────
# Polymorphic List Serializer Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestProblemPolymorphicListSerializer:
    """
    Tests for ProblemPolymorphicListSerializer.

    This serializer uses rest_polymorphic to dispatch to type-specific
    serializers based on problem type.
    """

    def test_serializes_eipl_correctly(self, serializer_eipl):
        """Polymorphic serializer should dispatch to EiPL serializer."""
        serializer = ProblemPolymorphicListSerializer(serializer_eipl)
        data = serializer.data

        assert data["problem_type"] == "eipl"
        assert data["function_name"] == "multiply"
        # resourcetype added by rest_polymorphic
        assert data["resourcetype"] == "EiplProblem"

    def test_serializes_mcq_correctly(self, serializer_mcq):
        """Polymorphic serializer should dispatch to MCQ serializer."""
        serializer = ProblemPolymorphicListSerializer(serializer_mcq)
        data = serializer.data

        assert data["problem_type"] == "mcq"
        assert data["resourcetype"] == "McqProblem"

    def test_serializes_prompt_correctly(self, serializer_prompt):
        """Polymorphic serializer should dispatch to Prompt serializer."""
        serializer = ProblemPolymorphicListSerializer(serializer_prompt)
        data = serializer.data

        assert data["problem_type"] == "prompt"
        assert data["image_url"] == "https://example.com/chart.png"

    def test_serializes_mixed_queryset(
        self, serializer_eipl, serializer_mcq, serializer_prompt
    ):
        """
        Polymorphic serializer should handle queryset with mixed types.

        This is the critical test for API list endpoints.
        """
        # Query all problems
        problems = Problem.objects.all().order_by("slug")

        serializer = ProblemPolymorphicListSerializer(problems, many=True)
        data = serializer.data

        assert len(data) == 3

        # Find each type in serialized data
        eipl_data = next(d for d in data if d["problem_type"] == "eipl")
        mcq_data = next(d for d in data if d["problem_type"] == "mcq")
        prompt_data = next(d for d in data if d["problem_type"] == "prompt")

        # Each should have type-specific fields as per their list serializers
        assert "function_name" in eipl_data  # EiPL has function_name
        assert eipl_data["resourcetype"] == "EiplProblem"
        assert mcq_data["resourcetype"] == "McqProblem"
        assert "image_url" in prompt_data  # Prompt has image_url

    def test_resourcetype_field_present(self, serializer_eipl):
        """
        rest_polymorphic adds resourcetype field for type discrimination.
        """
        serializer = ProblemPolymorphicListSerializer(serializer_eipl)
        data = serializer.data

        # rest_polymorphic typically adds this
        # (exact field name depends on configuration)
        assert "problem_type" in data or "resourcetype" in data


# ─────────────────────────────────────────────────────────────────────────────
# Serialization from FK Traversal Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSerializationAfterFKTraversal:
    """
    Tests that problems can be serialized after FK traversal.

    When serializing a Submission, the related Problem must serialize
    with correct subclass fields.
    """

    def test_serialize_problem_from_queryset(
        self, serializer_eipl, serializer_mcq, serializer_prompt
    ):
        """
        Problem.objects.all() should return serializable instances.
        """
        problems = list(Problem.objects.all())

        for problem in problems:
            # Should be able to serialize with polymorphic serializer
            serializer = ProblemPolymorphicListSerializer(problem)
            data = serializer.data

            # Should have correct type
            assert data["problem_type"] == problem.problem_type

    def test_queryset_with_prefetch_still_serializes(
        self, serializer_eipl, serializer_mcq
    ):
        """
        Prefetched problems should still serialize correctly.

        This tests that prefetch doesn't break polymorphic serialization.
        """
        problems = Problem.objects.prefetch_related("categories").all()

        serializer = ProblemPolymorphicListSerializer(problems, many=True)
        data = serializer.data

        assert len(data) >= 2
        types = {d["problem_type"] for d in data}
        assert "eipl" in types
        assert "mcq" in types


# ─────────────────────────────────────────────────────────────────────────────
# Admin Serializer Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminSerializers:
    """
    Tests for admin-facing serializers with full field access.
    """

    def test_problem_serializer_includes_reference_solution(self, serializer_eipl):
        """Admin serializer should include reference_solution."""
        serializer = ProblemSerializer(serializer_eipl)
        data = serializer.data

        assert "reference_solution" in data
        assert "multiply" in data["reference_solution"]

    def test_mcq_serializer_includes_options(self, serializer_mcq):
        """MCQ serializer should include full options."""
        serializer = McqProblemSerializer(serializer_mcq)
        data = serializer.data

        assert "options" in data
        assert len(data["options"]) == 3
        assert any(o["is_correct"] for o in data["options"])


# ─────────────────────────────────────────────────────────────────────────────
# Edge Case Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSerializerEdgeCases:
    """Edge cases for polymorphic serialization."""

    def test_serialize_single_type_queryset(self, serializer_eipl):
        """Queryset with only one type should work."""
        problems = Problem.objects.filter(slug="serializer-eipl")

        serializer = ProblemPolymorphicListSerializer(problems, many=True)
        data = serializer.data

        assert len(data) == 1
        assert data[0]["problem_type"] == "eipl"

    def test_serialize_empty_queryset(self, db):
        """Empty queryset should serialize to empty list."""
        problems = Problem.objects.none()

        serializer = ProblemPolymorphicListSerializer(problems, many=True)
        data = serializer.data

        assert data == []

    def test_serialize_problem_with_null_optional_fields(self, db):
        """Problem with null optional fields should serialize."""
        eipl = EiplProblem.objects.create(
            slug="minimal-eipl",
            title="Minimal EiPL",
            reference_solution="def x(): pass",
            function_signature="def x() -> None",
            # function_name will be auto-extracted
        )

        serializer = ProblemPolymorphicListSerializer(eipl)
        data = serializer.data

        assert data["slug"] == "minimal-eipl"
        # function_name should be auto-extracted or empty
        assert "function_name" in data
