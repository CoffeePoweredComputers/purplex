"""Integration tests for admin submission management API endpoints.

Validates the HTTP contract for admin submission listing (paginated),
submission detail, and category management.
"""

import pytest
from rest_framework import status

from tests.factories import (
    EiplProblemFactory,
    ProblemCategoryFactory,
    ProblemSetFactory,
    SubmissionFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from inline dicts in admin_views.py
# ---------------------------------------------------------------------------

# AdminSubmissionListView GET response (admin_views.py:578-654)
ADMIN_SUBMISSIONS_RESPONSE_FIELDS = {
    "results",
    "count",
    "next",
    "previous",
    "total_pages",
    "current_page",
    "filters",
}

# Individual submission item in admin list
ADMIN_SUBMISSION_ITEM_FIELDS = {
    "id",
    "user",
    "problem",
    "problem_slug",
    "problem_set",
    "course",
    "submission_type",
    "score",
    "status",
    "comprehension_level",
    "is_correct",
    "execution_status",
    "submitted_at",
    "passed_all_tests",
    "execution_time_ms",
    "memory_used_mb",
}

# ProblemCategorySerializer fields (serializers.py:23-36)
# Note: problems_count requires annotation — may be missing
CATEGORY_FIELDS_MINIMAL = {
    "id",
    "name",
    "slug",
    "description",
    "icon",
    "color",
    "order",
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def admin_submissions_url():
    return "/api/admin/submissions/"


def admin_submission_detail_url(submission_id):
    return f"/api/admin/submissions/{submission_id}/"


def admin_categories_url():
    return "/api/admin/categories/"


def admin_category_detail_url(pk):
    return f"/api/admin/categories/{pk}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def admin_submission(db):
    """A submission visible to admin."""
    student = UserFactory(username="admin_sub_student")
    UserProfileFactory(user=student)
    problem = EiplProblemFactory(is_active=True)
    ps = ProblemSetFactory()
    return SubmissionFactory(user=student, problem=problem, problem_set=ps)


# ===========================================================================
# TestAdminSubmissionList
# ===========================================================================
class TestAdminSubmissionList:
    """GET /api/admin/submissions/"""

    def test_list_success(self, admin_client, admin_submission):
        resp = admin_client.get(admin_submissions_url())
        assert resp.status_code == status.HTTP_200_OK

    def test_list_response_shape(self, admin_client, admin_submission):
        resp = admin_client.get(admin_submissions_url())
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == ADMIN_SUBMISSIONS_RESPONSE_FIELDS

    def test_list_item_shape(self, admin_client, admin_submission):
        resp = admin_client.get(admin_submissions_url())
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) >= 1
        item = resp.data["results"][0]
        assert set(item.keys()) == ADMIN_SUBMISSION_ITEM_FIELDS

    def test_list_pagination(self, admin_client, admin_submission):
        resp = admin_client.get(admin_submissions_url(), {"page": 1, "page_size": 5})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["current_page"] == 1

    def test_list_filters_metadata(self, admin_client, admin_submission):
        resp = admin_client.get(admin_submissions_url())
        filters = resp.data["filters"]
        assert "problem_sets" in filters
        assert "courses" in filters
        assert "statuses" in filters

    def test_list_non_admin_forbidden(self, authenticated_client):
        resp = authenticated_client.get(admin_submissions_url())
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_instructor_forbidden(self, instructor_client):
        resp = instructor_client.get(admin_submissions_url())
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_unauthenticated(self, api_client):
        resp = api_client.get(admin_submissions_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestAdminSubmissionDetail
# ===========================================================================
class TestAdminSubmissionDetail:
    """GET /api/admin/submissions/{id}/"""

    def test_detail_success(self, admin_client, admin_submission):
        resp = admin_client.get(
            admin_submission_detail_url(admin_submission.submission_id)
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_detail_nonexistent_404(self, admin_client):
        resp = admin_client.get(
            admin_submission_detail_url("00000000-0000-0000-0000-000000000000")
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_non_admin_forbidden(self, authenticated_client, admin_submission):
        resp = authenticated_client.get(
            admin_submission_detail_url(admin_submission.submission_id)
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestAdminCategories
# ===========================================================================
class TestAdminCategories:
    """GET/POST /api/admin/categories/"""

    def test_list_success(self, admin_client):
        ProblemCategoryFactory()
        resp = admin_client.get(admin_categories_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)

    def test_create_success(self, admin_client):
        resp = admin_client.post(
            admin_categories_url(),
            {"name": "New Category", "description": "Test category"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "New Category"

    def test_create_non_admin_forbidden(self, authenticated_client):
        resp = authenticated_client.post(
            admin_categories_url(),
            {"name": "Fail", "description": "nope"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_unauthenticated(self, api_client):
        resp = api_client.get(admin_categories_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
