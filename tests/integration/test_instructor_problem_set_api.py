"""Integration tests for instructor problem set and course-problem-set API endpoints.

Validates problem set CRUD and the course-problem-set management endpoints
(add/remove/patch problem sets within a course). Includes detection of known
frontend-backend contract inconsistencies.
"""

import pytest
from rest_framework import status

from tests.factories import (
    CourseProblemSetFactory,
    EiplProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets
# ---------------------------------------------------------------------------

# ProblemSetSerializer (serializers.py:1039-1067) — used for list and create
PROBLEM_SET_FIELDS = {
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
}

# AdminProblemSetSerializer (serializers.py:1086-1115) — used for detail GET
PROBLEM_SET_DETAIL_FIELDS = PROBLEM_SET_FIELDS | {"problems_detail"}

# CourseProblemSet POST response (instructor_content_views.py:423-437)
# Matches frontend CourseProblemSet type (types/index.ts:746-758)
CPS_POST_FIELDS = {
    "id",
    "problem_set",
    "order",
    "is_required",
    "due_date",
    "deadline_type",
}
CPS_POST_PS_FIELDS = {"slug", "title", "description", "problems_count"}

# CourseProblemSet PATCH response — now matches POST shape
CPS_PATCH_FIELDS = CPS_POST_FIELDS


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def ps_list_url():
    return "/api/instructor/problem-sets/"


def ps_detail_url(slug):
    return f"/api/instructor/problem-sets/{slug}/"


def cps_manage_url(course_id):
    return f"/api/instructor/courses/{course_id}/problem-sets/manage/"


def cps_membership_url(course_id, membership_id):
    return f"/api/instructor/courses/{course_id}/problem-sets/{membership_id}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def instructor_problem_set(instructor):
    """Problem set owned by the test instructor."""
    return ProblemSetFactory(created_by=instructor)


@pytest.fixture
def instructor_problem_set_with_problem(instructor):
    """Problem set with one problem, owned by the test instructor."""
    ps = ProblemSetFactory(created_by=instructor)
    problem = EiplProblemFactory(created_by=instructor)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    return ps


@pytest.fixture
def other_instructor(db):
    """A second instructor."""
    u = UserFactory(username="other_ps_instructor")
    UserProfileFactory(user=u, role="instructor")
    return u


@pytest.fixture
def other_problem_set(other_instructor):
    """Problem set owned by another instructor."""
    return ProblemSetFactory(created_by=other_instructor)


# ===========================================================================
# TestInstructorProblemSetCRUD
# ===========================================================================
class TestInstructorProblemSetList:
    """GET /api/instructor/problem-sets/"""

    def test_list_success(self, instructor_client, instructor_problem_set):
        resp = instructor_client.get(ps_list_url())
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        slugs = [ps["slug"] for ps in resp.data]
        assert instructor_problem_set.slug in slugs

    def test_list_response_shape(self, instructor_client, instructor_problem_set):
        resp = instructor_client.get(ps_list_url())
        assert resp.status_code == status.HTTP_200_OK
        item = resp.data[0]
        assert set(item.keys()) == PROBLEM_SET_FIELDS

    def test_list_only_own(
        self, instructor_client, instructor_problem_set, other_problem_set
    ):
        resp = instructor_client.get(ps_list_url())
        assert resp.status_code == status.HTTP_200_OK
        slugs = [ps["slug"] for ps in resp.data]
        assert instructor_problem_set.slug in slugs
        assert other_problem_set.slug not in slugs

    def test_list_unauthenticated(self, api_client):
        resp = api_client.get(ps_list_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_list_student_forbidden(self, authenticated_client):
        resp = authenticated_client.get(ps_list_url())
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestInstructorProblemSetCreate:
    """POST /api/instructor/problem-sets/"""

    def test_create_success(self, instructor_client):
        data = {"title": "New Problem Set", "description": "A test set"}
        resp = instructor_client.post(ps_list_url(), data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["title"] == "New Problem Set"

    def test_create_response_shape(self, instructor_client):
        data = {"title": "Shape Test Set", "description": "checking shape"}
        resp = instructor_client.post(ps_list_url(), data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert set(resp.data.keys()) == PROBLEM_SET_FIELDS

    def test_create_missing_title(self, instructor_client):
        resp = instructor_client.post(ps_list_url(), {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestInstructorProblemSetDetail:
    """GET/PUT/DELETE /api/instructor/problem-sets/{slug}/"""

    def test_get_success(self, instructor_client, instructor_problem_set_with_problem):
        resp = instructor_client.get(
            ps_detail_url(instructor_problem_set_with_problem.slug)
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_get_response_shape(
        self, instructor_client, instructor_problem_set_with_problem
    ):
        resp = instructor_client.get(
            ps_detail_url(instructor_problem_set_with_problem.slug)
        )
        assert resp.status_code == status.HTTP_200_OK
        # Detail view uses AdminProblemSetSerializer
        assert set(resp.data.keys()) == PROBLEM_SET_DETAIL_FIELDS

    def test_update_success(self, instructor_client, instructor_problem_set):
        resp = instructor_client.put(
            ps_detail_url(instructor_problem_set.slug),
            {"title": "Updated PS Title"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["title"] == "Updated PS Title"

    def test_delete_success(self, instructor_client, instructor_problem_set):
        resp = instructor_client.delete(ps_detail_url(instructor_problem_set.slug))
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_get_other_instructor_404(self, instructor_client, other_problem_set):
        resp = instructor_client.get(ps_detail_url(other_problem_set.slug))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# TestInstructorCourseProblemSetManage
# ===========================================================================
class TestInstructorCourseProblemSetManage:
    """POST/DELETE/PATCH on course-problem-set management endpoints."""

    def test_add_problem_set_to_course(
        self, instructor_client, course, instructor_problem_set
    ):
        data = {"problem_set_slug": instructor_problem_set.slug}
        resp = instructor_client.post(
            cps_manage_url(course.course_id), data, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_add_problem_set_response_shape(
        self, instructor_client, course, instructor_problem_set
    ):
        data = {"problem_set_slug": instructor_problem_set.slug}
        resp = instructor_client.post(
            cps_manage_url(course.course_id), data, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert set(resp.data.keys()) == CPS_POST_FIELDS
        assert set(resp.data["problem_set"].keys()) == CPS_POST_PS_FIELDS

    def test_add_nonexistent_problem_set_404(self, instructor_client, course):
        data = {"problem_set_slug": "nonexistent-slug"}
        resp = instructor_client.post(
            cps_manage_url(course.course_id), data, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_problem_set_from_course(self, instructor_client, course):
        ps = ProblemSetFactory()
        cps = CourseProblemSetFactory(course=course, problem_set=ps)
        resp = instructor_client.delete(
            cps_membership_url(course.course_id, cps.id),
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_patch_problem_set_membership(self, instructor_client, course):
        ps = ProblemSetFactory()
        cps = CourseProblemSetFactory(course=course, problem_set=ps, order=0)
        resp = instructor_client.patch(
            cps_membership_url(course.course_id, cps.id),
            {"order": 5, "is_required": False},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["order"] == 5
        assert resp.data["is_required"] is False

    def test_patch_response_shape(self, instructor_client, course):
        ps = ProblemSetFactory()
        cps = CourseProblemSetFactory(course=course, problem_set=ps)
        resp = instructor_client.patch(
            cps_membership_url(course.course_id, cps.id),
            {"order": 1},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        # Document what the backend actually returns
        assert set(resp.data.keys()) == CPS_PATCH_FIELDS

    def test_patch_matches_frontend_type(self, instructor_client, course):
        """PATCH response should match the frontend CourseProblemSet type."""
        ps = ProblemSetFactory()
        cps = CourseProblemSetFactory(course=course, problem_set=ps)
        resp = instructor_client.patch(
            cps_membership_url(course.course_id, cps.id),
            {"order": 2},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        # PATCH now returns same shape as POST with nested problem_set
        assert set(resp.data.keys()) == CPS_POST_FIELDS
        assert set(resp.data["problem_set"].keys()) == CPS_POST_PS_FIELDS

    def test_student_cannot_manage(self, authenticated_client, course):
        data = {"problem_set_slug": "anything"}
        resp = authenticated_client.post(
            cps_manage_url(course.course_id), data, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_ta_cannot_manage(self, ta_client, course_with_team):
        data = {"problem_set_slug": "anything"}
        resp = ta_client.post(
            cps_manage_url(course_with_team.course_id), data, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
