"""
Unit tests for ActivityEvent recording in views.

Verifies that probe, hint, and refute views record ActivityEvents
correctly, and that recording failures don't break the primary flow.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status

from purplex.submissions.models import ActivityEvent
from tests.factories import (
    EiplProblemFactory,
    ProbeableCodeProblemFactory,
    ProblemHintFactory,
    ProblemSetFactory,
    ProblemSetMembershipFactory,
    RefuteProblemFactory,
    UserFactory,
    UserProgressFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ─────────────────────────────────────────────────────────────────────────────
# Probe: probe.execute
# ─────────────────────────────────────────────────────────────────────────────


class TestProbeExecuteEventRecording:
    """Verify ProbeOracleView records probe.execute events."""

    @patch("purplex.problems_app.views.probe_views.ProbeService.execute_probe")
    def test_probe_records_activity_event(self, mock_execute, api_client):
        """Successful probe records an ActivityEvent."""
        user = UserFactory()
        problem = ProbeableCodeProblemFactory()
        mock_execute.return_value = {
            "success": True,
            "result": 42,
            "error": None,
            "probe_status": {"mode": "explore", "remaining": None, "used": 1},
        }

        api_client.force_authenticate(user=user)
        url = reverse("probe_oracle", kwargs={"slug": problem.slug})
        response = api_client.post(url, {"input": {"x": 5}}, format="json")

        assert response.status_code == status.HTTP_200_OK

        events = ActivityEvent.objects.filter(event_type="probe.execute")
        assert events.count() == 1

        event = events.first()
        assert event.user == user
        assert event.problem == problem
        assert event.payload["input"] == {"x": 5}
        assert event.payload["output"] == 42
        assert event.payload["success"] is True
        assert event.payload["probe_mode"] == "explore"

    @patch("purplex.problems_app.views.probe_views.ProbeService.execute_probe")
    def test_probe_records_event_on_limit_reached(self, mock_execute, api_client):
        """Limit-blocked probe still records an event with success=False."""
        user = UserFactory()
        problem = ProbeableCodeProblemFactory()
        mock_execute.return_value = {
            "success": False,
            "result": None,
            "error": "Probe limit reached",
            "probe_status": {"mode": "block", "remaining": 0, "used": 10},
        }

        api_client.force_authenticate(user=user)
        url = reverse("probe_oracle", kwargs={"slug": problem.slug})
        response = api_client.post(url, {"input": {"x": 1}}, format="json")

        assert response.status_code == status.HTTP_200_OK

        event = ActivityEvent.objects.filter(event_type="probe.execute").first()
        assert event is not None
        assert event.payload["success"] is False

    @patch("purplex.problems_app.views.probe_views.ProbeService.execute_probe")
    @patch(
        "purplex.submissions.activity_event_service.ActivityEventService.record",
        side_effect=RuntimeError("DB down"),
    )
    def test_probe_continues_on_recording_failure(
        self, mock_record, mock_execute, api_client
    ):
        """Probe still returns 200 if activity recording fails."""
        user = UserFactory()
        problem = ProbeableCodeProblemFactory()
        mock_execute.return_value = {
            "success": True,
            "result": 42,
            "error": None,
            "probe_status": {"mode": "explore", "remaining": None, "used": 1},
        }

        api_client.force_authenticate(user=user)
        url = reverse("probe_oracle", kwargs={"slug": problem.slug})
        response = api_client.post(url, {"input": {"x": 5}}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True
        assert ActivityEvent.objects.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# Hint: hint.view
# ─────────────────────────────────────────────────────────────────────────────


class TestHintViewEventRecording:
    """Verify ProblemHintDetailView records hint.view events."""

    def test_hint_view_records_activity_event(self, api_client):
        """Successful hint delivery records an ActivityEvent."""
        user = UserFactory()
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()
        ProblemSetMembershipFactory(problem=problem, problem_set=problem_set, order=1)
        ProblemHintFactory(
            problem=problem,
            hint_type="variable_fade",
            min_attempts=1,
            content={"mappings": [{"from": "x", "to": "count"}]},
        )
        UserProgressFactory(
            user=user,
            problem=problem,
            problem_set=problem_set,
            attempts=2,
        )

        api_client.force_authenticate(user=user)
        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem.slug, "hint_type": "variable_fade"},
        )
        response = api_client.get(url, {"problem_set_slug": problem_set.slug})

        assert response.status_code == status.HTTP_200_OK

        events = ActivityEvent.objects.filter(event_type="hint.view")
        assert events.count() == 1

        event = events.first()
        assert event.user == user
        assert event.payload["hint_type"] == "variable_fade"
        assert event.payload["problem_slug"] == problem.slug

    def test_hint_view_no_event_on_error(self, api_client):
        """Error responses don't record an ActivityEvent."""
        user = UserFactory()
        api_client.force_authenticate(user=user)
        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": "nonexistent", "hint_type": "variable_fade"},
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert ActivityEvent.objects.filter(event_type="hint.view").count() == 0

    @patch(
        "purplex.submissions.activity_event_service.ActivityEventService.record",
        side_effect=RuntimeError("DB down"),
    )
    def test_hint_view_continues_on_recording_failure(self, mock_record, api_client):
        """Hint is still delivered if activity recording fails."""
        user = UserFactory()
        problem = EiplProblemFactory()
        problem_set = ProblemSetFactory()
        ProblemSetMembershipFactory(problem=problem, problem_set=problem_set, order=1)
        ProblemHintFactory(
            problem=problem,
            hint_type="variable_fade",
            min_attempts=1,
            content={"mappings": []},
        )
        UserProgressFactory(
            user=user,
            problem=problem,
            problem_set=problem_set,
            attempts=2,
        )

        api_client.force_authenticate(user=user)
        url = reverse(
            "problem_hint_detail",
            kwargs={"slug": problem.slug, "hint_type": "variable_fade"},
        )
        response = api_client.get(url, {"problem_set_slug": problem_set.slug})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["type"] == "variable_fade"


# ─────────────────────────────────────────────────────────────────────────────
# Refute: refute.attempt
# ─────────────────────────────────────────────────────────────────────────────


class TestRefuteAttemptEventRecording:
    """Verify RefuteTestView records refute.attempt events."""

    @patch("purplex.problems_app.views.probe_views.get_handler")
    def test_refute_records_activity_event(self, mock_get_handler, api_client):
        """Successful refute test records an ActivityEvent."""
        user = UserFactory()
        problem = RefuteProblemFactory()
        mock_handler = MagicMock()
        mock_handler.test_counterexample.return_value = {
            "success": True,
            "result": -10,
            "claim_disproven": True,
            "error": None,
        }
        mock_get_handler.return_value = mock_handler

        api_client.force_authenticate(user=user)
        url = reverse("refute_test", kwargs={"slug": problem.slug})
        response = api_client.post(url, {"input": {"x": -5}}, format="json")

        assert response.status_code == status.HTTP_200_OK

        events = ActivityEvent.objects.filter(event_type="refute.attempt")
        assert events.count() == 1

        event = events.first()
        assert event.user == user
        assert event.problem == problem
        assert event.payload["input"] == {"x": -5}
        assert event.payload["claim_disproven"] is True

    @patch("purplex.problems_app.views.probe_views.get_handler")
    @patch(
        "purplex.submissions.activity_event_service.ActivityEventService.record",
        side_effect=RuntimeError("DB down"),
    )
    def test_refute_continues_on_recording_failure(
        self, mock_record, mock_get_handler, api_client
    ):
        """Refute test still returns 200 if activity recording fails."""
        user = UserFactory()
        problem = RefuteProblemFactory()
        mock_handler = MagicMock()
        mock_handler.test_counterexample.return_value = {
            "success": True,
            "result": -10,
            "claim_disproven": True,
            "error": None,
        }
        mock_get_handler.return_value = mock_handler

        api_client.force_authenticate(user=user)
        url = reverse("refute_test", kwargs={"slug": problem.slug})
        response = api_client.post(url, {"input": {"x": -5}}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["claim_disproven"] is True
        assert ActivityEvent.objects.count() == 0
