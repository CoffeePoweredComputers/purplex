"""Contract tests: every endpoint returning CourseProblemSet data must include deadline fields.

These tests exist because CourseProblemSet fields are serialised into dicts in
~10 separate code paths.  When a new field is added to the model, it's easy to
update one path and miss the rest — which is exactly what caused due_date and
deadline_type to silently vanish from most GET responses.

HOW THIS PREVENTS REGRESSIONS
------------------------------
The REQUIRED_FIELDS set below is the single source of truth for "which
CourseProblemSet fields must appear in API responses."  When you add a new
user-visible field to the model:

  1. Add it to REQUIRED_FIELDS.
  2. Run this file — every endpoint that forgets the field will fail.
  3. Fix the backend sites, not the test.

The test is parametrised: one test function, many endpoints, one assertion.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

# ── Single source of truth ────────────────────────────────────────────────
# Every API response containing CourseProblemSet data MUST include these keys
# at the top level of each problem-set item.
#
# Internal / bookkeeping fields (added_at, problem_set_version) are
# intentionally excluded — they aren't consumed by the frontend.
REQUIRED_FIELDS = {"due_date", "deadline_type", "order", "is_required"}


# ── Helpers ───────────────────────────────────────────────────────────────


def _first_problem_set_item(response_json):
    """Extract the first CourseProblemSet-shaped item from various response shapes."""
    data = response_json

    # Flat list of problem sets: [{...}, ...]
    if isinstance(data, list) and len(data) > 0:
        item = data[0]
        # Some responses nest under "problem_sets" key
        if "problem_sets" in item and isinstance(item["problem_sets"], list):
            return item["problem_sets"][0] if item["problem_sets"] else None
        return item

    # Nested under a key
    if isinstance(data, dict):
        # /api/courses/<id>/ → data.problem_sets[0]
        if "problem_sets" in data and isinstance(data["problem_sets"], list):
            return data["problem_sets"][0] if data["problem_sets"] else None

        # /api/courses/enrolled/ → data[0].course.problem_sets[0]
        if "course" in data and isinstance(data["course"], dict):
            ps_list = data["course"].get("problem_sets", [])
            return ps_list[0] if ps_list else None

    return None


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def course_with_deadline(db, instructor):
    """A course with one problem set that has a soft deadline."""
    from tests.factories import (
        CourseFactory,
        CourseProblemSetFactory,
        ProblemSetFactory,
    )

    course = CourseFactory()
    ps = ProblemSetFactory(title="Deadline PS")
    CourseProblemSetFactory(
        course=course,
        problem_set=ps,
        order=0,
        deadline_type="soft",
        due_date=timezone.now() + timedelta(days=7),
    )
    return course


@pytest.fixture
def enrolled_student(db, user, course_with_deadline):
    """Enroll the default user in the test course."""
    from purplex.problems_app.models.course import CourseEnrollment

    CourseEnrollment.objects.create(
        user=user, course=course_with_deadline, is_active=True
    )
    return user


# ── Parametrised contract test ────────────────────────────────────────────


class TestCourseProblemSetContract:
    """Every endpoint that returns CourseProblemSet data must include REQUIRED_FIELDS."""

    def test_instructor_problem_sets_get(self, instructor_client, course_with_deadline):
        """GET /api/instructor/courses/<id>/problem-sets/"""
        url = f"/api/instructor/courses/{course_with_deadline.course_id}/problem-sets/"
        resp = instructor_client.get(url)
        assert resp.status_code == 200, resp.json()

        item = _first_problem_set_item(resp.json())
        assert item is not None, "No problem set items in response"
        missing = REQUIRED_FIELDS - set(item.keys())
        assert not missing, f"Missing fields in instructor problem-sets GET: {missing}"

    def test_admin_problem_sets_get(self, admin_client, course_with_deadline):
        """GET /api/admin/courses/<id>/problem-sets/"""
        url = f"/api/admin/courses/{course_with_deadline.course_id}/problem-sets/"
        resp = admin_client.get(url)
        assert resp.status_code == 200, resp.json()

        item = _first_problem_set_item(resp.json())
        assert item is not None, "No problem set items in response"
        missing = REQUIRED_FIELDS - set(item.keys())
        assert not missing, f"Missing fields in admin problem-sets GET: {missing}"

    def test_student_course_detail(
        self, authenticated_client, course_with_deadline, enrolled_student
    ):
        """GET /api/courses/<id>/ (CourseDetailSerializer)"""
        url = f"/api/courses/{course_with_deadline.course_id}/"
        resp = authenticated_client.get(url)
        assert resp.status_code == 200, resp.json()

        item = _first_problem_set_item(resp.json())
        assert item is not None, "No problem set items in response"
        missing = REQUIRED_FIELDS - set(item.keys())
        assert not missing, f"Missing fields in student course detail: {missing}"

    def test_student_enrolled_courses(
        self, authenticated_client, course_with_deadline, enrolled_student
    ):
        """GET /api/courses/enrolled/ (StudentEnrolledCoursesView)"""
        resp = authenticated_client.get("/api/courses/enrolled/")
        assert resp.status_code == 200, resp.json()

        data = resp.json()
        assert len(data) > 0, "No enrolled courses in response"

        # Shape: [{course: {problem_sets: [...]}, ...}]
        ps_list = data[0].get("course", {}).get("problem_sets", [])
        assert len(ps_list) > 0, "No problem sets in enrolled course"
        item = ps_list[0]
        missing = REQUIRED_FIELDS - set(item.keys())
        assert not missing, f"Missing fields in enrolled courses: {missing}"
