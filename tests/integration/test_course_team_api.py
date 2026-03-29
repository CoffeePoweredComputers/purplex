"""Integration tests for the course team management API."""

import pytest

from tests.factories import UserFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def team_url(course_id):
    return f"/api/instructor/courses/{course_id}/team/"


def team_detail_url(course_id, user_id):
    return f"/api/instructor/courses/{course_id}/team/{user_id}/"


def admin_team_url(course_id):
    return f"/api/admin/courses/{course_id}/team/"


def admin_team_detail_url(course_id, user_id):
    return f"/api/admin/courses/{course_id}/team/{user_id}/"


class TestCourseTeamList:
    """GET /api/instructor/courses/<id>/team/"""

    def test_primary_can_list(self, instructor_client, course_with_team):
        resp = instructor_client.get(team_url(course_with_team.course_id))
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_ta_can_list(self, ta_client, course_with_team):
        resp = ta_client.get(team_url(course_with_team.course_id))
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_non_instructor_403(self, authenticated_client, course_with_team):
        resp = authenticated_client.get(team_url(course_with_team.course_id))
        assert resp.status_code == 403

    def test_unauthenticated_403(self, api_client, course_with_team):
        resp = api_client.get(team_url(course_with_team.course_id))
        assert resp.status_code == 403

    def test_nonexistent_course_404(self, instructor_client):
        resp = instructor_client.get(team_url("NONEXISTENT-999"))
        assert resp.status_code == 404


class TestCourseTeamCreate:
    """POST /api/instructor/courses/<id>/team/"""

    def test_primary_adds_ta(self, instructor_client, course_with_team):
        new_user = UserFactory()
        resp = instructor_client.post(
            team_url(course_with_team.course_id),
            {"email": new_user.email, "role": "ta"},
        )
        assert resp.status_code == 201
        assert resp.data["role"] == "ta"

    def test_primary_adds_primary(self, instructor_client, course_with_team):
        new_user = UserFactory()
        resp = instructor_client.post(
            team_url(course_with_team.course_id),
            {"email": new_user.email, "role": "primary"},
        )
        assert resp.status_code == 201
        assert resp.data["role"] == "primary"

    def test_ta_cannot_add_403(self, ta_client, course_with_team):
        new_user = UserFactory()
        resp = ta_client.post(
            team_url(course_with_team.course_id),
            {"email": new_user.email, "role": "ta"},
        )
        assert resp.status_code == 403

    def test_duplicate_409(self, instructor_client, course_with_team, ta_user):
        resp = instructor_client.post(
            team_url(course_with_team.course_id),
            {"email": ta_user.email, "role": "ta"},
        )
        assert resp.status_code == 409

    def test_nonexistent_user_404(self, instructor_client, course_with_team):
        resp = instructor_client.post(
            team_url(course_with_team.course_id),
            {"email": "nobody@example.com", "role": "ta"},
        )
        assert resp.status_code == 404

    def test_invalid_role_400(self, instructor_client, course_with_team):
        new_user = UserFactory()
        resp = instructor_client.post(
            team_url(course_with_team.course_id),
            {"email": new_user.email, "role": "invalid"},
        )
        assert resp.status_code == 400


class TestCourseTeamUpdate:
    """PATCH /api/instructor/courses/<id>/team/<uid>/"""

    def test_promote_ta(self, instructor_client, course_with_team, ta_user):
        resp = instructor_client.patch(
            team_detail_url(course_with_team.course_id, ta_user.id),
            {"role": "primary"},
        )
        assert resp.status_code == 200
        assert resp.data["role"] == "primary"

    def test_demote_when_multiple(
        self, instructor_client, course_with_team, ta_user, instructor
    ):
        # First promote TA so we have 2 primaries
        instructor_client.patch(
            team_detail_url(course_with_team.course_id, ta_user.id),
            {"role": "primary"},
        )
        # Now demote original instructor
        resp = instructor_client.patch(
            team_detail_url(course_with_team.course_id, instructor.id),
            {"role": "ta"},
        )
        assert resp.status_code == 200
        assert resp.data["role"] == "ta"

    def test_cannot_demote_last_primary_400(
        self, instructor_client, course_with_team, instructor
    ):
        resp = instructor_client.patch(
            team_detail_url(course_with_team.course_id, instructor.id),
            {"role": "ta"},
        )
        assert resp.status_code == 400
        assert "last primary" in resp.data["error"]

    def test_ta_cannot_update_403(self, ta_client, course_with_team, instructor):
        resp = ta_client.patch(
            team_detail_url(course_with_team.course_id, instructor.id),
            {"role": "ta"},
        )
        assert resp.status_code == 403

    def test_invalid_role_400(self, instructor_client, course_with_team, ta_user):
        resp = instructor_client.patch(
            team_detail_url(course_with_team.course_id, ta_user.id),
            {"role": "invalid"},
        )
        assert resp.status_code == 400


class TestCourseTeamDelete:
    """DELETE /api/instructor/courses/<id>/team/<uid>/"""

    def test_remove_ta(self, instructor_client, course_with_team, ta_user):
        resp = instructor_client.delete(
            team_detail_url(course_with_team.course_id, ta_user.id)
        )
        assert resp.status_code == 204

    def test_remove_primary_when_multiple(
        self, instructor_client, course_with_team, instructor, ta_user
    ):
        # Add second primary
        new_primary = UserFactory()
        instructor_client.post(
            team_url(course_with_team.course_id),
            {"email": new_primary.email, "role": "primary"},
        )
        resp = instructor_client.delete(
            team_detail_url(course_with_team.course_id, instructor.id)
        )
        assert resp.status_code == 204

    def test_cannot_remove_last_primary_400(
        self, instructor_client, course_with_team, instructor
    ):
        resp = instructor_client.delete(
            team_detail_url(course_with_team.course_id, instructor.id)
        )
        assert resp.status_code == 400

    def test_ta_cannot_delete_403(self, ta_client, course_with_team, instructor):
        resp = ta_client.delete(
            team_detail_url(course_with_team.course_id, instructor.id)
        )
        assert resp.status_code == 403


# ===========================================================================
# Admin course team management (via /api/admin/courses/<id>/team/)
# ===========================================================================


class TestAdminAccessToInstructorTeamEndpoints:
    """Admins who navigate to the instructor course overview call
    /api/instructor/ team endpoints. These use IsPrimaryCourseInstructor
    which allows superusers. Verify admins can or cannot access them."""

    def test_admin_can_list_via_instructor_endpoint(
        self, admin_client, course_with_team
    ):
        resp = admin_client.get(team_url(course_with_team.course_id))
        assert resp.status_code == 200

    def test_admin_can_patch_via_instructor_endpoint(
        self, admin_client, course_with_team, ta_user
    ):
        """This is the exact scenario that was failing in the browser."""
        resp = admin_client.patch(
            team_detail_url(course_with_team.course_id, ta_user.id),
            {"role": "primary"},
        )
        assert resp.status_code == 200
        assert resp.data["role"] == "primary"


class TestAdminCourseTeamList:
    """GET /api/admin/courses/<id>/team/"""

    def test_admin_can_list(self, admin_client, course_with_team):
        resp = admin_client.get(admin_team_url(course_with_team.course_id))
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_non_admin_forbidden(self, authenticated_client, course_with_team):
        resp = authenticated_client.get(admin_team_url(course_with_team.course_id))
        assert resp.status_code == 403

    def test_nonexistent_course_404(self, admin_client):
        resp = admin_client.get(admin_team_url("NONEXISTENT-999"))
        assert resp.status_code == 404


class TestAdminCourseTeamCreate:
    """POST /api/admin/courses/<id>/team/"""

    def test_admin_adds_ta(self, admin_client, course_with_team):
        new_user = UserFactory()
        resp = admin_client.post(
            admin_team_url(course_with_team.course_id),
            {"email": new_user.email, "role": "ta"},
        )
        assert resp.status_code == 201
        assert resp.data["role"] == "ta"

    def test_admin_add_duplicate_409(self, admin_client, course_with_team, ta_user):
        resp = admin_client.post(
            admin_team_url(course_with_team.course_id),
            {"email": ta_user.email, "role": "ta"},
        )
        assert resp.status_code == 409


class TestAdminCourseTeamUpdate:
    """PATCH /api/admin/courses/<id>/team/<uid>/"""

    def test_admin_promote_ta(self, admin_client, course_with_team, ta_user):
        resp = admin_client.patch(
            admin_team_detail_url(course_with_team.course_id, ta_user.id),
            {"role": "primary"},
        )
        assert resp.status_code == 200
        assert resp.data["role"] == "primary"

    def test_admin_invalid_role_400(self, admin_client, course_with_team, ta_user):
        resp = admin_client.patch(
            admin_team_detail_url(course_with_team.course_id, ta_user.id),
            {"role": "invalid"},
        )
        assert resp.status_code == 400

    def test_admin_cannot_demote_last_primary(
        self, admin_client, course_with_team, instructor
    ):
        resp = admin_client.patch(
            admin_team_detail_url(course_with_team.course_id, instructor.id),
            {"role": "ta"},
        )
        assert resp.status_code == 400
        assert "last primary" in resp.data["error"]


class TestAdminCourseTeamDelete:
    """DELETE /api/admin/courses/<id>/team/<uid>/"""

    def test_admin_remove_ta(self, admin_client, course_with_team, ta_user):
        resp = admin_client.delete(
            admin_team_detail_url(course_with_team.course_id, ta_user.id)
        )
        assert resp.status_code == 204

    def test_admin_cannot_remove_last_primary(
        self, admin_client, course_with_team, instructor
    ):
        resp = admin_client.delete(
            admin_team_detail_url(course_with_team.course_id, instructor.id)
        )
        assert resp.status_code == 400
