"""
Unit tests for Redis progress publishing functions.

These tests verify that the pipeline correctly publishes progress updates
to Redis channels for real-time frontend feedback.

The Redis publishing is non-critical (pipeline works even if Redis fails),
but it's important for user experience.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import redis

pytestmark = pytest.mark.unit


class TestPublishToRedis:
    """Tests for the internal _publish_to_redis helper function."""

    def test_publish_success(self):
        """_publish_to_redis returns True on successful publish."""
        from purplex.problems_app.tasks.pipeline import _publish_to_redis

        mock_client = MagicMock()

        with patch(
            "purplex.problems_app.tasks.pipeline.get_pubsub_client",
            return_value=mock_client,
        ):
            result = _publish_to_redis(
                channel="task:test-123",
                event_data={"type": "update", "progress": 0.5},
                event_type="progress",
            )

        assert result is True
        mock_client.publish.assert_called_once()
        # Verify channel name
        call_args = mock_client.publish.call_args
        assert call_args[0][0] == "task:test-123"
        # Verify JSON payload
        payload = json.loads(call_args[0][1])
        assert payload["type"] == "update"
        assert payload["progress"] == 0.5

    def test_publish_retries_on_connection_error(self):
        """_publish_to_redis retries on transient connection errors."""
        from purplex.problems_app.tasks.pipeline import _publish_to_redis

        mock_client = MagicMock()
        # First call fails, second succeeds
        mock_client.publish.side_effect = [
            redis.ConnectionError("Connection refused"),
            None,  # Success on retry
        ]

        with patch(
            "purplex.problems_app.tasks.pipeline.get_pubsub_client",
            return_value=mock_client,
        ):
            with patch("time.sleep"):  # Don't actually sleep in tests
                result = _publish_to_redis(
                    channel="task:test-123",
                    event_data={"type": "update"},
                    event_type="progress",
                )

        assert result is True
        assert mock_client.publish.call_count == 2

    def test_publish_returns_false_after_max_retries(self):
        """_publish_to_redis returns False after exhausting retries."""
        from purplex.problems_app.tasks.pipeline import _publish_to_redis

        mock_client = MagicMock()
        mock_client.publish.side_effect = redis.ConnectionError("Connection refused")

        with patch(
            "purplex.problems_app.tasks.pipeline.get_pubsub_client",
            return_value=mock_client,
        ):
            with patch("time.sleep"):  # Don't actually sleep
                result = _publish_to_redis(
                    channel="task:test-123",
                    event_data={"type": "update"},
                    event_type="progress",
                    max_retries=3,
                )

        assert result is False
        assert mock_client.publish.call_count == 3

    def test_publish_handles_timeout_error(self):
        """_publish_to_redis handles Redis timeout errors."""
        from purplex.problems_app.tasks.pipeline import _publish_to_redis

        mock_client = MagicMock()
        mock_client.publish.side_effect = redis.TimeoutError("Read timeout")

        with patch(
            "purplex.problems_app.tasks.pipeline.get_pubsub_client",
            return_value=mock_client,
        ):
            with patch("time.sleep"):
                result = _publish_to_redis(
                    channel="task:test-123",
                    event_data={"type": "update"},
                    event_type="progress",
                    max_retries=1,
                )

        assert result is False

    def test_publish_handles_unexpected_error(self):
        """_publish_to_redis handles unexpected errors without retry."""
        from purplex.problems_app.tasks.pipeline import _publish_to_redis

        mock_client = MagicMock()
        mock_client.publish.side_effect = Exception("Unexpected error")

        with patch(
            "purplex.problems_app.tasks.pipeline.get_pubsub_client",
            return_value=mock_client,
        ):
            result = _publish_to_redis(
                channel="task:test-123",
                event_data={"type": "update"},
                event_type="progress",
            )

        assert result is False
        # Should not retry on unexpected errors
        assert mock_client.publish.call_count == 1


class TestPublishProgress:
    """Tests for the publish_progress function."""

    def test_publish_progress_format(self):
        """publish_progress sends correctly formatted progress event."""
        from purplex.problems_app.tasks.pipeline import publish_progress

        with patch(
            "purplex.problems_app.tasks.pipeline._publish_to_redis"
        ) as mock_publish:
            mock_publish.return_value = True

            publish_progress(
                task_id="task-123",
                progress=50,
                message="Processing...",
            )

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args

            # Verify channel
            assert call_args[0][0] == "task:task-123"

            # Verify event structure
            event_data = call_args[0][1]
            assert event_data["type"] == "update"
            assert event_data["status"] == "processing"
            assert event_data["progress"] == 0.5  # 50/100 = 0.5
            assert event_data["message"] == "Processing..."
            assert "timestamp" in event_data

    def test_publish_progress_with_extra_data(self):
        """publish_progress includes extra_data in event."""
        from purplex.problems_app.tasks.pipeline import publish_progress

        with patch(
            "purplex.problems_app.tasks.pipeline._publish_to_redis"
        ) as mock_publish:
            mock_publish.return_value = True

            publish_progress(
                task_id="task-123",
                progress=75,
                message="Testing variations...",
                extra_data={"variation_count": 3, "current": 2},
            )

            event_data = mock_publish.call_args[0][1]
            assert event_data["variation_count"] == 3
            assert event_data["current"] == 2


class TestPublishCompletion:
    """Tests for the publish_completion function."""

    def test_publish_completion_format(self):
        """publish_completion sends correctly formatted completion event."""
        from purplex.problems_app.tasks.pipeline import publish_completion

        result = {
            "submission_id": "abc-123",
            "score": 100,
            "is_correct": True,
        }

        with patch(
            "purplex.problems_app.tasks.pipeline._publish_to_redis"
        ) as mock_publish:
            mock_publish.return_value = True

            publish_completion(task_id="task-456", result=result)

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args

            # Verify channel
            assert call_args[0][0] == "task:task-456"

            # Verify event structure
            event_data = call_args[0][1]
            assert event_data["type"] == "completed"
            assert event_data["status"] == "completed"
            assert "Score: 100%" in event_data["message"]
            assert event_data["result"] == result
            assert "timestamp" in event_data


class TestPublishError:
    """Tests for the publish_error function."""

    def test_publish_error_format(self):
        """publish_error sends correctly formatted error event."""
        from purplex.problems_app.tasks.pipeline import publish_error

        with patch(
            "purplex.problems_app.tasks.pipeline._publish_to_redis"
        ) as mock_publish:
            mock_publish.return_value = True

            publish_error(task_id="task-789", error_message="AI generation failed")

            mock_publish.assert_called_once()
            call_args = mock_publish.call_args

            # Verify channel
            assert call_args[0][0] == "task:task-789"

            # Verify event structure
            event_data = call_args[0][1]
            assert event_data["type"] == "failed"
            assert event_data["status"] == "failed"
            assert event_data["error"] == "AI generation failed"
            assert "Task failed:" in event_data["message"]
            assert "timestamp" in event_data


class TestProgressPublishingInPipeline:
    """Integration tests for progress publishing within pipeline context."""

    def test_progress_sequence_follows_expected_pattern(self):
        """Verify progress values increase monotonically in typical pipeline."""
        from purplex.problems_app.tasks.pipeline import publish_progress

        # Test that progress can be called with increasing values
        # This validates the API contract, not the actual pipeline calls
        progress_values = [0, 20, 50, 80, 95, 100]

        with patch(
            "purplex.problems_app.tasks.pipeline._publish_to_redis"
        ) as mock_publish:
            mock_publish.return_value = True

            for progress in progress_values:
                publish_progress("task-1", progress, f"Progress at {progress}%")

            # All calls should have been made
            assert mock_publish.call_count == len(progress_values)

            # Verify progress values in calls (position 0=channel, 1=event_data)
            for i, call in enumerate(mock_publish.call_args_list):
                event_data = call[0][1]
                expected_progress = progress_values[i] / 100.0
                assert event_data["progress"] == expected_progress

    def test_redis_failure_does_not_break_pipeline(self):
        """Pipeline should complete even if Redis publishing fails."""
        from purplex.problems_app.tasks.pipeline import publish_progress

        # Simulate Redis being unavailable
        with patch(
            "purplex.problems_app.tasks.pipeline._publish_to_redis",
            return_value=False,  # Publishing fails
        ):
            # These should not raise, just log and continue
            publish_progress("task-1", 50, "Processing...")
            # No exception raised means success

        # Pipeline logic would continue after failed publish


class TestBuildCompletionResult:
    """Tests for the build_completion_result helper."""

    @pytest.mark.django_db
    def test_build_completion_result_structure(self):
        """build_completion_result creates unified envelope structure."""
        from purplex.problems_app.handlers import get_handler
        from purplex.problems_app.tasks.pipeline import build_completion_result
        from purplex.submissions.models import Submission
        from tests.factories import (
            EiplProblemFactory,
            ProblemSetFactory,
            UserFactory,
            UserProfileFactory,
        )

        user = UserFactory()
        UserProfileFactory(user=user)
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()

        submission = Submission.objects.create(
            user=user,
            problem=problem,
            problem_set=problem_set,
            raw_input="Test prompt",
            submission_type="eipl",
            score=100,
            execution_status="completed",
        )

        handler = get_handler("eipl")

        result = build_completion_result(
            submission=submission,
            handler=handler,
            user_input="Test prompt",
            legacy_fields={"variations": ["def foo(): pass"]},
        )

        # Verify envelope structure
        assert result["submission_id"] == str(submission.submission_id)
        assert result["problem_type"] == "eipl"
        assert result["score"] == 100
        assert result["user_input"] == "Test prompt"
        assert "result" in result  # Handler-specific payload
        assert result["variations"] == ["def foo(): pass"]  # Legacy field merged
