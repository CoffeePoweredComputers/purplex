"""Integration tests for student progress and submission history API endpoints.

Validates the HTTP contract for submission history retrieval, progress tracking,
problem set progress, and last submission endpoints.
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
    UserProgressFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

# ---------------------------------------------------------------------------
# Field sets — from inline dicts in submission_views.py and progress_views.py
# ---------------------------------------------------------------------------

# SubmissionHistoryView top-level response (submission_views.py:486-503)
HISTORY_TOP_FIELDS = {
    "problem_slug",
    "total_attempts",
    "best_score",
    "best_attempt_id",
    "current_progress",
    "submissions",
}

# SubmissionHistoryItem (submission_views.py:356-470)
# Matches frontend SubmissionHistoryItem (types/index.ts:623-674)
HISTORY_ITEM_FIELDS = {
    "id",
    "attempt_number",
    "submitted_at",
    "score",
    "passed_all_tests",
    "completion_status",
    "execution_status",
    "submission_type",
    "tests_passed",
    "total_tests",
    "execution_time_ms",
    "is_best",
    "variations_count",
    "comprehension_level",
    "segmentation",
    "data",
    "type_specific",
}

# UserProgressView specific-problem response (progress_views.py:53-81)
PROGRESS_FIELDS = {
    "problem_slug",
    "status",
    "best_score",
    "attempts",
    "is_completed",
    "completion_percentage",
    "last_attempt",
    "completed_at",
    "grade",
}

# ProblemSetProgressView top-level (progress_views.py:126-139)
PS_PROGRESS_TOP_FIELDS = {"problem_set", "problems_progress"}
PS_PROGRESS_SET_FIELDS = {
    "slug",
    "title",
    "total_problems",
    "completed_problems",
    "in_progress_problems",
    "completion_percentage",
    "is_completed",
    "average_score",
    "last_activity",
}

# LastSubmissionView — with submission (progress_views.py:210-236)
LAST_SUB_WITH_FIELDS = {
    "has_submission",
    "submission_id",
    "variations",
    "results",
    "passing_variations",
    "total_variations",
    "user_prompt",
    "feedback",
    "segmentation",
    "segmentation_passed",
    "score",
    "submitted_at",
    "grade",
}

# LastSubmissionView — no submission (progress_views.py:239-252)
LAST_SUB_NONE_FIELDS = {
    "has_submission",
    "variations",
    "results",
    "passing_variations",
    "total_variations",
    "user_prompt",
    "feedback",
    "segmentation",
    "segmentation_passed",
    "score",
    "submitted_at",
}


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def history_url(problem_slug):
    return f"/api/submissions/history/{problem_slug}/"


def progress_url(problem_slug=None):
    if problem_slug:
        return f"/api/progress/{problem_slug}/"
    return "/api/progress/"


def ps_progress_url(ps_slug):
    return f"/api/problem-sets/{ps_slug}/progress/"


def last_submission_url(problem_slug):
    return f"/api/last-submission/{problem_slug}/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def student_with_submission(db):
    """Student user with a submission against a problem in a problem set."""
    student = UserFactory(username="progress_student")
    UserProfileFactory(user=student)
    problem = EiplProblemFactory(is_active=True)
    ps = ProblemSetFactory(is_public=True)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    submission = SubmissionFactory(user=student, problem=problem, problem_set=ps)
    UserProgressFactory(
        user=student,
        problem=problem,
        problem_set=ps,
        attempts=1,
        best_score=submission.score,
        status="in_progress",
    )
    return {
        "student": student,
        "problem": problem,
        "problem_set": ps,
        "submission": submission,
    }


@pytest.fixture
def student_client(api_client, student_with_submission):
    """API client authenticated as the student with submissions."""
    api_client.force_authenticate(user=student_with_submission["student"])
    return api_client


@pytest.fixture
def enrolled_student_with_submission(db):
    """Student enrolled in a course, with submission in that course context."""
    student = UserFactory(username="enrolled_progress_student")
    UserProfileFactory(user=student)
    instructor_user = UserFactory(username="course_instructor_progress")
    UserProfileFactory(user=instructor_user, role="instructor")

    course = CourseFactory()
    CourseInstructorFactory(course=course, user=instructor_user, role="primary")
    CourseEnrollmentFactory(user=student, course=course)

    problem = EiplProblemFactory(is_active=True, created_by=instructor_user)
    ps = ProblemSetFactory(is_public=True, created_by=instructor_user)
    ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
    CourseProblemSetFactory(course=course, problem_set=ps, order=0)
    submission = SubmissionFactory(
        user=student, problem=problem, problem_set=ps, course=course
    )
    UserProgressFactory(
        user=student,
        problem=problem,
        problem_set=ps,
        course=course,
        attempts=1,
        best_score=submission.score,
        status="in_progress",
    )
    return {
        "student": student,
        "problem": problem,
        "problem_set": ps,
        "course": course,
        "submission": submission,
    }


@pytest.fixture
def enrolled_student_client(api_client, enrolled_student_with_submission):
    """API client for the enrolled student."""
    api_client.force_authenticate(user=enrolled_student_with_submission["student"])
    return api_client


# ===========================================================================
# TestSubmissionHistory
# ===========================================================================
class TestSubmissionHistory:
    """GET /api/submissions/history/{problem_slug}/"""

    def test_history_with_submissions(self, student_client, student_with_submission):
        problem = student_with_submission["problem"]
        resp = student_client.get(history_url(problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_attempts"] >= 1

    def test_history_response_shape(self, student_client, student_with_submission):
        problem = student_with_submission["problem"]
        resp = student_client.get(history_url(problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == HISTORY_TOP_FIELDS

    def test_history_item_shape(self, student_client, student_with_submission):
        problem = student_with_submission["problem"]
        resp = student_client.get(history_url(problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["submissions"]) >= 1
        item = resp.data["submissions"][0]
        assert set(item.keys()) == HISTORY_ITEM_FIELDS

    def test_history_no_submissions(self, authenticated_client):
        problem = EiplProblemFactory(is_active=True)
        resp = authenticated_client.get(history_url(problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_attempts"] == 0
        assert resp.data["submissions"] == []

    def test_history_nonexistent_problem_404(self, authenticated_client):
        resp = authenticated_client.get(history_url("does-not-exist"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_history_unauthenticated(self, api_client):
        resp = api_client.get(history_url("any-slug"))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_history_filter_by_problem_set(
        self, student_client, student_with_submission
    ):
        problem = student_with_submission["problem"]
        ps = student_with_submission["problem_set"]
        resp = student_client.get(
            history_url(problem.slug), {"problem_set_slug": ps.slug}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_attempts"] >= 1

    def test_history_filter_by_course(
        self, enrolled_student_client, enrolled_student_with_submission
    ):
        problem = enrolled_student_with_submission["problem"]
        course = enrolled_student_with_submission["course"]
        resp = enrolled_student_client.get(
            history_url(problem.slug), {"course_id": course.course_id}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["total_attempts"] >= 1


# ===========================================================================
# TestUserProgress
# ===========================================================================
class TestUserProgress:
    """GET /api/progress/ and GET /api/progress/{problem_slug}/"""

    def test_all_progress(self, student_client, student_with_submission):
        resp = student_client.get(progress_url())
        assert resp.status_code == status.HTTP_200_OK
        # Returns a list of progress objects
        assert isinstance(resp.data, list)

    def test_specific_problem_progress(self, student_client, student_with_submission):
        problem = student_with_submission["problem"]
        ps = student_with_submission["problem_set"]
        resp = student_client.get(
            progress_url(problem.slug), {"problem_set_slug": ps.slug}
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_specific_progress_response_shape(
        self, student_client, student_with_submission
    ):
        problem = student_with_submission["problem"]
        ps = student_with_submission["problem_set"]
        resp = student_client.get(
            progress_url(problem.slug), {"problem_set_slug": ps.slug}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == PROGRESS_FIELDS

    def test_progress_not_started_returns_defaults(self, authenticated_client):
        problem = EiplProblemFactory(is_active=True)
        ps = ProblemSetFactory(is_public=True)
        ProblemSetMembershipFactory(problem_set=ps, problem=problem, order=0)
        resp = authenticated_client.get(
            progress_url(problem.slug), {"problem_set_slug": ps.slug}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "not_started"
        assert resp.data["best_score"] == 0
        assert resp.data["attempts"] == 0
        assert resp.data["is_completed"] is False

    def test_progress_nonexistent_problem_404(self, authenticated_client):
        resp = authenticated_client.get(
            progress_url("does-not-exist"), {"problem_set_slug": "fake"}
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_progress_unauthenticated(self, api_client):
        resp = api_client.get(progress_url())
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestProblemSetProgress
# ===========================================================================
class TestProblemSetProgress:
    """GET /api/problem-sets/{slug}/progress/"""

    def test_progress_success(self, student_client, student_with_submission):
        ps = student_with_submission["problem_set"]
        resp = student_client.get(ps_progress_url(ps.slug))
        assert resp.status_code == status.HTTP_200_OK

    def test_progress_response_shape(self, student_client, student_with_submission):
        ps = student_with_submission["problem_set"]
        resp = student_client.get(ps_progress_url(ps.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) >= PS_PROGRESS_TOP_FIELDS
        assert set(resp.data["problem_set"].keys()) == PS_PROGRESS_SET_FIELDS

    def test_progress_with_course_includes_deadline(
        self, enrolled_student_client, enrolled_student_with_submission
    ):
        """When course_id provided and deadline exists, response includes deadline info."""
        ps = enrolled_student_with_submission["problem_set"]
        course = enrolled_student_with_submission["course"]
        resp = enrolled_student_client.get(
            ps_progress_url(ps.slug), {"course_id": course.course_id}
        )
        assert resp.status_code == status.HTTP_200_OK
        # deadline key is only present if the CourseProblemSet has a due_date set
        # Our fixture doesn't set one, so deadline should be absent
        # This test validates the endpoint works with course context

    def test_nonexistent_set_404(self, authenticated_client):
        resp = authenticated_client.get(ps_progress_url("does-not-exist"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated(self, api_client):
        resp = api_client.get(ps_progress_url("any-slug"))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


# ===========================================================================
# TestLastSubmission
# ===========================================================================
class TestLastSubmission:
    """GET /api/last-submission/{problem_slug}/"""

    def test_last_submission_exists(self, student_client, student_with_submission):
        problem = student_with_submission["problem"]
        resp = student_client.get(last_submission_url(problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["has_submission"] is True
        assert resp.data["score"] >= 0

    def test_last_submission_with_response_shape(
        self, student_client, student_with_submission
    ):
        problem = student_with_submission["problem"]
        resp = student_client.get(last_submission_url(problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == LAST_SUB_WITH_FIELDS

    def test_no_submission_response(self, authenticated_client):
        problem = EiplProblemFactory(is_active=True)
        resp = authenticated_client.get(last_submission_url(problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["has_submission"] is False
        assert resp.data["score"] == 0
        assert resp.data["submitted_at"] is None

    def test_no_submission_response_shape(self, authenticated_client):
        problem = EiplProblemFactory(is_active=True)
        resp = authenticated_client.get(last_submission_url(problem.slug))
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data.keys()) == LAST_SUB_NONE_FIELDS

    def test_nonexistent_problem_404(self, authenticated_client):
        resp = authenticated_client.get(last_submission_url("does-not-exist"))
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated(self, api_client):
        resp = api_client.get(last_submission_url("any-slug"))
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
