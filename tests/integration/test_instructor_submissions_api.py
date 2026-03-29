"""Integration tests for instructor submissions and course problem set view endpoints.

Validates the HTTP contract for instructor views of student submission data,
including FERPA isolation (instructors can only see submissions from their courses).
"""

import pytest
from rest_framework import status

from tests.factories import (
    CourseEnrollmentFactory,
    CourseFactory,
    CourseInstructorFactory,
    CourseProblemSetFactory,
    EiplProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    SubmissionFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from inline dicts in instructor_views.py
# ---------------------------------------------------------------------------

# Top-level paginated response (instructor_views.py:164-180)
SUBMISSIONS_RESPONSE_FIELDS = {
    "results",
    "count",
    "next",
    "previous",
    "total_pages",
    "current_page",
    "filters",
    "course",
}

# Individual submission item (instructor_views.py:126-149)
SUBMISSION_ITEM_FIELDS = {
    "id",
    "user",
    "user_id",
    "problem",
    "problem_slug",
    "problem_set",
    "problem_set_slug",
    "submission_type",
    "score",
    "status",
    "comprehension_level",
    "is_correct",
    "execution_status",
    "submitted_at",
    "passed_all_tests",
    "execution_time_ms",
}

# Course problem set item (instructor_views.py:49-65)
COURSE_PS_ITEM_FIELDS = {
    "id",
    "problem_set",
    "order",
    "is_required",
    "due_date",
    "deadline_type",
}

COURSE_PS_NESTED_FIELDS = {"slug", "title", "description", "problems_count"}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def submissions_url(course_id):
    return f"/api/instructor/courses/{course_id}/submissions/"


def submission_detail_url(course_id, submission_id):
    return f"/api/instructor/courses/{course_id}/submissions/{submission_id}/"


def course_ps_url(course_id):
    return f"/api/instructor/courses/{course_id}/problem-sets/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def other_course_submission(db):
    """Submission in a different course — should be invisible to our instructor."""
    other_instructor = UserFactory(username="ferpa_other_instructor")
    UserProfileFactory(user=other_instructor, role="instructor")
    other_course = CourseFactory(course_id="FERPA-OTHER")
    CourseInstructorFactory(course=other_course, user=other_instructor, role="primary")
    student = UserFactory(username="other_student")
    UserProfileFactory(user=student)
    CourseEnrollmentFactory(user=student, course=other_course)
    ps = ProblemSetFactory(created_by=other_instructor)
    problem = EiplProblemFactory(created_by=other_instructor)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    CourseProblemSetFactory(course=other_course, problem_set=ps)
    return SubmissionFactory(
        user=student, problem=problem, problem_set=ps, course=other_course
    )


# ===========================================================================
# TestInstructorCourseSubmissions
# ===========================================================================
class TestInstructorCourseSubmissions:
    """GET /api/instructor/courses/{id}/submissions/"""

    def test_list_submissions_success(
        self, instructor_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(submissions_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK

    def test_list_submissions_response_shape(
        self, instructor_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(submissions_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == SUBMISSIONS_RESPONSE_FIELDS

    def test_list_submissions_item_shape(
        self, instructor_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(submissions_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) >= 1
        item = resp.data["results"][0]
        assert set(item.keys()) == SUBMISSION_ITEM_FIELDS

    def test_list_submissions_pagination_metadata(
        self, instructor_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(submissions_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["current_page"] == 1
        assert resp.data["total_pages"] >= 1
        assert isinstance(resp.data["count"], int)

    def test_list_submissions_includes_filters(
        self, instructor_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(submissions_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        filters = resp.data["filters"]
        assert "problem_sets" in filters
        assert "statuses" in filters
        assert "types" in filters

    def test_list_submissions_non_instructor_forbidden(
        self, authenticated_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        resp = authenticated_client.get(submissions_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_submissions_nonexistent_course_404(self, instructor_client):
        resp = instructor_client.get(submissions_url("DOES-NOT-EXIST"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_ferpa_isolation(
        self,
        instructor_client,
        enrolled_course_with_submission,
        other_course_submission,
    ):
        """Instructor should not see submissions from courses they don't teach."""
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(submissions_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        submission_ids = [s["id"] for s in resp.data["results"]]
        assert str(other_course_submission.submission_id) not in submission_ids


# ===========================================================================
# TestInstructorCourseProblemSets
# ===========================================================================
class TestInstructorCourseProblemSets:
    """GET /api/instructor/courses/{id}/problem-sets/"""

    def test_list_success(self, instructor_client, enrolled_course_with_submission):
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(course_ps_url(course.course_id))
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)
        assert len(resp.data) >= 1

    def test_list_response_shape(
        self, instructor_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(course_ps_url(course.course_id))
        item = resp.data[0]
        assert set(item.keys()) == COURSE_PS_ITEM_FIELDS
        assert set(item["problem_set"].keys()) == COURSE_PS_NESTED_FIELDS

    def test_non_instructor_forbidden(
        self, authenticated_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        resp = authenticated_client.get(course_ps_url(course.course_id))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# TestInstructorSubmissionDetail
# ===========================================================================
class TestInstructorSubmissionDetail:
    """GET /api/instructor/courses/{id}/submissions/{submission_id}/"""

    def test_get_submission_success(
        self, instructor_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        sub = enrolled_course_with_submission["submission"]
        resp = instructor_client.get(
            submission_detail_url(course.course_id, sub.submission_id)
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_submission_from_other_course_404(
        self,
        instructor_client,
        enrolled_course_with_submission,
        other_course_submission,
    ):
        """FERPA: Can't access a submission by ID if it's from another course."""
        course = enrolled_course_with_submission["course"]
        resp = instructor_client.get(
            submission_detail_url(
                course.course_id, other_course_submission.submission_id
            )
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_non_instructor_forbidden(
        self, authenticated_client, enrolled_course_with_submission
    ):
        course = enrolled_course_with_submission["course"]
        sub = enrolled_course_with_submission["submission"]
        resp = authenticated_client.get(
            submission_detail_url(course.course_id, sub.submission_id)
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
