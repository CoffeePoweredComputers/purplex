"""
Tests for pipeline transaction boundary correctness.

These tests verify that:
- DB writes are atomic (partial failures roll back cleanly)
- ProgressService calls are outside transaction blocks
- Idempotency handlers only catch celery_task_id collisions, not unrelated errors
- ProgressService failures don't roll back committed submissions

The MCQ pipeline is the only pipeline testable without Docker/code execution.
Debug Fix and Probeable Code pipelines have identical transaction structure
but require integration tests to exercise fully.

Known limitation: _record_eipl_test_results_no_transaction (used by EiPL,
Debug Fix, and Probeable Code when test_execution_data is present) still calls
ProgressService.process_submission INSIDE the transaction.atomic() block.
This is tracked in V01_REVIEW.md Task 6.
"""

from unittest.mock import call, patch

import pytest
from django.db import IntegrityError

from purplex.problems_app.tasks.pipeline import execute_mcq_pipeline
from purplex.submissions.models import Submission
from tests.factories import McqProblemFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestMcqTransactionBoundaries:
    """Verify MCQ pipeline transaction isolation and error propagation."""

    @pytest.fixture
    def mcq_setup(self, user, problem_set):
        """MCQ problem with known correct answer (option 'b')."""
        problem = McqProblemFactory(
            options=[
                {"id": "a", "text": "Wrong", "is_correct": False},
                {"id": "b", "text": "Right", "is_correct": True},
            ]
        )
        return {"user": user, "problem": problem, "problem_set": problem_set}

    def _run_mcq(self, mcq_setup, selected_option, task_id, throw=True):
        """Helper to run MCQ pipeline synchronously via Celery .apply().

        Args:
            throw: If False, exceptions are stored in the result rather than
                raised immediately. Use throw=False when you need to inspect
                the result AND check DB state after a failure.
        """
        return execute_mcq_pipeline.apply(
            kwargs={
                "problem_id": mcq_setup["problem"].pk,
                "selected_option": selected_option,
                "user_id": mcq_setup["user"].id,
                "problem_set_id": mcq_setup["problem_set"].pk,
                "course_id": None,
            },
            task_id=task_id,
            throw=throw,
        )

    # -----------------------------------------------------------------
    # 1. ProgressService error propagation (the bug I fixed)
    # -----------------------------------------------------------------

    @patch(
        "purplex.problems_app.services.progress_service.ProgressService.process_submission",
        side_effect=IntegrityError("F() expression crash in progress rollup"),
    )
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_progress_integrity_error_not_swallowed_by_idempotency_handler(
        self, mock_publish, mock_progress, mcq_setup
    ):
        """
        ProgressService IntegrityError must NOT be caught by the celery_task_id
        idempotency handler.

        Before the fix, ProgressService.process_submission was inside the
        try/except IntegrityError block. Any IntegrityError from ProgressService
        (e.g., the F() expression bug in update_or_create) would be caught,
        checked for 'celery_task_id' in str(e) — which wouldn't match — and
        then re-raised. This test verifies the error propagates correctly AND
        the submission is still committed.
        """
        result = self._run_mcq(
            mcq_setup, "b", "tx-progress-integrity-error", throw=False
        )

        # The task should have failed
        assert result.state == "FAILURE"
        with pytest.raises(IntegrityError, match="F\\(\\) expression crash"):
            result.get()

        # Submission should still exist — it was committed before ProgressService ran
        assert Submission.objects.filter(
            celery_task_id="tx-progress-integrity-error"
        ).exists()

    @patch(
        "purplex.problems_app.services.progress_service.ProgressService.process_submission",
        side_effect=ValueError("unexpected progress failure"),
    )
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_progress_generic_error_propagates(
        self, mock_publish, mock_progress, mcq_setup
    ):
        """Non-IntegrityError from ProgressService should also propagate."""
        result = self._run_mcq(
            mcq_setup, "b", "tx-progress-generic-error", throw=False
        )

        assert result.state == "FAILURE"
        with pytest.raises(ValueError, match="unexpected progress failure"):
            result.get()

        # Submission still committed
        assert Submission.objects.filter(
            celery_task_id="tx-progress-generic-error"
        ).exists()

    # -----------------------------------------------------------------
    # 2. Submission persistence after ProgressService failure
    # -----------------------------------------------------------------

    @patch(
        "purplex.problems_app.services.progress_service.ProgressService.process_submission",
        side_effect=Exception("progress crashed"),
    )
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_submission_persisted_despite_progress_failure(
        self, mock_publish, mock_progress, mcq_setup
    ):
        """
        Submission must be fully saved (correct fields) even if
        ProgressService fails afterward. This proves the transaction
        committed before ProgressService was called.
        """
        result = self._run_mcq(
            mcq_setup, "b", "tx-persist-despite-failure", throw=False
        )

        # Task failed, but submission should be fully saved
        assert result.state == "FAILURE"

        submission = Submission.objects.get(
            celery_task_id="tx-persist-despite-failure"
        )
        assert submission.completion_status == "complete"
        assert submission.score == 100
        assert submission.is_correct is True
        assert submission.execution_status == "completed"

    # -----------------------------------------------------------------
    # 3. Transaction atomicity — rollback on mid-write failure
    # -----------------------------------------------------------------

    @patch(
        "purplex.problems_app.services.progress_service.ProgressService.process_submission"
    )
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_transaction_rollback_on_save_failure(
        self, mock_publish, mock_progress, mcq_setup
    ):
        """
        If submission.save() fails inside the transaction, the entire
        transaction should roll back — no orphaned submission record.

        We use a counter-based mock: allow the first save() call (from
        Submission.objects.create) and fail on the second (the explicit
        submission.save() after field updates).
        """
        original_save = Submission.save
        save_call_count = {"n": 0}

        def save_then_fail(self_sub, *args, **kwargs):
            save_call_count["n"] += 1
            if save_call_count["n"] > 1:
                raise IntegrityError("simulated save failure on update")
            return original_save(self_sub, *args, **kwargs)

        with patch.object(Submission, "save", save_then_fail):
            result = self._run_mcq(
                mcq_setup, "b", "tx-rollback-test", throw=False
            )

        assert result.state == "FAILURE"

        # No submission should exist — the transaction rolled back both
        # the create AND the failed save
        assert not Submission.objects.filter(
            celery_task_id="tx-rollback-test"
        ).exists()

        # ProgressService should NOT have been called (transaction never committed)
        assert mock_progress.call_count == 0

    # -----------------------------------------------------------------
    # 4. Idempotency handler — duplicate task_id
    # -----------------------------------------------------------------

    @patch(
        "purplex.problems_app.services.progress_service.ProgressService.process_submission"
    )
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_duplicate_task_id_returns_cached_result(
        self, mock_publish, mock_progress, mcq_setup
    ):
        """
        When a Celery task retries with the same task_id, the idempotency
        handler should detect the duplicate and return the existing submission
        without creating a new one.
        """
        # First run — creates submission
        result1 = self._run_mcq(mcq_setup, "b", "tx-idempotent-test")
        result1.get()

        submission = Submission.objects.get(celery_task_id="tx-idempotent-test")
        original_id = submission.submission_id

        # Second run — same task_id, should hit idempotency handler
        result2 = self._run_mcq(mcq_setup, "b", "tx-idempotent-test")
        cached = result2.get()

        # Should still be exactly one submission
        assert Submission.objects.filter(
            celery_task_id="tx-idempotent-test"
        ).count() == 1
        # Returned result should reference the original
        assert cached["submission_id"] == str(original_id)

    # -----------------------------------------------------------------
    # 5. ProgressService receives committed submission
    # -----------------------------------------------------------------

    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_progress_called_with_committed_submission(
        self, mock_publish, mcq_setup
    ):
        """
        ProgressService.process_submission must be called with a submission
        that already exists in the DB (i.e., the transaction has committed).
        We verify this by checking the submission is queryable from inside
        the mock.
        """
        captured = []

        def capture_submission(submission):
            # Verify submission is actually in the DB at call time
            exists = Submission.objects.filter(pk=submission.pk).exists()
            captured.append({"pk": submission.pk, "exists_in_db": exists})

        with patch(
            "purplex.problems_app.services.progress_service.ProgressService.process_submission",
            side_effect=capture_submission,
        ):
            result = self._run_mcq(mcq_setup, "b", "tx-committed-check")
            result.get()

        assert len(captured) == 1
        assert captured[0]["exists_in_db"] is True, (
            "ProgressService was called before the transaction committed"
        )

    # -----------------------------------------------------------------
    # 6. ProgressService called exactly once on success
    # -----------------------------------------------------------------

    @patch(
        "purplex.problems_app.services.progress_service.ProgressService.process_submission"
    )
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_progress_called_once_on_success(
        self, mock_publish, mock_progress, mcq_setup
    ):
        """ProgressService should be called exactly once per successful MCQ submission."""
        result = self._run_mcq(mcq_setup, "a", "tx-called-once")
        result.get()

        assert mock_progress.call_count == 1

    # -----------------------------------------------------------------
    # 7. ProgressService NOT called on idempotent retry
    # -----------------------------------------------------------------

    @patch(
        "purplex.problems_app.services.progress_service.ProgressService.process_submission"
    )
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_progress_not_called_on_idempotent_retry(
        self, mock_publish, mock_progress, mcq_setup
    ):
        """
        On a duplicate task_id (idempotent retry), ProgressService should
        NOT be called again — the early return from the idempotency handler
        skips it.
        """
        # First run
        result1 = self._run_mcq(mcq_setup, "b", "tx-no-double-progress")
        result1.get()
        assert mock_progress.call_count == 1

        # Second run (retry with same task_id)
        result2 = self._run_mcq(mcq_setup, "b", "tx-no-double-progress")
        result2.get()

        # Still only 1 call — the retry hit the idempotency handler
        assert mock_progress.call_count == 1

    # -----------------------------------------------------------------
    # 8. Idempotency handler does NOT eat unrelated IntegrityErrors
    # -----------------------------------------------------------------

    @patch(
        "purplex.problems_app.services.progress_service.ProgressService.process_submission"
    )
    @patch("purplex.problems_app.tasks.pipeline.publish_progress")
    def test_non_task_id_integrity_error_reraises(
        self, mock_publish, mock_progress, mcq_setup
    ):
        """
        If an IntegrityError occurs during submission creation that is NOT
        a celery_task_id uniqueness violation, it should be re-raised, not
        swallowed by the idempotency handler.
        """
        with patch(
            "purplex.submissions.services.SubmissionService.create_submission",
            side_effect=IntegrityError("some_other_constraint violated"),
        ):
            result = self._run_mcq(
                mcq_setup, "b", "tx-non-taskid-error", throw=False
            )

        assert result.state == "FAILURE"
        with pytest.raises(IntegrityError, match="some_other_constraint"):
            result.get()
