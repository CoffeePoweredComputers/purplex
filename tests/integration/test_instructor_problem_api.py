"""Integration tests for instructor problem API endpoints.

Validates the HTTP contract for problem CRUD operations including
ownership isolation (instructors can only manage their own problems).
"""

import pytest
from rest_framework import status

from tests.factories import (
    EiplProblemFactory,
    McqProblemFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from EiplProblemListSerializer (serializers.py:442-463)
# The polymorphic serializer adds 'resourcetype'.
# ---------------------------------------------------------------------------

# Common fields across all problem types in the polymorphic list serializer
EIPL_LIST_FIELDS = {
    "slug",
    "title",
    "difficulty",
    "problem_type",
    "categories",
    "problem_sets",
    "function_name",
    "tags",
    "is_active",
    "test_cases_count",
    "created_at",
    "resourcetype",
}

# AdminProblemSerializer fields for EiPL detail (serializers.py:62-113 + 1160)
# category_ids is write-only so excluded from response
EIPL_DETAIL_FIELDS = {
    "slug",
    "title",
    "description",
    "difficulty",
    "problem_type",
    "categories",
    "function_name",
    "function_signature",
    "reference_solution",
    "memory_limit",
    "tags",
    "is_active",
    "segmentation_enabled",
    "segmentation_config",
    "requires_highlevel_comprehension",
    "segmentation_threshold",
    "problem_sets",
    "test_cases",
    "test_cases_count",
    "visible_test_cases_count",
    "created_by",
    "created_by_name",
    "created_at",
    "updated_at",
    "version",
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def problem_list_url():
    return "/api/instructor/problems/"


def problem_detail_url(slug):
    return f"/api/instructor/problems/{slug}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def instructor_problem(instructor):
    """EiPL problem owned by the test instructor."""
    return EiplProblemFactory(created_by=instructor)


@pytest.fixture
def instructor_mcq_problem(instructor):
    """MCQ problem owned by the test instructor."""
    return McqProblemFactory(created_by=instructor)


@pytest.fixture
def other_instructor(db):
    """A second instructor."""
    u = UserFactory(username="other_problem_instructor")
    UserProfileFactory(user=u, role="instructor")
    return u


@pytest.fixture
def other_problem(other_instructor):
    """Problem owned by someone else."""
    return EiplProblemFactory(created_by=other_instructor)


# ===========================================================================
# TestInstructorProblemList
# ===========================================================================
class TestInstructorProblemList:
    """GET /api/instructor/problems/"""

    def test_list_problems_success(self, instructor_client, instructor_problem):
        resp = instructor_client.get(problem_list_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        slugs = [p["slug"] for p in resp.data]
        assert instructor_problem.slug in slugs

    def test_list_problems_response_shape(self, instructor_client, instructor_problem):
        resp = instructor_client.get(problem_list_url())
        assert resp.status_code == status.HTTP_200_OK
        item = resp.data[0]
        assert set(item.keys()) == EIPL_LIST_FIELDS

    def test_list_only_own_problems(
        self, instructor_client, instructor_problem, other_problem
    ):
        resp = instructor_client.get(problem_list_url())
        slugs = [p["slug"] for p in resp.data]
        assert instructor_problem.slug in slugs
        assert other_problem.slug not in slugs

    def test_list_problems_unauthenticated(self, api_client):
        resp = api_client.get(problem_list_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_problems_student_forbidden(self, authenticated_client):
        resp = authenticated_client.get(problem_list_url())
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestInstructorProblemCreate
# ===========================================================================
class TestInstructorProblemCreate:
    """POST /api/instructor/problems/"""

    EIPL_CREATE_DATA = {
        "problem_type": "eipl",
        "title": "New EiPL Problem",
        "description": "Explain what this function does",
        "difficulty": "easy",
        "function_name": "add_numbers",
        "function_signature": "def add_numbers(a, b):",
        "reference_solution": "def add_numbers(a, b):\n    return a + b",
    }

    MCQ_CREATE_DATA = {
        "problem_type": "mcq",
        "title": "New MCQ Problem",
        "description": "Pick the correct answer",
        "difficulty": "easy",
        "question_text": "What is 2 + 2?",
        "options": [
            {"id": "a", "text": "3", "is_correct": False},
            {"id": "b", "text": "4", "is_correct": True},
            {"id": "c", "text": "5", "is_correct": False},
        ],
    }

    def test_create_eipl_problem_success(self, instructor_client):
        resp = instructor_client.post(
            problem_list_url(), self.EIPL_CREATE_DATA, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["title"] == "New EiPL Problem"

    def test_create_eipl_problem_response_shape(self, instructor_client):
        resp = instructor_client.post(
            problem_list_url(), self.EIPL_CREATE_DATA, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        # Response uses the read serializer (AdminProblemSerializer)
        assert set(resp.data.keys()) == EIPL_DETAIL_FIELDS

    def test_create_mcq_problem_success(self, instructor_client):
        resp = instructor_client.post(
            problem_list_url(), self.MCQ_CREATE_DATA, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["title"] == "New MCQ Problem"

    def test_create_sets_created_by_to_instructor(self, instructor_client, instructor):
        resp = instructor_client.post(
            problem_list_url(), self.EIPL_CREATE_DATA, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["created_by"] == instructor.id

    def test_create_problem_invalid_type(self, instructor_client):
        data = {**self.EIPL_CREATE_DATA, "problem_type": "nonexistent"}
        resp = instructor_client.post(problem_list_url(), data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_problem_missing_fields(self, instructor_client):
        resp = instructor_client.post(
            problem_list_url(), {"problem_type": "eipl"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_problem_unauthenticated(self, api_client):
        resp = api_client.post(problem_list_url(), self.EIPL_CREATE_DATA, format="json")
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_create_problem_student_forbidden(self, authenticated_client):
        resp = authenticated_client.post(
            problem_list_url(), self.EIPL_CREATE_DATA, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestInstructorProblemDetail
# ===========================================================================
class TestInstructorProblemDetail:
    """GET/PUT/DELETE /api/instructor/problems/{slug}/"""

    def test_get_own_problem_success(self, instructor_client, instructor_problem):
        resp = instructor_client.get(problem_detail_url(instructor_problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["slug"] == instructor_problem.slug

    def test_get_own_problem_response_shape(
        self, instructor_client, instructor_problem
    ):
        resp = instructor_client.get(problem_detail_url(instructor_problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == EIPL_DETAIL_FIELDS

    def test_get_other_instructors_problem_404(self, instructor_client, other_problem):
        resp = instructor_client.get(problem_detail_url(other_problem.slug))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.xfail(
        reason=(
            "AdminProblemSerializer.validate() fallback (serializers.py:1240) always "
            "checks reference_solution even on partial updates. The view passes "
            "partial=True but validation doesn't respect it. Frontend avoids this by "
            "always sending ALL fields on update, but the API contract is broken for "
            "true partial updates."
        ),
        strict=True,
    )
    def test_update_own_problem_partial(self, instructor_client, instructor_problem):
        """Partial update (only title) should work since view uses partial=True."""
        resp = instructor_client.put(
            problem_detail_url(instructor_problem.slug),
            {"title": "Updated Title"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["title"] == "Updated Title"

    def test_update_own_problem_full(self, instructor_client, instructor_problem):
        """Full update with all required fields (how the frontend actually does it)."""
        resp = instructor_client.put(
            problem_detail_url(instructor_problem.slug),
            {
                "title": "Updated Title",
                "description": instructor_problem.description,
                "reference_solution": instructor_problem.reference_solution,
                "function_name": instructor_problem.function_name,
                "function_signature": instructor_problem.function_signature,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["title"] == "Updated Title"

    def test_update_preserves_response_shape(
        self, instructor_client, instructor_problem
    ):
        resp = instructor_client.put(
            problem_detail_url(instructor_problem.slug),
            {
                "title": "Updated Title 2",
                "description": instructor_problem.description,
                "reference_solution": instructor_problem.reference_solution,
                "function_name": instructor_problem.function_name,
                "function_signature": instructor_problem.function_signature,
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == EIPL_DETAIL_FIELDS

    def test_update_other_instructors_problem_404(
        self, instructor_client, other_problem
    ):
        resp = instructor_client.put(
            problem_detail_url(other_problem.slug),
            {"title": "Hijack"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_own_problem_success(self, instructor_client, instructor_problem):
        resp = instructor_client.delete(problem_detail_url(instructor_problem.slug))
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_other_instructors_problem_404(
        self, instructor_client, other_problem
    ):
        resp = instructor_client.delete(problem_detail_url(other_problem.slug))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_unauthenticated(self, api_client, instructor_problem):
        resp = api_client.get(problem_detail_url(instructor_problem.slug))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
