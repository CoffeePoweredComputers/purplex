"""
API-level tests for ActivitySubmissionView.

Validates the HTTP boundary where handler sync/async behavior
translates to 200 vs 202 responses for the frontend.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from tests.factories import (
    CourseEnrollmentFactory,
    CourseFactory,
    CourseProblemSetFactory,
    DebugFixProblemFactory,
    EiplProblemFactory,
    McqProblemFactory,
    ProbeableCodeProblemFactory,
    ProbeableSpecProblemFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    PromptProblemFactory,
    RefuteProblemFactory,
    TestCaseFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

SUBMIT_URL = reverse("submit_activity")

EIPL_PIPELINE = "purplex.problems_app.tasks.pipeline.execute_eipl_pipeline"
DEBUG_FIX_PIPELINE = "purplex.problems_app.tasks.pipeline.execute_debug_fix_pipeline"
PROBEABLE_CODE_PIPELINE = (
    "purplex.problems_app.tasks.pipeline.execute_probeable_code_pipeline"
)
PROGRESS_SERVICE = "purplex.problems_app.services.progress_service.ProgressService"


# ─── Shared fixtures ───────────────────────────────────────────


@pytest.fixture
def enrolled_user(ai_consented_user):
    """User with AI_PROCESSING consent, enrolled in a course with a problem set.

    Composed on `ai_consented_user` so the consent dependency is an explicit
    named fixture rather than a silent grant. Tests exercising AI-consent
    denial should depend on `user_without_ai_consent` instead — see
    `tests/integration/test_eipl_submission_consent.py` for the canonical
    pattern.
    """
    course = CourseFactory()
    CourseEnrollmentFactory(user=ai_consented_user, course=course)
    problem_set = ProblemSetFactory()
    CourseProblemSetFactory(course=course, problem_set=problem_set)
    return {"user": ai_consented_user, "course": course, "problem_set": problem_set}


@pytest.fixture
def auth_client(enrolled_user):
    """Authenticated API client for the enrolled user."""
    client = APIClient()
    client.force_authenticate(user=enrolled_user["user"])
    return client


def _submit(client, problem_slug, raw_input, problem_set_slug=None, course_id=None):
    """POST to /api/submit/ with standard payload."""
    data = {"problem_slug": problem_slug, "raw_input": raw_input}
    if problem_set_slug:
        data["problem_set_slug"] = problem_set_slug
    if course_id:
        data["course_id"] = course_id
    return client.post(SUBMIT_URL, data, format="json")


def _add_to_problem_set(problem, problem_set):
    """Add problem to problem_set via membership factory."""
    ProblemSetMembershipFactory(problem_set=problem_set, problem=problem)


# ─── Sync handler view tests (MCQ) ───────────────────────────


class TestMCQSubmissionView:
    """MCQ submissions should return HTTP 200 (sync complete)."""

    @pytest.fixture
    def mcq_problem(self, enrolled_user):
        problem = McqProblemFactory()
        _add_to_problem_set(problem, enrolled_user["problem_set"])
        return problem

    @patch(PROGRESS_SERVICE)
    def test_correct_answer_returns_200(
        self, _mock_progress, auth_client, enrolled_user, mcq_problem
    ):
        response = _submit(
            auth_client,
            mcq_problem.slug,
            "b",
            problem_set_slug=enrolled_user["problem_set"].slug,
            course_id=enrolled_user["course"].course_id,
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.data}"
        )
        assert response.data["status"] == "complete"
        assert response.data["is_correct"] is True
        assert response.data["problem_type"] == "mcq"

    @patch(PROGRESS_SERVICE)
    def test_wrong_answer_still_returns_200(
        self, _mock_progress, auth_client, enrolled_user, mcq_problem
    ):
        response = _submit(
            auth_client,
            mcq_problem.slug,
            "a",
            problem_set_slug=enrolled_user["problem_set"].slug,
            course_id=enrolled_user["course"].course_id,
        )

        assert response.status_code == 200
        assert response.data["status"] == "complete"
        assert response.data["is_correct"] is False

    @patch(PROGRESS_SERVICE)
    def test_response_shape_matches_frontend_contract(
        self, _mock_progress, auth_client, enrolled_user, mcq_problem
    ):
        response = _submit(
            auth_client,
            mcq_problem.slug,
            "b",
            problem_set_slug=enrolled_user["problem_set"].slug,
            course_id=enrolled_user["course"].course_id,
        )

        assert "submission_id" in response.data
        assert "score" in response.data
        assert "is_correct" in response.data
        assert "problem_type" in response.data
        assert "status" in response.data


# ─── Sync handler view tests (Refute) ────────────────────────


class TestRefuteSubmissionView:
    """Refute submissions should return HTTP 200 (sync complete)."""

    @pytest.fixture
    def refute_problem(self, enrolled_user):
        problem = RefuteProblemFactory()
        _add_to_problem_set(problem, enrolled_user["problem_set"])
        return problem

    @patch(PROGRESS_SERVICE)
    def test_counterexample_returns_200(
        self, _mock_progress, auth_client, enrolled_user, refute_problem
    ):
        # f(-5) = -10, not > 0 → claim disproven
        response = _submit(
            auth_client,
            refute_problem.slug,
            json.dumps({"x": -5}),
            problem_set_slug=enrolled_user["problem_set"].slug,
            course_id=enrolled_user["course"].course_id,
        )

        assert response.status_code == 200
        assert response.data["status"] == "complete"
        assert response.data["claim_disproven"] is True

    @patch(PROGRESS_SERVICE)
    def test_non_counterexample_still_returns_200(
        self, _mock_progress, auth_client, enrolled_user, refute_problem
    ):
        response = _submit(
            auth_client,
            refute_problem.slug,
            json.dumps({"x": 5}),
            problem_set_slug=enrolled_user["problem_set"].slug,
            course_id=enrolled_user["course"].course_id,
        )

        assert response.status_code == 200
        assert response.data["claim_disproven"] is False


# ─── Async handler view tests ────────────────────────────────

ASYNC_PROBLEM_FACTORIES = {
    "eipl": (EiplProblemFactory, EIPL_PIPELINE),
    "prompt": (PromptProblemFactory, EIPL_PIPELINE),
    "debug_fix": (DebugFixProblemFactory, DEBUG_FIX_PIPELINE),
    "probeable_code": (ProbeableCodeProblemFactory, PROBEABLE_CODE_PIPELINE),
    "probeable_spec": (ProbeableSpecProblemFactory, EIPL_PIPELINE),
}

# Input that passes validation for each handler type
ASYNC_VALID_INPUTS = {
    "eipl": "This is a valid description of what the code does for testing purposes",
    "prompt": "This is a valid description of what the image represents for testing",
    "debug_fix": "def add(a, b):\n    return a + b",
    "probeable_code": "def mystery(x):\n    return x * 2",
    "probeable_spec": "This is a valid description of the discovered function behavior",
}


class TestAsyncSubmissionView:
    """Async submissions should return HTTP 202 with task_id."""

    @pytest.fixture(params=list(ASYNC_PROBLEM_FACTORIES.keys()))
    def async_problem(self, request, enrolled_user):
        handler_type = request.param
        factory_cls, pipeline_path = ASYNC_PROBLEM_FACTORIES[handler_type]
        problem = factory_cls()
        _add_to_problem_set(problem, enrolled_user["problem_set"])
        TestCaseFactory(problem=problem, inputs=[1], expected_output=2)
        return handler_type, problem, pipeline_path

    def test_returns_202_with_task_id(self, auth_client, enrolled_user, async_problem):
        handler_type, problem, pipeline_path = async_problem
        raw_input = ASYNC_VALID_INPUTS[handler_type]

        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        with patch(f"{pipeline_path}.apply_async", return_value=mock_task):
            response = _submit(
                auth_client,
                problem.slug,
                raw_input,
                problem_set_slug=enrolled_user["problem_set"].slug,
                course_id=enrolled_user["course"].course_id,
            )

        assert response.status_code == 202, (
            f"{handler_type}: expected 202, got {response.status_code}: {response.data}"
        )
        assert response.data["status"] == "processing"
        assert "task_id" in response.data

    def test_response_shape_matches_frontend_contract(
        self, auth_client, enrolled_user, async_problem
    ):
        handler_type, problem, pipeline_path = async_problem
        raw_input = ASYNC_VALID_INPUTS[handler_type]

        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        with patch(f"{pipeline_path}.apply_async", return_value=mock_task):
            response = _submit(
                auth_client,
                problem.slug,
                raw_input,
                problem_set_slug=enrolled_user["problem_set"].slug,
                course_id=enrolled_user["course"].course_id,
            )

        # These are the keys the frontend TypeScript types expect
        assert "request_id" in response.data
        assert "task_id" in response.data
        assert "status" in response.data
        assert "problem_type" in response.data
        assert "stream_url" in response.data
        assert response.data["stream_url"].startswith("/api/tasks/")

    def test_no_500_from_not_implemented_error(
        self, auth_client, enrolled_user, async_problem
    ):
        """The NotImplementedError from base process_submission() must never surface as HTTP 500."""
        handler_type, problem, pipeline_path = async_problem
        raw_input = ASYNC_VALID_INPUTS[handler_type]

        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        with patch(f"{pipeline_path}.apply_async", return_value=mock_task):
            response = _submit(
                auth_client,
                problem.slug,
                raw_input,
                problem_set_slug=enrolled_user["problem_set"].slug,
                course_id=enrolled_user["course"].course_id,
            )

        assert response.status_code != 500


# ─── Error path tests ────────────────────────────────────────


class TestSubmissionViewErrors:
    """Error handling in the submission endpoint."""

    def test_unauthenticated_returns_403(self, enrolled_user):
        client = APIClient()  # no auth
        problem = McqProblemFactory()
        _add_to_problem_set(problem, enrolled_user["problem_set"])

        response = _submit(client, problem.slug, "b")
        assert response.status_code == 403

    def test_missing_problem_slug_returns_400(self, auth_client):
        response = auth_client.post(SUBMIT_URL, {"raw_input": "hello"}, format="json")
        assert response.status_code == 400

    def test_nonexistent_problem_returns_400(self, auth_client):
        response = _submit(auth_client, "nonexistent-slug", "some input")
        assert response.status_code == 400
