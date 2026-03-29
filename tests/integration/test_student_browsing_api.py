"""Integration tests for student-facing browsing API endpoints.

Validates the HTTP contract for problem listing, problem details,
problem set browsing, and category listing.
"""

import pytest
from rest_framework import status

from tests.factories import (
    EiplProblemFactory,
    ProblemCategoryFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    TestCaseFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from frontend types and serializer Meta.fields
# ---------------------------------------------------------------------------

# ProblemCategorySerializer (serializers.py:23-36)
CATEGORY_FIELDS = {
    "id",
    "name",
    "slug",
    "description",
    "icon",
    "color",
    "order",
    "problems_count",
}

# ProblemSetListSerializer (serializers.py:1070-1083)
PS_LIST_FIELDS = {
    "slug",
    "title",
    "description",
    "icon",
    "problems_count",
    "is_public",
    "created_at",
}

# ProblemSetSerializer (serializers.py:1039-1067) — used for detail view
# plus 'problems' key added by the view (student_views.py:83)
PS_DETAIL_FIELDS = {
    "slug",
    "title",
    "description",
    "problems_count",
    "icon",
    "is_public",
    "created_by",
    "created_by_name",
    "created_at",
    "updated_at",
    "problems",
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def problem_list_url():
    return "/api/problems/"


def problem_detail_url(slug):
    return f"/api/problems/{slug}/"


def ps_list_url():
    return "/api/problem-sets/"


def ps_detail_url(slug):
    return f"/api/problem-sets/{slug}/"


def category_list_url():
    return "/api/categories/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def active_problem(db):
    """An active EiPL problem visible to students."""
    return EiplProblemFactory(is_active=True)


@pytest.fixture
def inactive_problem(db):
    """An inactive problem that should be hidden from students."""
    return EiplProblemFactory(is_active=False, title="Hidden Problem")


@pytest.fixture
def public_problem_set(db, user):
    """A public problem set with one problem."""
    ps = ProblemSetFactory(is_public=True, created_by=user)
    problem = EiplProblemFactory(is_active=True)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    return ps


@pytest.fixture
def category(db):
    """A problem category."""
    return ProblemCategoryFactory()


# ===========================================================================
# TestProblemList
# ===========================================================================
class TestProblemList:
    """GET /api/problems/"""

    def test_list_active_problems(self, authenticated_client, active_problem):
        resp = authenticated_client.get(problem_list_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        slugs = [p["slug"] for p in resp.data]
        assert active_problem.slug in slugs

    def test_excludes_inactive_problems(
        self, authenticated_client, active_problem, inactive_problem
    ):
        resp = authenticated_client.get(problem_list_url())
        slugs = [p["slug"] for p in resp.data]
        assert inactive_problem.slug not in slugs

    def test_unauthenticated_forbidden(self, api_client):
        resp = api_client.get(problem_list_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestProblemDetail
# ===========================================================================
class TestProblemDetail:
    """GET /api/problems/{slug}/"""

    def test_get_problem_success(self, authenticated_client, active_problem):
        resp = authenticated_client.get(problem_detail_url(active_problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["slug"] == active_problem.slug

    def test_get_problem_includes_test_cases_key(
        self, authenticated_client, active_problem
    ):
        """View injects test_cases into the response (student_views.py:48)."""
        resp = authenticated_client.get(problem_detail_url(active_problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert "test_cases" in resp.data
        assert isinstance(resp.data["test_cases"], list)

    def test_visible_test_cases_included(self, authenticated_client):
        problem = EiplProblemFactory(is_active=True)
        TestCaseFactory(problem=problem, is_hidden=False)
        TestCaseFactory(problem=problem, is_hidden=True)
        resp = authenticated_client.get(problem_detail_url(problem.slug))
        # Only non-hidden test cases should be returned
        assert len(resp.data["test_cases"]) == 1

    def test_nonexistent_problem_404(self, authenticated_client):
        resp = authenticated_client.get(problem_detail_url("does-not-exist"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_forbidden(self, api_client, active_problem):
        resp = api_client.get(problem_detail_url(active_problem.slug))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestProblemSetList
# ===========================================================================
class TestProblemSetList:
    """GET /api/problem-sets/"""

    def test_list_public_problem_sets(self, authenticated_client, public_problem_set):
        resp = authenticated_client.get(ps_list_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        slugs = [ps["slug"] for ps in resp.data]
        assert public_problem_set.slug in slugs

    def test_list_response_shape(self, authenticated_client, public_problem_set):
        resp = authenticated_client.get(ps_list_url())
        item = resp.data[0]
        assert set(item.keys()) == PS_LIST_FIELDS

    def test_unauthenticated_forbidden(self, api_client):
        resp = api_client.get(ps_list_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestProblemSetDetail
# ===========================================================================
class TestProblemSetDetail:
    """GET /api/problem-sets/{slug}/"""

    def test_get_problem_set_success(self, authenticated_client, public_problem_set):
        resp = authenticated_client.get(ps_detail_url(public_problem_set.slug))
        assert resp.status_code == status.HTTP_200_OK

    def test_get_problem_set_response_shape(
        self, authenticated_client, public_problem_set
    ):
        resp = authenticated_client.get(ps_detail_url(public_problem_set.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == PS_DETAIL_FIELDS

    def test_get_problem_set_includes_problems(
        self, authenticated_client, public_problem_set
    ):
        resp = authenticated_client.get(ps_detail_url(public_problem_set.slug))
        assert isinstance(resp.data["problems"], list)
        assert len(resp.data["problems"]) >= 1

    def test_unauthenticated_forbidden(self, api_client, public_problem_set):
        resp = api_client.get(ps_detail_url(public_problem_set.slug))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestCategoryList
# ===========================================================================
class TestCategoryList:
    """GET /api/categories/"""

    def test_list_categories(self, authenticated_client, category):
        resp = authenticated_client.get(category_list_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 1

    def test_list_response_shape(self, authenticated_client, category):
        resp = authenticated_client.get(category_list_url())
        item = resp.data[0]
        assert set(item.keys()) == CATEGORY_FIELDS

    def test_unauthenticated_forbidden(self, api_client):
        resp = api_client.get(category_list_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
