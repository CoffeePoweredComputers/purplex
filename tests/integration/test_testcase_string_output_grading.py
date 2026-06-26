"""
Regression tests for string-typed ``expected_output`` test cases.

Reproduces the reported bug: a problem about strings has test cases whose
expected output is a *numeric-looking string* (e.g. the string ``"123"``).
Such a test case **passes in the instructor authoring panel** but **fails for
students**.

Root cause (verified, see issue #136 for the related frontend angle):

    ``TestCase.expected_output`` is a Django ``JSONField`` — values are already
    deserialized to native Python types on read, so a stored string ``"123"``
    comes back as the Python ``str`` ``"123"`` (the final value).

    The STUDENT grading path then runs ``json.loads()`` on that value a *second*
    time (``pipeline.py`` "Parse JSON fields if needed" block, duplicated at the
    debug-fix and probeable-code pipelines). ``json.loads("123")`` returns the
    int ``123`` — a double-decode that corrupts the type.

    The AUTHORING path (``AdminTestProblemView``) forwards the request body
    straight to the grader with **no** such re-parse, so it keeps the string.

The downstream grader ``compare_results`` is type-strict (str != int), so the
student's correct string answer ``"123"`` is marked FAILED against the corrupted
int ``123`` — while the identical author-side run passes. That asymmetry is the
"super weird" symptom.

These tests assert on the payload *handed to the grader* (the real defect site),
not on the in-Docker verdict, so they are fast and hermetic. ``compare_results``'s
strictness — which is correct and must NOT be weakened — is covered separately in
``tests/unit/test_docker_execution_service.py::TestTestRunnerComparison``.
"""

from unittest.mock import MagicMock, patch

import pytest

from tests.factories import (
    EiplProblemFactory,
    ProbeableCodeProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    TestCaseFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = pytest.mark.integration


def _capture_test_cases(mock_service):
    """Return the ``test_cases`` list passed to ``service.test_solution(...)``.

    Signature is ``test_solution(code, function_name, test_cases)`` (positional).
    """
    assert mock_service.test_solution.called, "grader was never invoked"
    return mock_service.test_solution.call_args.args[2]


# =============================================================================
# Student grading path — the bug. These currently FAIL (the value is coerced).
# =============================================================================


@pytest.mark.django_db
class TestStudentPathCoercesStringExpectedOutput:
    """The student grading path must hand the grader the author's *string*,
    not a json.loads-coerced int/float/bool."""

    def test_variation_helper_preserves_string_expected_output(self, db):
        """Minimal repro through the shared loader+normalize path.

        ``test_variation_helper`` loads test cases from the DB and applies the
        exact "Parse JSON fields if needed" normalization used by the student
        pipelines. A stored string ``"123"`` must reach the grader as ``str``.
        """
        from purplex.problems_app.tasks.pipeline import test_variation_helper

        problem = EiplProblemFactory(
            function_name="stringify",
            function_signature="def stringify(n: int) -> str",
            reference_solution="def stringify(n):\n    return str(n)",
        )
        # Author's intent: the function returns the STRING "123".
        TestCaseFactory(problem=problem, inputs=[123], expected_output="123")

        mock_result = {
            "testsPassed": 1,
            "totalTests": 1,
            "success": True,
            "results": [{"pass": True}],
        }
        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_result
            MockCtx.return_value.__enter__.return_value = mock_service

            test_variation_helper("def stringify(n):\n    return str(n)", problem.id, 0)

        graded = _capture_test_cases(mock_service)[0]["expected_output"]
        assert isinstance(graded, str), (
            f"student path corrupted the type: expected str, got "
            f"{type(graded).__name__} ({graded!r}) — json.loads double-decode"
        )
        assert graded == "123"

    def test_probeable_code_pipeline_preserves_string_expected_output(self, db):
        """The genuine student submission task (probeable-code) must not coerce."""
        from purplex.problems_app.tasks.pipeline import (
            execute_probeable_code_pipeline,
        )

        user = UserFactory()
        UserProfileFactory(user=user)
        problem = ProbeableCodeProblemFactory(
            is_active=True,
            function_name="stringify",
            function_signature="def stringify(n: int) -> str",
            reference_solution="def stringify(n):\n    return str(n)",
        )
        problem_set = ProblemSetFactory()
        ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)
        TestCaseFactory(problem=problem, inputs=[123], expected_output="123")

        mock_result = {
            "testsPassed": 1,
            "totalTests": 1,
            "success": True,
            "results": [{"pass": True}],
        }
        with (
            patch(
                "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
            ) as MockCtx,
            patch("purplex.problems_app.tasks.pipeline.publish_progress"),
            patch("purplex.problems_app.tasks.pipeline.publish_completion"),
            patch("purplex.submissions.services.ProgressService.process_submission"),
        ):
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_result
            MockCtx.return_value.__enter__.return_value = mock_service

            execute_probeable_code_pipeline.apply(
                args=[
                    problem.id,
                    "def stringify(n):\n    return str(n)",
                    user.id,
                    problem_set.id,
                ]
            )

        graded = _capture_test_cases(mock_service)[0]["expected_output"]
        assert isinstance(graded, str), (
            f"student path corrupted the type: expected str, got "
            f"{type(graded).__name__} ({graded!r})"
        )
        assert graded == "123"


# =============================================================================
# Authoring path — the control. These PASS today (no coercion happens here),
# proving the asymmetry that makes the bug "pass in authoring, fail for student".
# =============================================================================


@pytest.mark.django_db
class TestAuthoringPathPreservesStringExpectedOutput:
    """The authoring 'Test Solution' endpoint forwards the string unchanged."""

    def test_admin_test_problem_keeps_string_expected_output(self, admin_client):
        payload = {
            "function_name": "stringify",
            "reference_solution": "def stringify(n):\n    return str(n)",
            "test_cases": [{"inputs": [123], "expected_output": "123"}],
        }
        mock_result = {
            "testsPassed": 1,
            "totalTests": 1,
            "success": True,
            "results": [{"pass": True}],
        }
        with patch(
            "purplex.problems_app.views.admin_views.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_result
            MockCtx.return_value.__enter__.return_value = mock_service

            response = admin_client.post(
                "/api/admin/test-problem/", payload, format="json"
            )

        assert response.status_code == 200, response.content
        graded = _capture_test_cases(mock_service)[0]["expected_output"]
        # Control assertion: the authoring path leaves the string alone.
        assert isinstance(graded, str)
        assert graded == "123"


# =============================================================================
# The discrepancy, stated as one test: both panels must agree on the type.
# =============================================================================


@pytest.mark.django_db
class TestAuthoringAndStudentPathsAgree:
    """Both panels must hand the grader the *same* type for the same test case.

    This is the user-visible "passes in authoring, fails for student" symptom,
    expressed directly. Currently fails because the student path coerces.
    """

    def test_both_paths_grade_the_same_type(self, db, admin_client):
        problem = ProbeableCodeProblemFactory(
            is_active=True,
            function_name="stringify",
            function_signature="def stringify(n: int) -> str",
            reference_solution="def stringify(n):\n    return str(n)",
        )
        TestCaseFactory(problem=problem, inputs=[123], expected_output="123")

        mock_result = {
            "testsPassed": 1,
            "totalTests": 1,
            "success": True,
            "results": [{"pass": True}],
        }

        # --- Authoring path (inline request body, as the editor would POST) ---
        with patch(
            "purplex.problems_app.views.admin_views.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_result
            MockCtx.return_value.__enter__.return_value = mock_service
            admin_client.post(
                "/api/admin/test-problem/",
                {
                    "function_name": "stringify",
                    "reference_solution": problem.reference_solution,
                    "test_cases": [{"inputs": [123], "expected_output": "123"}],
                },
                format="json",
            )
            authoring_type = type(
                _capture_test_cases(mock_service)[0]["expected_output"]
            )

        # --- Student path (loaded from the persisted TestCase) ---
        from purplex.problems_app.tasks.pipeline import test_variation_helper

        with patch(
            "purplex.problems_app.tasks.pipeline.SharedDockerServiceContext"
        ) as MockCtx:
            mock_service = MagicMock()
            mock_service.test_solution.return_value = mock_result
            MockCtx.return_value.__enter__.return_value = mock_service
            test_variation_helper(problem.reference_solution, problem.id, 0)
            student_type = type(_capture_test_cases(mock_service)[0]["expected_output"])

        assert authoring_type is student_type, (
            f"panels disagree on expected_output type: authoring graded a "
            f"{authoring_type.__name__}, student graded a {student_type.__name__}"
        )
