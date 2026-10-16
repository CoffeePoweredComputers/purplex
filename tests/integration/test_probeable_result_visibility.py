"""Integration tests for student-facing truncation of probeable results.

Students see test rows only up to and including the first failure; the rest
are locked (Denny et al. ITiCSE 2025 Section 4.2; Tang et al. ACE 2026
Section 3.1.5). Instructor/admin views must still see every test.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
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

PIPELINE = "purplex.problems_app.tasks.pipeline"


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

    def test_spec_last_submission_locks_tests_after_first_failure(
        self, authenticated_client, user
    ):
        submission = _submission_with_three_tests(
            user, ProbeableSpecProblemFactory(), "probeable_spec"
        )

        response = authenticated_client.get(
            f"/api/last-submission/{submission.problem.slug}/"
        )
        assert response.status_code == status.HTTP_200_OK

        entries = response.data["results"]
        assert len(entries) == 1
        assert [r["isSuccessful"] for r in entries[0]["test_results"]] == [True, False]
        assert entries[0]["lockedCount"] == 1


class TestProbeableSpecHistory:
    """Spec submissions get the same ladder rules as probeable_code."""

    def test_probeable_spec_history_locks_tests_after_first_failure(
        self, authenticated_client, user
    ):
        submission = _submission_with_three_tests(
            user, ProbeableSpecProblemFactory(), "probeable_spec"
        )

        response = authenticated_client.get(
            f"/api/submissions/history/{submission.problem.slug}/"
        )
        assert response.status_code == status.HTTP_200_OK

        attempt = response.data["submissions"][0]
        assert attempt["tests_passed"] == 1
        assert attempt["total_tests"] == 3
        assert attempt["locked_count"] == 1
        variation = attempt["data"]["variations"][0]
        assert [r["passed"] for r in variation["test_results"]] == [True, False]
        assert variation["locked_count"] == 1

        entry = attempt["type_specific"]["test_results"][0]
        assert len(entry["test_results"]) == 2
        assert entry["lockedCount"] == 1

    def test_probeable_spec_history_reports_comprehension_level(
        self, authenticated_client, user
    ):
        problem = ProbeableSpecProblemFactory()
        SubmissionFactory(
            user=user,
            problem=problem,
            submission_type="probeable_spec",
            comprehension_level="high-level",
        )

        response = authenticated_client.get(f"/api/submissions/history/{problem.slug}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["submissions"][0]["comprehension_level"] == "high-level"

    def test_spec_pipeline_attempt_counts_one_version(self, authenticated_client, user):
        """Two tests and one generated version read 2/2, not 10/10 (five versions).

        Runs the real pipeline against the dev mock LLM so the mock's version
        count is exercised too; Docker and Redis are mocked.
        """
        from purplex.problems_app.tasks.pipeline import execute_eipl_pipeline

        problem = ProbeableSpecProblemFactory(
            is_active=True, requires_highlevel_comprehension=False
        )
        for order in range(2):
            TestCaseFactory(
                problem=problem, inputs=[order], expected_output=order**2, order=order
            )
        submission = SubmissionFactory(
            user=user,
            problem=problem,
            submission_type="probeable_spec",
            raw_input="It squares its argument.",
        )
        docker_result = {
            "testsPassed": 2,
            "totalTests": 2,
            "success": True,
            "results": [
                {"pass": True, "inputs": [i], "expected_output": i**2} for i in range(2)
            ],
        }

        with (
            override_settings(
                USE_MOCK_OPENAI=True, PRIVACY_ENABLE_AI_CONSENT_GATE=False
            ),
            patch(f"{PIPELINE}.SharedDockerServiceContext") as mock_ctx,
            patch(f"{PIPELINE}.publish_progress"),
            patch(f"{PIPELINE}.publish_completion"),
            patch("purplex.submissions.services.ProgressService.process_submission"),
        ):
            service = MagicMock()
            service.test_solution.return_value = docker_result
            mock_ctx.return_value.__enter__.return_value = service
            execute_eipl_pipeline.apply(
                args=[
                    problem.id,
                    submission.raw_input,
                    user.id,
                    submission.problem_set_id,
                    None,
                    str(submission.submission_id),
                ]
            ).get()

        assert service.test_solution.call_count == 1

        response = authenticated_client.get(f"/api/submissions/history/{problem.slug}/")
        assert response.status_code == status.HTTP_200_OK
        attempt = response.data["submissions"][0]
        assert attempt["tests_passed"] == 2
        assert attempt["total_tests"] == 2
        assert attempt["variations_count"] == 1
        assert attempt["locked_count"] == 0


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
