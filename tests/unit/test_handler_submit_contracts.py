"""
Tests for handler submit() method contracts.

Verifies the behavioral split between sync and async handlers:
- Async handlers: submit() queues Celery task, returns complete=False, never calls process_submission()
- Sync handlers: submit() processes inline, returns complete=True, never raises NotImplementedError
"""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from purplex.problems_app.handlers import get_handler
from purplex.problems_app.handlers.base import SubmissionOutcome

pytestmark = pytest.mark.unit

PROGRESS_SERVICE_PATH = "purplex.problems_app.services.progress_service.ProgressService"


# ─── Shared fixtures ───────────────────────────────────────────


def _make_mock_submission():
    """Create a mock Submission with the fields handlers expect."""
    sub = MagicMock()
    sub.submission_id = uuid.uuid4()
    sub.problem = MagicMock()
    sub.save = MagicMock()
    return sub


def _make_handler_context():
    """Create the context dict that the view passes to handler.submit()."""
    return {
        "user_id": 1,
        "problem_set": None,
        "problem_set_id": None,
        "course": None,
        "course_id": None,
        "request_id": str(uuid.uuid4()),
        "activated_hints": [],
    }


# ─── Async handler contracts ──────────────────────────────────

# Pipeline task paths at their definition site (lazy-imported by handlers)
ASYNC_HANDLER_CONFIGS = {
    "eipl": "purplex.problems_app.tasks.pipeline.execute_eipl_pipeline",
    "prompt": "purplex.problems_app.tasks.pipeline.execute_eipl_pipeline",
    "debug_fix": "purplex.problems_app.tasks.pipeline.execute_debug_fix_pipeline",
    "probeable_code": "purplex.problems_app.tasks.pipeline.execute_probeable_code_pipeline",
    "probeable_spec": "purplex.problems_app.tasks.pipeline.execute_eipl_pipeline",
}


class TestAsyncHandlerSubmitContract:
    """Async handlers: submit() queues Celery, returns complete=False, never calls process_submission()."""

    @pytest.fixture(params=list(ASYNC_HANDLER_CONFIGS.keys()))
    def async_setup(self, request):
        """Return (handler_type, handler_instance)."""
        return request.param, get_handler(request.param)

    def _patch_task(self, handler_type):
        """Return a context manager that patches the Celery task for this handler type."""
        task_path = ASYNC_HANDLER_CONFIGS[handler_type]
        mock_result = MagicMock()
        mock_result.id = "test-task-id"
        return patch(f"{task_path}.apply_async", return_value=mock_result)

    def test_submit_returns_complete_false(self, async_setup):
        handler_type, handler = async_setup
        with self._patch_task(handler_type):
            submission = _make_mock_submission()
            outcome = handler.submit(
                submission,
                "test input " * 5,
                MagicMock(id=1, slug="test"),
                _make_handler_context(),
            )

        assert isinstance(outcome, SubmissionOutcome)
        assert outcome.complete is False
        assert outcome.task_id is not None

    def test_submit_queues_celery_task(self, async_setup):
        handler_type, handler = async_setup
        with self._patch_task(handler_type) as mock_apply:
            handler.submit(
                _make_mock_submission(),
                "test input " * 5,
                MagicMock(id=1, slug="test"),
                _make_handler_context(),
            )

        mock_apply.assert_called_once()

    def test_submit_passes_submission_id_to_celery(self, async_setup):
        handler_type, handler = async_setup
        submission = _make_mock_submission()
        with self._patch_task(handler_type) as mock_apply:
            handler.submit(
                submission,
                "test input " * 5,
                MagicMock(id=1, slug="test"),
                _make_handler_context(),
            )

        call_kwargs = mock_apply.call_args.kwargs or mock_apply.call_args[1]
        celery_args = call_kwargs.get("args", [])
        assert str(submission.submission_id) in celery_args

    def test_submit_does_not_call_process_submission(self, async_setup):
        handler_type, handler = async_setup
        with (
            self._patch_task(handler_type),
            patch.object(
                type(handler), "process_submission", wraps=handler.process_submission
            ) as spy,
        ):
            handler.submit(
                _make_mock_submission(),
                "test input " * 5,
                MagicMock(id=1, slug="test"),
                _make_handler_context(),
            )

        spy.assert_not_called()

    def test_submit_uses_request_id_as_celery_task_id(self, async_setup):
        handler_type, handler = async_setup
        context = _make_handler_context()
        with self._patch_task(handler_type) as mock_apply:
            handler.submit(
                _make_mock_submission(),
                "test input " * 5,
                MagicMock(id=1, slug="test"),
                context,
            )

        call_kwargs = mock_apply.call_args.kwargs or mock_apply.call_args[1]
        assert call_kwargs["task_id"] == context["request_id"]


# ─── Sync handler contracts ───────────────────────────────────


class TestMCQSubmitContract:
    """MCQ: submit() processes inline, returns complete=True."""

    @pytest.fixture
    def mcq_handler(self):
        return get_handler("mcq")

    @pytest.fixture
    def mcq_problem(self):
        problem = MagicMock()
        problem.slug = "test-mcq"
        problem.options = [
            {"id": "a", "text": "Wrong", "is_correct": False},
            {
                "id": "b",
                "text": "Correct",
                "is_correct": True,
                "explanation": "Because.",
            },
        ]
        problem.allow_multiple = False
        return problem

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_returns_complete_true(
        self, _mock_progress, mcq_handler, mcq_problem
    ):
        submission = _make_mock_submission()
        outcome = mcq_handler.submit(
            submission, "b", mcq_problem, _make_handler_context()
        )

        assert isinstance(outcome, SubmissionOutcome)
        assert outcome.complete is True
        assert outcome.task_id is None

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_updates_submission_fields(
        self, _mock_progress, mcq_handler, mcq_problem
    ):
        submission = _make_mock_submission()
        mcq_handler.submit(submission, "b", mcq_problem, _make_handler_context())

        assert submission.score == 100
        assert submission.passed_all_tests is True
        assert submission.is_correct is True
        assert submission.execution_status == "completed"
        submission.save.assert_called_once()

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_incorrect_still_completes(
        self, _mock_progress, mcq_handler, mcq_problem
    ):
        submission = _make_mock_submission()
        outcome = mcq_handler.submit(
            submission, "a", mcq_problem, _make_handler_context()
        )

        assert outcome.complete is True
        assert submission.score == 0
        assert submission.is_correct is False

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_result_data_matches_frontend_contract(
        self, _mock_progress, mcq_handler, mcq_problem
    ):
        submission = _make_mock_submission()
        outcome = mcq_handler.submit(
            submission, "b", mcq_problem, _make_handler_context()
        )

        rd = outcome.result_data
        assert rd["problem_type"] == "mcq"
        assert "score" in rd
        assert "is_correct" in rd
        assert "selected_option" in rd
        assert "correct_option" in rd
        assert "submission_id" in rd

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_never_raises_not_implemented_error(
        self, _mock_progress, mcq_handler, mcq_problem
    ):
        submission = _make_mock_submission()
        outcome = mcq_handler.submit(
            submission, "b", mcq_problem, _make_handler_context()
        )
        assert outcome.complete is True


class TestRefuteSubmitContract:
    """Refute: submit() processes inline, returns complete=True."""

    @pytest.fixture
    def refute_handler(self):
        return get_handler("refute")

    @pytest.fixture
    def refute_problem(self):
        """Mock RefuteProblem with attributes the handler reads."""
        from purplex.problems_app.models import RefuteProblem

        problem = MagicMock(spec=RefuteProblem)
        problem.slug = "test-refute"
        problem.reference_solution = "def f(x):\n    return x * 2"
        problem.function_signature = "f(x: int) -> int"
        problem.claim_predicate = "result > 0"
        problem.claim_text = "The function always returns a positive number"
        return problem

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_returns_complete_true_disproven(
        self, _mock_progress, refute_handler, refute_problem
    ):
        submission = _make_mock_submission()
        # f(-5) = -10, which is NOT > 0, so claim is disproven
        outcome = refute_handler.submit(
            submission, json.dumps({"x": -5}), refute_problem, _make_handler_context()
        )

        assert isinstance(outcome, SubmissionOutcome)
        assert outcome.complete is True
        assert outcome.result_data["claim_disproven"] is True

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_returns_complete_true_not_disproven(
        self, _mock_progress, refute_handler, refute_problem
    ):
        submission = _make_mock_submission()
        # f(5) = 10, which IS > 0, so claim is NOT disproven
        outcome = refute_handler.submit(
            submission, json.dumps({"x": 5}), refute_problem, _make_handler_context()
        )

        assert outcome.complete is True
        assert outcome.result_data["claim_disproven"] is False

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_updates_submission_fields(
        self, _mock_progress, refute_handler, refute_problem
    ):
        submission = _make_mock_submission()
        refute_handler.submit(
            submission, json.dumps({"x": -5}), refute_problem, _make_handler_context()
        )

        assert submission.score == 100
        assert submission.is_correct is True
        assert submission.execution_status == "completed"
        submission.save.assert_called_once()

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_result_data_matches_frontend_contract(
        self, _mock_progress, refute_handler, refute_problem
    ):
        submission = _make_mock_submission()
        outcome = refute_handler.submit(
            submission, json.dumps({"x": -5}), refute_problem, _make_handler_context()
        )

        rd = outcome.result_data
        assert rd["problem_type"] == "refute"
        assert "score" in rd
        assert "is_correct" in rd
        assert "claim_disproven" in rd
        assert "input_args" in rd
        assert "result_value" in rd
        assert "submission_id" in rd

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_never_raises_not_implemented_error(
        self, _mock_progress, refute_handler, refute_problem
    ):
        submission = _make_mock_submission()
        outcome = refute_handler.submit(
            submission, json.dumps({"x": -5}), refute_problem, _make_handler_context()
        )
        assert outcome.complete is True

    @patch(PROGRESS_SERVICE_PATH)
    def test_submit_handles_invalid_json(
        self, _mock_progress, refute_handler, refute_problem
    ):
        submission = _make_mock_submission()
        outcome = refute_handler.submit(
            submission, "not json", refute_problem, _make_handler_context()
        )

        assert outcome.complete is True
        assert outcome.error is not None
        assert "JSON" in outcome.error
