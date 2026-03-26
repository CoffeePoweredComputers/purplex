"""
Integration tests for the ActivityEvent frontend API endpoint.

Tests full HTTP flow including FK resolution, consent gating,
and research export integration.
"""

import json

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from purplex.submissions.models import ActivityEvent
from purplex.users_app.models import ConsentType
from tests.factories import (
    CourseFactory,
    EiplProblemFactory,
    UserConsentFactory,
    UserFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def user_client():
    """Authenticated API client with a regular user."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def admin_client():
    """Authenticated API client with admin privileges."""
    user = UserFactory(is_staff=True, is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


class TestActivityEventEndpointIntegration:
    """Full-flow integration tests for the activity event API."""

    def test_full_flow_hint_track(self, user_client):
        """Complete hint.track flow with FK resolution and payload."""
        client, user = user_client
        problem = EiplProblemFactory()
        course = CourseFactory()

        url = reverse("activity_event_create")
        response = client.post(
            url,
            {
                "event_type": "hint.track",
                "payload": {
                    "hint_type": "structural",
                    "attempt_number": 3,
                    "first_hint_time": "2026-03-25T10:00:00Z",
                    "hints_used_count": 2,
                },
                "problem_slug": problem.slug,
                "course_id": course.course_id,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify event in DB
        event = ActivityEvent.objects.get(id=response.data["id"])
        assert event.user == user
        assert event.event_type == "hint.track"
        assert event.problem == problem
        assert event.course == course
        assert event.payload["hint_type"] == "structural"
        assert event.payload["attempt_number"] == 3
        assert event.anonymous_user_id  # pre-computed at write time

    def test_full_flow_session_with_consent(self, user_client):
        """Session events work end-to-end with consent."""
        client, user = user_client
        UserConsentFactory(
            user=user, consent_type=ConsentType.BEHAVIORAL_TRACKING, granted=True
        )

        url = reverse("activity_event_create")

        # Session start
        r1 = client.post(
            url,
            {"event_type": "session.start", "payload": {"page": "/problems/two-sum"}},
            format="json",
        )
        assert r1.status_code == status.HTTP_201_CREATED

        # Session end
        r2 = client.post(
            url,
            {"event_type": "session.end", "payload": {"page": "/problems/two-sum"}},
            format="json",
        )
        assert r2.status_code == status.HTTP_201_CREATED

        # Verify both events exist
        events = ActivityEvent.objects.filter(user=user).order_by("timestamp")
        assert events.count() == 2
        assert events[0].event_type == "session.start"
        assert events[1].event_type == "session.end"

    def test_event_appears_in_research_export(self, admin_client):
        """Frontend-recorded events appear in the research export."""
        client, user = admin_client

        # Record an event via the API
        url = reverse("activity_event_create")
        client.post(
            url,
            {
                "event_type": "hint.track",
                "payload": {"hint_type": "edge_case"},
            },
            format="json",
        )

        # Fetch research export
        export_url = reverse("research_export")
        response = client.get(export_url)
        assert response.status_code == status.HTTP_200_OK

        data = json.loads(response.content)
        assert "activity_events" in data

        # Find our event
        hint_tracks = [
            e for e in data["activity_events"] if e["event_type"] == "hint.track"
        ]
        assert len(hint_tracks) == 1
        assert hint_tracks[0]["payload"]["hint_type"] == "edge_case"
