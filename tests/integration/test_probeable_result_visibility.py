"""Integration tests for student-facing truncation of probeable_code results.

Students see test rows only up to and including the first failure; the rest
are locked (Denny et al. ITiCSE 2025 Section 4.2; Tang et al. ACE 2026
Section 3.1.5). Instructor/admin views must still see every test.
"""

import pytest
from rest_framework import status

from tests.factories import (
    CodeVariationFactory,
    ProbeableCodeProblemFactory,
    ProbeableSpecProblemFactory,
    SubmissionFactory,
    TestCaseFactory,
    TestExecutionFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _submission_with_three_tests(user, problem, submission_type):
    """A submission whose tests ran [pass, fail, fail] in one variation."""
    submission = SubmissionFactory(
        user=user,
        problem=problem,
        submission_type=submission_type,
        raw_input="def mystery(x):\n    return x + 1",
        processed_code="def mystery(x):\n    return x + 1",
        score=33,
    )
    variation = CodeVariationFactory(
        submission=submission,
        variation_index=0,
        generated_code=submission.processed_code,
        tests_passed=1,
        tests_total=3,
        score=33,
    )
    for order, passed in enumerate((True, False, False)):
        test_case = TestCaseFactory(
            problem=problem, inputs=[order], expected_output=order * 2, order=order
        )
        TestExecutionFactory(
            submission=submission,
            code_variation=variation,
            test_case=test_case,
            execution_order=order,
            passed=passed,
            input_values=[order],
            expected_output=order * 2,
            actual_output=order * 2 if passed else order + 1,
        )
    return submission


@pytest.fixture
def probeable_submission(user):
    """A probeable_code submission whose tests ran [pass, fail, fail]."""
    return _submission_with_three_tests(
        user, ProbeableCodeProblemFactory(), "probeable_code"
    )


class TestStudentHistoryTruncation:
    def test_history_locks_tests_after_first_failure(
        self, authenticated_client, probeable_submission
    ):
        response = authenticated_client.get(
            f"/api/submissions/history/{probeable_submission.problem.slug}/"
        )
        assert response.status_code == status.HTTP_200_OK

        attempt = response.data["submissions"][0]
        assert attempt["tests_passed"] == 1
        assert attempt["total_tests"] == 3
        assert attempt["locked_count"] == 1

        variation = attempt["data"]["variations"][0]
        assert [r["passed"] for r in variation["test_results"]] == [True, False]
        assert variation["tests_passed"] == 1
        assert variation["total_tests"] == 3
        assert variation["locked_count"] == 1

        # Top-level rows are only populated for submissions without variations
        # (covered by test_top_level_rows_truncated_without_variations).
        assert attempt["data"]["test_results"] == []

        entry = attempt["type_specific"]["test_results"][0]
        assert len(entry["test_results"]) == 2
        assert entry["testsPassed"] == 1
        assert entry["totalTests"] == 3
        assert entry["lockedCount"] == 1

    def test_top_level_rows_truncated_without_variations(
        self, authenticated_client, user
    ):
        problem = ProbeableCodeProblemFactory()
        submission = SubmissionFactory(
            user=user, problem=problem, submission_type="probeable_code"
        )
        for order, passed in enumerate((True, False, False)):
            TestExecutionFactory(
                submission=submission, execution_order=order, passed=passed
            )

        response = authenticated_client.get(f"/api/submissions/history/{problem.slug}/")
        assert response.status_code == status.HTTP_200_OK

        attempt = response.data["submissions"][0]
        assert [r["passed"] for r in attempt["data"]["test_results"]] == [
            True,
            False,
        ]
        assert attempt["tests_passed"] == 1
        assert attempt["total_tests"] == 3
        assert attempt["locked_count"] == 1


class TestStudentLastSubmissionTruncation:
    def test_last_submission_locks_tests_after_first_failure(
        self, authenticated_client, probeable_submission
    ):
        response = authenticated_client.get(
            f"/api/last-submission/{probeable_submission.problem.slug}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_submission"] is True

        entry = response.data["results"][0]
        assert [r["isSuccessful"] for r in entry["test_results"]] == [True, False]
        assert entry["testsPassed"] == 1
        assert entry["totalTests"] == 3
        assert entry["lockedCount"] == 1


class TestOtherTypesUntruncated:
    def test_probeable_spec_history_shows_every_test(self, authenticated_client, user):
        submission = _submission_with_three_tests(
            user, ProbeableSpecProblemFactory(), "probeable_spec"
        )

        response = authenticated_client.get(
            f"/api/submissions/history/{submission.problem.slug}/"
        )
        assert response.status_code == status.HTTP_200_OK

        attempt = response.data["submissions"][0]
        assert "locked_count" not in attempt
        variation = attempt["data"]["variations"][0]
        assert [r["passed"] for r in variation["test_results"]] == [
            True,
            False,
            False,
        ]
        assert "locked_count" not in variation


class TestStaffViewUntruncated:
    def test_admin_detail_returns_all_tests(self, admin_client, probeable_submission):
        response = admin_client.get(
            f"/api/admin/submissions/{probeable_submission.submission_id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert [r["passed"] for r in response.data["test_results"]] == [
            True,
            False,
            False,
        ]
