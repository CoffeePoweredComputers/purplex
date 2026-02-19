"""Tests for GET /api/instructor/courses/<course_id>/problem-sets/

Regression tests verifying that due_date and deadline_type are returned
in the GET response, not just in the PATCH response.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _url(course):
    return f"/api/instructor/courses/{course.course_id}/problem-sets/"


class TestGetProblemSetsIncludesDueDateFields:
    """Verify due_date and deadline_type appear in GET responses."""

    def test_get_problem_sets_includes_due_date(
        self, instructor_client, course_with_due_dates
    ):
        """Problem sets with a due_date should return the date in GET."""
        response = instructor_client.get(_url(course_with_due_dates))

        assert response.status_code == 200
        data = response.json()
        # course_with_due_dates has 3 problem sets ordered 0, 1, 2
        # Index 1 ("Soft Deadline Set") has a due_date
        soft = next(
            ps for ps in data if ps["problem_set"]["title"] == "Soft Deadline Set"
        )
        assert soft["due_date"] is not None

    def test_get_problem_sets_includes_deadline_type(
        self, instructor_client, course_with_due_dates
    ):
        """Problem sets with a hard deadline should return deadline_type='hard'."""
        response = instructor_client.get(_url(course_with_due_dates))

        assert response.status_code == 200
        data = response.json()
        hard = next(
            ps for ps in data if ps["problem_set"]["title"] == "Hard Deadline Set"
        )
        assert hard["deadline_type"] == "hard"

    def test_get_problem_sets_null_due_date(
        self, instructor_client, course_with_due_dates
    ):
        """Problem sets without a due_date should return due_date=None."""
        response = instructor_client.get(_url(course_with_due_dates))

        assert response.status_code == 200
        data = response.json()
        none_ps = next(
            ps for ps in data if ps["problem_set"]["title"] == "No Deadline Set"
        )
        assert none_ps["due_date"] is None
        assert none_ps["deadline_type"] == "none"

    def test_due_date_survives_round_trip(
        self, instructor_client, course, course_problem_set
    ):
        """PATCH a due_date, then GET — the value must persist (regression)."""
        due = (timezone.now() + timedelta(days=5)).isoformat()

        # PATCH to set due_date
        patch_url = (
            f"/api/instructor/courses/{course.course_id}"
            f"/problem-sets/{course_problem_set.id}/"
        )
        patch_resp = instructor_client.patch(
            patch_url,
            {"due_date": due, "deadline_type": "soft"},
            format="json",
        )
        assert patch_resp.status_code == 200

        # GET the list — the same due_date should be there
        get_resp = instructor_client.get(_url(course))
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert len(data) == 1
        assert data[0]["due_date"] is not None
        assert data[0]["deadline_type"] == "soft"
