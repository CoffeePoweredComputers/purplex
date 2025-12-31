"""
Tests for Admin API endpoints.

Tests:
- Problem list/create API
- Problem detail API (get, update, delete)
- Problem set list/create API
- Problem set detail API
- Test case API
"""

import pytest
from rest_framework import status

from purplex.problems_app.models import (
    EiplProblem,
    McqProblem,
    ProbeableCodeProblem,
    Problem,
    ProblemSet,
    RefuteProblem,
    TestCase,
)

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# Admin Problem List API
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminProblemListAPI:
    """Tests for GET /api/admin/problems/."""

    def test_list_problems_requires_auth(self, api_client):
        """Unauthenticated requests should fail."""
        response = api_client.get("/api/admin/problems/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_problems_requires_admin(self, authenticated_client):
        """Non-admin users should be denied."""
        response = authenticated_client.get("/api/admin/problems/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_problems_success(self, admin_client, eipl_problem, mcq_problem):
        """Admin can list all problems."""
        response = admin_client.get("/api/admin/problems/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        # Should contain at least the fixture problems
        slugs = [p["slug"] for p in response.data]
        assert eipl_problem.slug in slugs
        assert mcq_problem.slug in slugs

    def test_list_problems_includes_all_types(
        self, admin_client, eipl_problem, mcq_problem, refute_problem
    ):
        """Response includes different problem types."""
        response = admin_client.get("/api/admin/problems/")
        assert response.status_code == status.HTTP_200_OK

        # Find each problem type in response by checking type-specific fields
        slugs = [p["slug"] for p in response.data]
        assert eipl_problem.slug in slugs
        assert mcq_problem.slug in slugs
        assert refute_problem.slug in slugs


# ─────────────────────────────────────────────────────────────────────────────
# Admin Problem Create API
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminProblemCreateAPI:
    """Tests for POST /api/admin/problems/."""

    def test_create_eipl_problem(self, admin_client):
        """Create an EiPL problem."""
        data = {
            "title": "Test EiPL Problem",
            "problem_type": "eipl",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": "beginner",
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Test EiPL Problem"
        assert EiplProblem.objects.filter(title="Test EiPL Problem").exists()

    def test_create_mcq_problem(self, admin_client):
        """Create an MCQ problem."""
        data = {
            "title": "Test MCQ Problem",
            "problem_type": "mcq",
            "question_text": "What is 2 + 2?",
            "options": [
                {"id": "a", "text": "3", "is_correct": False},
                {"id": "b", "text": "4", "is_correct": True},
                {"id": "c", "text": "5", "is_correct": False},
            ],
            "allow_multiple": False,
            "difficulty": "beginner",
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Test MCQ Problem"
        assert McqProblem.objects.filter(title="Test MCQ Problem").exists()

    def test_create_probeable_code_problem(self, admin_client):
        """Create a Probeable Code problem."""
        data = {
            "title": "Test Probeable Code Problem",
            "problem_type": "probeable_code",
            "reference_solution": "def mystery(x):\n    return x * 2",
            "function_signature": "def mystery(x: int) -> int",
            "function_name": "mystery",
            "show_function_signature": True,
            "probe_mode": "explore",
            "max_probes": 10,
            "difficulty": "intermediate",
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Test Probeable Code Problem"
        assert ProbeableCodeProblem.objects.filter(
            title="Test Probeable Code Problem"
        ).exists()

    def test_create_refute_problem(self, admin_client):
        """Create a Refute problem."""
        data = {
            "title": "Test Refute Problem",
            "problem_type": "refute",
            "question_text": "Find a counterexample",
            "claim_text": "The function always returns positive",
            "claim_predicate": "result > 0",
            "reference_solution": "def f(x):\n    return x * 2",
            "function_signature": "def f(x: int) -> int",
            "grading_mode": "deterministic",
            "expected_counterexample": {"x": -5},
            "difficulty": "advanced",
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Test Refute Problem"
        assert RefuteProblem.objects.filter(title="Test Refute Problem").exists()

    def test_create_problem_missing_title_fails(self, admin_client):
        """Missing required fields should fail validation."""
        data = {
            "problem_type": "eipl",
            "reference_solution": "def foo(): pass",
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "title" in response.data

    def test_create_problem_auto_generates_slug(self, admin_client):
        """Slug should be auto-generated from title."""
        data = {
            "title": "Auto Slug Test Problem",
            "problem_type": "eipl",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": "beginner",
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["slug"] == "auto-slug-test-problem"


# ─────────────────────────────────────────────────────────────────────────────
# Admin Problem Detail API
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminProblemDetailAPI:
    """Tests for GET/PUT/DELETE /api/admin/problems/<slug>/."""

    def test_get_problem_detail(self, admin_client, eipl_problem):
        """Get problem details by slug."""
        response = admin_client.get(f"/api/admin/problems/{eipl_problem.slug}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == eipl_problem.title
        assert response.data["slug"] == eipl_problem.slug

    def test_get_problem_not_found(self, admin_client):
        """Non-existent problem returns 404."""
        response = admin_client.get("/api/admin/problems/nonexistent-slug/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_problem(self, admin_client, eipl_problem):
        """Update problem fields.

        Note: PUT requires maintaining valid type hints in function_signature.
        """
        data = {
            "title": "Updated Problem Title",
            "difficulty": "advanced",
            "reference_solution": eipl_problem.reference_solution,
            "function_signature": eipl_problem.function_signature,
            "function_name": eipl_problem.function_name,
        }
        response = admin_client.put(
            f"/api/admin/problems/{eipl_problem.slug}/", data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Updated Problem Title"

        # Verify in database
        eipl_problem.refresh_from_db()
        assert eipl_problem.title == "Updated Problem Title"

    def test_update_problem_partial(self, admin_client, eipl_problem):
        """Partial update changes specified fields while preserving others.

        Note: Even partial updates need title + required fields for validation.
        """
        original_solution = eipl_problem.reference_solution
        data = {
            "title": eipl_problem.title,  # Required for validation
            "difficulty": "intermediate",
            "reference_solution": original_solution,
            "function_signature": eipl_problem.function_signature,
            "function_name": eipl_problem.function_name,
        }
        response = admin_client.put(
            f"/api/admin/problems/{eipl_problem.slug}/", data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        # Original solution unchanged
        eipl_problem.refresh_from_db()
        assert eipl_problem.reference_solution == original_solution
        assert eipl_problem.difficulty == "intermediate"

    def test_delete_problem(self, admin_client, eipl_problem):
        """Delete a problem."""
        problem_id = eipl_problem.id
        response = admin_client.delete(f"/api/admin/problems/{eipl_problem.slug}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted
        assert not Problem.objects.filter(id=problem_id).exists()

    def test_delete_problem_not_found(self, admin_client):
        """Deleting non-existent problem returns 404."""
        response = admin_client.delete("/api/admin/problems/nonexistent-slug/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────────────────────────────────────────────────────────────────
# Admin Problem Set List API
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminProblemSetListAPI:
    """Tests for GET/POST /api/admin/problem-sets/."""

    def test_list_problem_sets_requires_auth(self, api_client):
        """Unauthenticated requests should fail."""
        response = api_client.get("/api/admin/problem-sets/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_problem_sets_success(self, admin_client, problem_set):
        """Admin can list all problem sets."""
        response = admin_client.get("/api/admin/problem-sets/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        slugs = [ps["slug"] for ps in response.data]
        assert problem_set.slug in slugs

    def test_create_problem_set(self, admin_client):
        """Create a new problem set."""
        data = {
            "title": "New Test Problem Set",
            "description": "A test problem set",
        }
        response = admin_client.post("/api/admin/problem-sets/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "New Test Problem Set"
        assert ProblemSet.objects.filter(title="New Test Problem Set").exists()

    def test_create_problem_set_with_problems(self, admin_client, eipl_problem):
        """Create problem set with initial problems."""
        data = {
            "title": "PS With Problems",
            "problem_slugs": [eipl_problem.slug],
        }
        response = admin_client.post("/api/admin/problem-sets/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # Verify problem was added
        ps = ProblemSet.objects.get(title="PS With Problems")
        assert ps.problems.filter(slug=eipl_problem.slug).exists()

    def test_create_problem_set_missing_title_fails(self, admin_client):
        """Missing title should fail validation."""
        data = {"description": "No title"}
        response = admin_client.post("/api/admin/problem-sets/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "title" in response.data

    def test_create_problem_set_duplicate_title_fails(self, admin_client, problem_set):
        """Duplicate title should fail validation."""
        data = {"title": problem_set.title}
        response = admin_client.post("/api/admin/problem-sets/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# Admin Problem Set Detail API
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminProblemSetDetailAPI:
    """Tests for GET/PUT/DELETE /api/admin/problem-sets/<slug>/."""

    def test_get_problem_set_detail(self, admin_client, problem_set):
        """Get problem set details by slug."""
        response = admin_client.get(f"/api/admin/problem-sets/{problem_set.slug}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == problem_set.title

    def test_get_problem_set_not_found(self, admin_client):
        """Non-existent problem set returns 404."""
        response = admin_client.get("/api/admin/problem-sets/nonexistent/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_problem_set(self, admin_client, problem_set):
        """Update problem set fields."""
        data = {
            "title": "Updated Problem Set Title",
            "description": "Updated description",
        }
        response = admin_client.put(
            f"/api/admin/problem-sets/{problem_set.slug}/", data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        problem_set.refresh_from_db()
        assert problem_set.title == "Updated Problem Set Title"

    def test_delete_problem_set(self, admin_client, problem_set):
        """Delete a problem set."""
        ps_id = problem_set.id
        response = admin_client.delete(f"/api/admin/problem-sets/{problem_set.slug}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted
        assert not ProblemSet.objects.filter(id=ps_id).exists()

    def test_delete_problem_set_not_found(self, admin_client):
        """Deleting non-existent problem set returns 404."""
        response = admin_client.delete("/api/admin/problem-sets/nonexistent/")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────────────────────────────────────────────────────────────────
# Admin Test Case API
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminTestCaseAPI:
    """Tests for /api/admin/problems/<slug>/test-cases/."""

    def test_create_test_case(self, admin_client, eipl_problem):
        """Create a test case for a problem."""
        data = {
            "inputs": [1, 2],
            "expected_output": 3,
            "description": "Basic addition test",
            "is_hidden": False,
            "is_sample": True,
        }
        response = admin_client.post(
            f"/api/admin/problems/{eipl_problem.slug}/test-cases/",
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["description"] == "Basic addition test"

        # Verify in database
        assert TestCase.objects.filter(
            problem=eipl_problem, description="Basic addition test"
        ).exists()

    def test_create_test_case_problem_not_found(self, admin_client):
        """Creating test case for non-existent problem fails."""
        data = {"inputs": [1], "expected_output": 1}
        response = admin_client.post(
            "/api/admin/problems/nonexistent/test-cases/",
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_test_case(self, admin_client, test_case):
        """Update a test case."""
        data = {
            "description": "Updated test case description",
            "is_hidden": True,
        }
        response = admin_client.put(
            f"/api/admin/problems/{test_case.problem.slug}/test-cases/{test_case.id}/",
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        test_case.refresh_from_db()
        assert test_case.description == "Updated test case description"
        assert test_case.is_hidden is True

    def test_delete_test_case(self, admin_client, test_case):
        """Delete a test case."""
        tc_id = test_case.id
        problem_slug = test_case.problem.slug
        response = admin_client.delete(
            f"/api/admin/problems/{problem_slug}/test-cases/{tc_id}/"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted
        assert not TestCase.objects.filter(id=tc_id).exists()

    def test_delete_test_case_not_found(self, admin_client, eipl_problem):
        """Deleting non-existent test case returns 404."""
        response = admin_client.delete(
            f"/api/admin/problems/{eipl_problem.slug}/test-cases/99999/"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────────────────────────────────────────────────────────────────
# Admin Problem with Problem Sets
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminProblemWithProblemSets:
    """Tests for problem-to-problem-set relationships via API."""

    def test_create_problem_with_problem_sets(self, admin_client, problem_set):
        """Create problem and assign to problem sets."""
        data = {
            "title": "Problem in Set",
            "problem_type": "eipl",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": "beginner",
            "problem_sets": [problem_set.slug],
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        assert response.status_code == status.HTTP_201_CREATED

        # Verify problem is in problem set
        problem = Problem.objects.get(title="Problem in Set")
        assert problem.problem_sets.filter(slug=problem_set.slug).exists()

    def test_update_problem_problem_sets(self, admin_client, eipl_problem, problem_set):
        """Update problem's problem set assignments."""
        # First ensure problem is not in any set
        eipl_problem.problem_sets.clear()

        data = {
            "title": eipl_problem.title,  # Required for validation
            "problem_sets": [problem_set.slug],
            "reference_solution": eipl_problem.reference_solution,
            "function_signature": eipl_problem.function_signature,
            "function_name": eipl_problem.function_name,
        }
        response = admin_client.put(
            f"/api/admin/problems/{eipl_problem.slug}/", data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify problem is now in problem set
        eipl_problem.refresh_from_db()
        assert eipl_problem.problem_sets.filter(slug=problem_set.slug).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Admin API Edge Cases
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminAPIEdgeCases:
    """Edge case tests for admin API."""

    def test_empty_problem_list(self, admin_client):
        """Empty problem list returns empty array."""
        # Delete all problems first
        Problem.objects.all().delete()

        response = admin_client.get("/api/admin/problems/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_empty_problem_set_list(self, admin_client):
        """Empty problem set list returns empty array."""
        ProblemSet.objects.all().delete()

        response = admin_client.get("/api/admin/problem-sets/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_create_problem_with_nonexistent_problem_set(self, admin_client):
        """Creating problem with non-existent problem set slug.

        The API should succeed and silently ignore non-existent problem sets.
        """
        data = {
            "title": "Problem with Bad Set",
            "problem_type": "eipl",
            "reference_solution": "def add(a, b):\n    return a + b",
            "function_signature": "def add(a: int, b: int) -> int",
            "function_name": "add",
            "difficulty": "beginner",
            "problem_sets": ["nonexistent-set"],
        }
        response = admin_client.post("/api/admin/problems/", data, format="json")
        # Should succeed and ignore invalid problem set
        assert response.status_code == status.HTTP_201_CREATED
        assert Problem.objects.filter(title="Problem with Bad Set").exists()
