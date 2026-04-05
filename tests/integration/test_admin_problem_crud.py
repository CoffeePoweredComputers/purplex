"""
Regression tests for polymorphic problem creation via Admin API.

Bug Prevention:
- Bug 1: AdminProblemSerializer.create() used base Problem model instead of
  the specific polymorphic subclass (EiplProblem, McqProblem, etc.), causing
  'unexpected keyword arguments' errors for type-specific fields.

These tests verify each polymorphic problem type can be:
1. Created via API with ALL type-specific fields
2. Retrieved with all fields intact
3. Updated while preserving type-specific fields

The existing test_admin_api.py has basic creation tests, but these are more
comprehensive and specifically test the type-specific fields that were
broken by Bug 1.
"""

import pytest
from rest_framework import status

from purplex.problems_app.models import (
    DebugFixProblem,
    EiplProblem,
    McqProblem,
    ProbeableCodeProblem,
    ProbeableSpecProblem,
    PromptProblem,
    RefuteProblem,
)

pytestmark = pytest.mark.integration


# =============================================================================
# Bug 1 Regression: EiPL Problem with ALL Type-Specific Fields
# =============================================================================


@pytest.mark.django_db
class TestEiplProblemCreationRegression:
    """
    Regression tests for EiPL problem creation.

    Bug 1 caused: Problem() got unexpected keyword arguments: 'function_name',
    'function_signature', 'reference_solution', 'segmentation_config',
    'requires_highlevel_comprehension'

    These tests verify ALL EiPL-specific fields are accepted and saved.
    """

    def test_create_eipl_with_segmentation_config(self, admin_client):
        """EiPL with segmentation_threshold and requires_highlevel_comprehension."""
        data = {
            "title": "Regression EiPL Segmentation",
            "problem_type": "eipl",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": "beginner",
            "segmentation_threshold": 5,
            "requires_highlevel_comprehension": True,
        }

        response = admin_client.post("/api/admin/problems/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )
        assert response.data["function_name"] == "add"
        assert response.data["function_signature"] == "def add(a: int, b: int) -> int"

        # Verify database has correct model type and fields
        problem = EiplProblem.objects.get(title="Regression EiPL Segmentation")
        assert problem.function_name == "add"
        assert problem.segmentation_threshold == 5
        assert problem.requires_highlevel_comprehension is True

    def test_create_eipl_minimal_fields(self, admin_client):
        """EiPL with only required fields (defaults for optional)."""
        data = {
            "title": "Regression EiPL Minimal",
            "problem_type": "eipl",
            "reference_solution": "def foo(x: int) -> int:\n    return x",
            "function_signature": "def foo(x: int) -> int",
            "function_name": "foo",
            "difficulty": "beginner",
        }

        response = admin_client.post("/api/admin/problems/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )
        problem = EiplProblem.objects.get(title="Regression EiPL Minimal")
        assert problem.function_name == "foo"


# =============================================================================
# Bug 1 Regression: Prompt Problem with Image Fields
# =============================================================================


@pytest.mark.django_db
class TestPromptProblemCreationRegression:
    """
    Regression tests for Prompt problem creation.

    Prompt problems have image_url and image_alt_text fields that must be
    saved to PromptProblem model (not base Problem).

    KNOWN ISSUE: AdminProblemSerializer.create() hardcodes EiplProblem.objects.create()
    instead of dispatching to the correct model type. Prompt problems need their own
    AdminPromptProblemSerializer (similar to AdminMcqProblemSerializer).
    """

    def test_create_prompt_with_image_fields(self, admin_client):
        """Prompt problem with image_url and image_alt_text."""
        data = {
            "title": "Regression Prompt Image",
            "problem_type": "prompt",
            "reference_solution": "def analyze(img: str) -> str:\n    return 'result'",
            "function_signature": "def analyze(img: str) -> str",
            "function_name": "analyze",
            "difficulty": "intermediate",
            "image_url": "https://example.com/regression-test.png",
            "image_alt_text": "Regression test image description",
        }

        response = admin_client.post("/api/admin/problems/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = PromptProblem.objects.get(title="Regression Prompt Image")
        assert problem.image_url == "https://example.com/regression-test.png"
        assert problem.image_alt_text == "Regression test image description"

    def test_create_terminal_mode_prompt(self, admin_client):
        """Prompt problem with terminal display mode."""
        data = {
            "title": "Terminal Prompt",
            "problem_type": "prompt",
            "reference_solution": "def square(x):\n    return x**2",
            "function_signature": "def square(x: int) -> int",
            "function_name": "square",
            "difficulty": "intermediate",
            "display_mode": "terminal",
            "display_data": {
                "schema_version": 1,
                "runs": [
                    {
                        "interactions": [
                            {"type": "output", "text": "Enter: "},
                            {"type": "input", "text": "5"},
                            {"type": "output", "text": "25"},
                        ]
                    }
                ],
            },
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = PromptProblem.objects.get(title="Terminal Prompt")
        assert problem.display_mode == "terminal"
        assert len(problem.display_data["runs"]) == 1
        assert problem.image_url == ""

    def test_create_function_table_mode_prompt(self, admin_client):
        """Prompt problem with function table display mode."""
        data = {
            "title": "Table Prompt",
            "problem_type": "prompt",
            "reference_solution": "def square(x):\n    return x**2",
            "function_signature": "def square(x: int) -> int",
            "function_name": "square",
            "difficulty": "intermediate",
            "display_mode": "function_table",
            "display_data": {
                "schema_version": 1,
                "calls": [
                    {"args": [5], "return_value": 25},
                    {"args": [-3], "return_value": 9},
                ],
            },
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = PromptProblem.objects.get(title="Table Prompt")
        assert problem.display_mode == "function_table"
        assert len(problem.display_data["calls"]) == 2

    def test_default_display_mode_is_image(self, admin_client):
        """Omitting display_mode should default to image."""
        data = {
            "title": "Default Mode Prompt",
            "problem_type": "prompt",
            "reference_solution": "def f(): pass",
            "function_signature": "def f() -> None",
            "function_name": "f",
            "difficulty": "easy",
            "image_url": "https://example.com/img.png",
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = PromptProblem.objects.get(title="Default Mode Prompt")
        assert problem.display_mode == "image"


# =============================================================================
# Bug 1 Regression: DebugFix Problem with Buggy Code
# =============================================================================


@pytest.mark.django_db
class TestDebugFixProblemCreationRegression:
    """
    Regression tests for DebugFix problem creation.

    DebugFix problems have buggy_code and bug_hints
    fields that must be saved to DebugFixProblem model.

    KNOWN ISSUE: AdminProblemSerializer.create() hardcodes EiplProblem.objects.create()
    instead of dispatching to the correct model type. DebugFix problems need their own
    AdminDebugFixProblemSerializer (similar to AdminMcqProblemSerializer).
    """

    def test_create_debug_fix_with_buggy_code(self, admin_client):
        """DebugFix with buggy_code and bug_hints."""
        data = {
            "title": "Regression DebugFix",
            "problem_type": "debug_fix",
            "reference_solution": "def add(a: int, b: int) -> int:\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "buggy_code": "def add(a: int, b: int) -> int:\n    return a - b  # Bug!",
            "bug_hints": [
                {"level": 1, "text": "Check the operator"},
                {"level": 2, "text": "Should add, not subtract"},
            ],
            "difficulty": "intermediate",
        }

        response = admin_client.post("/api/admin/problems/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = DebugFixProblem.objects.get(title="Regression DebugFix")
        assert "return a - b" in problem.buggy_code
        assert len(problem.bug_hints) == 2


# =============================================================================
# Bug 1 Regression: MCQ Problem with Options
# =============================================================================


@pytest.mark.django_db
class TestMcqProblemCreationRegression:
    """
    Regression tests for MCQ problem creation.

    MCQ problems have question_text, options, and allow_multiple fields
    that must be saved to McqProblem model.
    """

    def test_create_mcq_with_all_fields(self, admin_client):
        """MCQ with options array and allow_multiple."""
        data = {
            "title": "Regression MCQ",
            "problem_type": "mcq",
            "question_text": "What is 2 + 2?",
            "options": [
                {"id": "a", "text": "3", "is_correct": False},
                {"id": "b", "text": "4", "is_correct": True},
                {"id": "c", "text": "5", "is_correct": False},
                {"id": "d", "text": "6", "is_correct": False},
            ],
            "allow_multiple": True,
            "difficulty": "beginner",
        }

        response = admin_client.post("/api/admin/problems/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = McqProblem.objects.get(title="Regression MCQ")
        assert problem.question_text == "What is 2 + 2?"
        assert len(problem.options) == 4
        assert problem.allow_multiple is True


# =============================================================================
# Bug 1 Regression: Refute Problem with Claim Fields
# =============================================================================


@pytest.mark.django_db
class TestRefuteProblemCreationRegression:
    """
    Regression tests for Refute problem creation.

    Refute problems have claim_text, claim_predicate, grading_mode, and
    expected_counterexample fields that must be saved to RefuteProblem model.
    """

    def test_create_refute_with_claim_fields(self, admin_client):
        """Refute problem with claim_text and expected_counterexample."""
        data = {
            "title": "Regression Refute",
            "problem_type": "refute",
            "question_text": "Find a counterexample to disprove this claim",
            "claim_text": "The function always returns a positive number",
            "claim_predicate": "result > 0",
            "reference_solution": "def f(x):\n    return x * 2",
            "function_signature": "def f(x: int) -> int",
            "grading_mode": "deterministic",
            "expected_counterexample": {"x": -5},
            "difficulty": "advanced",
        }

        response = admin_client.post("/api/admin/problems/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = RefuteProblem.objects.get(title="Regression Refute")
        assert problem.claim_text == "The function always returns a positive number"
        assert problem.claim_predicate == "result > 0"
        assert problem.grading_mode == "deterministic"
        assert problem.expected_counterexample == {"x": -5}


# =============================================================================
# Bug 1 Regression: ProbeableCode Problem with Probe Config
# =============================================================================


@pytest.mark.django_db
class TestProbeableCodeProblemCreationRegression:
    """
    Regression tests for ProbeableCode problem creation.

    ProbeableCode problems have probe_mode, max_probes, cooldown_attempts,
    and cooldown_refill fields that must be saved correctly.
    """

    def test_create_probeable_code_with_probe_config(self, admin_client):
        """ProbeableCode with probe_mode and max_probes."""
        data = {
            "title": "Regression ProbeableCode",
            "problem_type": "probeable_code",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "show_function_signature": False,
            "probe_mode": "cooldown",
            "max_probes": 15,
            "cooldown_attempts": 5,
            "cooldown_refill": 3,
            "difficulty": "intermediate",
        }

        response = admin_client.post("/api/admin/problems/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = ProbeableCodeProblem.objects.get(title="Regression ProbeableCode")
        assert problem.probe_mode == "cooldown"
        assert problem.max_probes == 15
        assert problem.cooldown_attempts == 5
        assert problem.cooldown_refill == 3
        assert problem.show_function_signature is False


# =============================================================================
# Bug 1 Regression: ProbeableSpec Problem
# =============================================================================


@pytest.mark.django_db
class TestProbeableSpecProblemCreationRegression:
    """
    Regression tests for ProbeableSpec problem creation.

    ProbeableSpec problems share probe fields with ProbeableCode but have
    different use case (spec discovery vs code understanding).

    KNOWN ISSUE: AdminProblemSerializer.create() hardcodes EiplProblem.objects.create()
    instead of dispatching to the correct model type. ProbeableSpec problems need their own
    AdminProbeableSpecProblemSerializer (similar to AdminProbeableCodeProblemSerializer).
    """

    def test_create_probeable_spec_with_probe_config(self, admin_client):
        """ProbeableSpec with probe configuration."""
        data = {
            "title": "Regression ProbeableSpec",
            "problem_type": "probeable_spec",
            "reference_solution": "def discover(x: int) -> int:\n    return x ** 2",
            "function_signature": "def discover(x: int) -> int",
            "function_name": "discover",
            "show_function_signature": True,
            "probe_mode": "explore",
            "max_probes": 20,
            "difficulty": "advanced",
        }

        response = admin_client.post("/api/admin/problems/", data, format="json")

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Failed: {response.data}"
        )

        problem = ProbeableSpecProblem.objects.get(title="Regression ProbeableSpec")
        assert problem.probe_mode == "explore"
        assert problem.max_probes == 20
        assert problem.show_function_signature is True


# =============================================================================
# Retrieval Tests: Verify Type-Specific Fields Are Returned
# =============================================================================


@pytest.mark.django_db
class TestPolymorphicProblemRetrieval:
    """
    Tests that verify type-specific fields are returned when retrieving
    problems via the API.
    """

    def test_get_eipl_returns_eipl_fields(self, admin_client, eipl_problem):
        """GET /api/admin/problems/<slug>/ returns EiPL-specific fields."""
        response = admin_client.get(f"/api/admin/problems/{eipl_problem.slug}/")

        assert response.status_code == status.HTTP_200_OK
        assert "function_name" in response.data
        assert "function_signature" in response.data
        assert "reference_solution" in response.data
        assert response.data["problem_type"] == "eipl"

    def test_get_mcq_returns_mcq_fields(self, admin_client, mcq_problem):
        """GET /api/admin/problems/<slug>/ returns MCQ-specific fields."""
        response = admin_client.get(f"/api/admin/problems/{mcq_problem.slug}/")

        assert response.status_code == status.HTTP_200_OK
        assert "question_text" in response.data
        assert "options" in response.data
        assert response.data["problem_type"] == "mcq"

    def test_list_returns_mixed_types_correctly(
        self, admin_client, eipl_problem, mcq_problem, refute_problem
    ):
        """GET /api/admin/problems/ returns correct fields for each type."""
        response = admin_client.get("/api/admin/problems/")

        assert response.status_code == status.HTTP_200_OK

        # Find each problem in response
        problems_by_slug = {p["slug"]: p for p in response.data}

        eipl_data = problems_by_slug.get(eipl_problem.slug)
        assert eipl_data is not None
        assert eipl_data["problem_type"] == "eipl"

        mcq_data = problems_by_slug.get(mcq_problem.slug)
        assert mcq_data is not None
        assert mcq_data["problem_type"] == "mcq"

        refute_data = problems_by_slug.get(refute_problem.slug)
        assert refute_data is not None
        assert refute_data["problem_type"] == "refute"


# =============================================================================
# Bug 1 Regression: Prompt Problem UPDATE Tests
# =============================================================================


@pytest.mark.django_db
class TestPromptProblemUpdateRegression:
    """
    UPDATE regression tests for Prompt problem.

    These tests verify type-specific fields (image_url, image_alt_text)
    are correctly updated via PUT /api/admin/problems/<slug>/.
    """

    def test_update_prompt_image_url(self, admin_client, prompt_problem):
        """Update image_url field and verify persistence."""
        data = {
            "title": prompt_problem.title,
            "reference_solution": prompt_problem.reference_solution,
            "function_signature": prompt_problem.function_signature,
            "function_name": prompt_problem.function_name,
            "difficulty": "intermediate",
            "image_url": "https://updated-example.com/new-image.png",
            "image_alt_text": prompt_problem.image_alt_text,
        }

        response = admin_client.put(
            f"/api/admin/problems/{prompt_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"
        assert response.data["image_url"] == "https://updated-example.com/new-image.png"

        prompt_problem.refresh_from_db()
        assert prompt_problem.image_url == "https://updated-example.com/new-image.png"

    def test_update_prompt_image_alt_text(self, admin_client, prompt_problem):
        """Update image_alt_text field and verify persistence."""
        data = {
            "title": prompt_problem.title,
            "reference_solution": prompt_problem.reference_solution,
            "function_signature": prompt_problem.function_signature,
            "function_name": prompt_problem.function_name,
            "difficulty": "intermediate",
            "image_url": prompt_problem.image_url,
            "image_alt_text": "Updated description of the image for accessibility",
        }

        response = admin_client.put(
            f"/api/admin/problems/{prompt_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"

        prompt_problem.refresh_from_db()
        assert (
            prompt_problem.image_alt_text
            == "Updated description of the image for accessibility"
        )

    def test_update_prompt_preserves_type_specific_fields_on_base_update(
        self, admin_client, prompt_problem
    ):
        """Update base fields and verify type-specific fields are preserved."""
        original_image_url = prompt_problem.image_url
        original_image_alt_text = prompt_problem.image_alt_text

        data = {
            "title": "Updated Prompt Title",
            "reference_solution": prompt_problem.reference_solution,
            "function_signature": prompt_problem.function_signature,
            "function_name": prompt_problem.function_name,
            "difficulty": "advanced",
            "image_url": prompt_problem.image_url,
            "image_alt_text": prompt_problem.image_alt_text,
        }

        response = admin_client.put(
            f"/api/admin/problems/{prompt_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"

        prompt_problem.refresh_from_db()
        assert prompt_problem.title == "Updated Prompt Title"
        assert prompt_problem.difficulty == "advanced"
        assert prompt_problem.image_url == original_image_url
        assert prompt_problem.image_alt_text == original_image_alt_text


# =============================================================================
# Bug 1 Regression: DebugFix Problem UPDATE Tests
# =============================================================================


@pytest.mark.django_db
class TestDebugFixProblemUpdateRegression:
    """
    UPDATE regression tests for DebugFix problem.

    These tests verify type-specific fields (buggy_code, bug_hints)
    are correctly updated via PUT.
    """

    def test_update_debug_fix_buggy_code(self, admin_client, debug_fix_problem):
        """Update buggy_code field and verify persistence."""
        data = {
            "title": debug_fix_problem.title,
            "reference_solution": debug_fix_problem.reference_solution,
            "function_signature": debug_fix_problem.function_signature,
            "function_name": debug_fix_problem.function_name,
            "difficulty": "intermediate",
            "buggy_code": "def add(a, b):\n    return a * b  # New bug: multiplication",
            "bug_hints": debug_fix_problem.bug_hints,
        }

        response = admin_client.put(
            f"/api/admin/problems/{debug_fix_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"

        debug_fix_problem.refresh_from_db()
        assert "return a * b" in debug_fix_problem.buggy_code

    def test_update_debug_fix_bug_hints(self, admin_client, debug_fix_problem):
        """Update bug_hints JSONField and verify persistence."""
        new_hints = [
            {"level": 1, "text": "Updated hint level 1"},
            {"level": 2, "text": "Updated hint level 2"},
            {"level": 3, "text": "Added third hint"},
        ]
        data = {
            "title": debug_fix_problem.title,
            "reference_solution": debug_fix_problem.reference_solution,
            "function_signature": debug_fix_problem.function_signature,
            "function_name": debug_fix_problem.function_name,
            "difficulty": "intermediate",
            "buggy_code": debug_fix_problem.buggy_code,
            "bug_hints": new_hints,
        }

        response = admin_client.put(
            f"/api/admin/problems/{debug_fix_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"

        debug_fix_problem.refresh_from_db()
        assert len(debug_fix_problem.bug_hints) == 3
        assert debug_fix_problem.bug_hints[2]["text"] == "Added third hint"

    def test_update_debug_fix_preserves_type_specific_fields_on_base_update(
        self, admin_client, debug_fix_problem
    ):
        """Update base fields and verify type-specific fields are preserved."""
        original_buggy_code = debug_fix_problem.buggy_code
        original_bug_hints = debug_fix_problem.bug_hints.copy()

        data = {
            "title": "Updated DebugFix Title",
            "reference_solution": debug_fix_problem.reference_solution,
            "function_signature": debug_fix_problem.function_signature,
            "function_name": debug_fix_problem.function_name,
            "difficulty": "advanced",
            "buggy_code": debug_fix_problem.buggy_code,
            "bug_hints": debug_fix_problem.bug_hints,
        }

        response = admin_client.put(
            f"/api/admin/problems/{debug_fix_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"

        debug_fix_problem.refresh_from_db()
        assert debug_fix_problem.title == "Updated DebugFix Title"
        assert debug_fix_problem.buggy_code == original_buggy_code
        assert debug_fix_problem.bug_hints == original_bug_hints


# =============================================================================
# Bug 1 Regression: ProbeableSpec Problem UPDATE Tests
# =============================================================================


@pytest.mark.django_db
class TestProbeableSpecProblemUpdateRegression:
    """
    UPDATE regression tests for ProbeableSpec problem.

    These tests verify type-specific fields (probe_mode, max_probes,
    cooldown_attempts, cooldown_refill, show_function_signature) are
    correctly updated via PUT.
    """

    def test_update_probeable_spec_probe_mode(
        self, admin_client, probeable_spec_problem
    ):
        """Update probe_mode field and verify persistence."""
        # Factory default is "cooldown", update to "explore"
        data = {
            "title": probeable_spec_problem.title,
            "reference_solution": probeable_spec_problem.reference_solution,
            "function_signature": probeable_spec_problem.function_signature,
            "function_name": probeable_spec_problem.function_name,
            "difficulty": "intermediate",
            "probe_mode": "explore",
            "max_probes": probeable_spec_problem.max_probes,
            "show_function_signature": probeable_spec_problem.show_function_signature,
        }

        response = admin_client.put(
            f"/api/admin/problems/{probeable_spec_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"
        assert response.data["probe_mode"] == "explore"

        probeable_spec_problem.refresh_from_db()
        assert probeable_spec_problem.probe_mode == "explore"

    def test_update_probeable_spec_probe_config(
        self, admin_client, probeable_spec_problem
    ):
        """Update probe configuration fields and verify persistence."""
        data = {
            "title": probeable_spec_problem.title,
            "reference_solution": probeable_spec_problem.reference_solution,
            "function_signature": probeable_spec_problem.function_signature,
            "function_name": probeable_spec_problem.function_name,
            "difficulty": "intermediate",
            "probe_mode": "cooldown",
            "max_probes": 25,
            "cooldown_attempts": 7,
            "cooldown_refill": 10,
            "show_function_signature": probeable_spec_problem.show_function_signature,
        }

        response = admin_client.put(
            f"/api/admin/problems/{probeable_spec_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"

        probeable_spec_problem.refresh_from_db()
        assert probeable_spec_problem.max_probes == 25
        assert probeable_spec_problem.cooldown_attempts == 7
        assert probeable_spec_problem.cooldown_refill == 10

    def test_update_probeable_spec_show_function_signature(
        self, admin_client, probeable_spec_problem
    ):
        """Update show_function_signature boolean and verify persistence."""
        # Factory default is True, update to False
        data = {
            "title": probeable_spec_problem.title,
            "reference_solution": probeable_spec_problem.reference_solution,
            "function_signature": probeable_spec_problem.function_signature,
            "function_name": probeable_spec_problem.function_name,
            "difficulty": "intermediate",
            "probe_mode": probeable_spec_problem.probe_mode,
            "max_probes": probeable_spec_problem.max_probes,
            "show_function_signature": False,
        }

        response = admin_client.put(
            f"/api/admin/problems/{probeable_spec_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"

        probeable_spec_problem.refresh_from_db()
        assert probeable_spec_problem.show_function_signature is False

    def test_update_probeable_spec_preserves_type_specific_fields_on_base_update(
        self, admin_client, probeable_spec_problem
    ):
        """Update base fields and verify type-specific fields are preserved."""
        original_probe_mode = probeable_spec_problem.probe_mode
        original_max_probes = probeable_spec_problem.max_probes

        data = {
            "title": "Updated ProbeableSpec Title",
            "reference_solution": probeable_spec_problem.reference_solution,
            "function_signature": probeable_spec_problem.function_signature,
            "function_name": probeable_spec_problem.function_name,
            "difficulty": "advanced",
            "probe_mode": probeable_spec_problem.probe_mode,
            "max_probes": probeable_spec_problem.max_probes,
            "show_function_signature": probeable_spec_problem.show_function_signature,
        }

        response = admin_client.put(
            f"/api/admin/problems/{probeable_spec_problem.slug}/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, f"Failed: {response.data}"

        probeable_spec_problem.refresh_from_db()
        assert probeable_spec_problem.title == "Updated ProbeableSpec Title"
        assert probeable_spec_problem.probe_mode == original_probe_mode
        assert probeable_spec_problem.max_probes == original_max_probes
