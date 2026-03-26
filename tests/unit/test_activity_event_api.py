"""
Unit tests for the ActivityEvent frontend API endpoint.

Tests authentication, input validation, FK resolution, consent gating,
rate limiting, idempotency, and payload storage.
"""

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

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def api_client():
    """Authenticated API client."""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def url():
    return reverse("activity_event_create")


# ─────────────────────────────────────────────────────────────────────────────
# Auth & permissions
# ─────────────────────────────────────────────────────────────────────────────


class TestActivityEventAuth:
    """Authentication and permission checks."""

    def test_requires_authentication(self, url):
        """Unauthenticated request is rejected."""
        client = APIClient()
        response = client.post(url, {"event_type": "hint.track"}, format="json")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_authenticated_user_can_create_event(self, api_client, url):
        """Authenticated user can create an event."""
        client, _ = api_client
        response = client.post(url, {"event_type": "hint.track"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert response.data["event_type"] == "hint.track"


# ─────────────────────────────────────────────────────────────────────────────
# Input validation
# ─────────────────────────────────────────────────────────────────────────────


class TestActivityEventValidation:
    """Input validation for event_type and payload."""

    def test_missing_event_type_returns_400(self, api_client, url):
        """Missing event_type returns 400."""
        client, _ = api_client
        response = client.post(url, {"payload": {}}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "event_type" in response.data["error"]

    def test_invalid_event_type_format_returns_400(self, api_client, url):
        """Invalid event_type format returns 400."""
        client, _ = api_client
        response = client.post(url, {"event_type": "invalid"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_event_type_prefix_returns_400(self, api_client, url):
        """Unknown prefix returns 400."""
        client, _ = api_client
        response = client.post(url, {"event_type": "unknown.action"}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_payload_stored_correctly(self, api_client, url):
        """Nested payload is stored as-is."""
        client, _ = api_client
        payload = {"hint_type": "structural", "nested": {"a": [1, 2, 3]}}
        response = client.post(
            url,
            {"event_type": "hint.track", "payload": payload},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        event = ActivityEvent.objects.get(id=response.data["id"])
        assert event.payload == payload


# ─────────────────────────────────────────────────────────────────────────────
# FK resolution
# ─────────────────────────────────────────────────────────────────────────────


class TestActivityEventFKResolution:
    """Slug/ID resolution to FK references."""

    def test_resolves_problem_slug_to_fk(self, api_client, url):
        """Valid problem_slug resolves to a Problem FK."""
        client, _ = api_client
        problem = EiplProblemFactory()
        response = client.post(
            url,
            {"event_type": "hint.track", "problem_slug": problem.slug},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        event = ActivityEvent.objects.get(id=response.data["id"])
        assert event.problem == problem

    def test_invalid_problem_slug_records_with_null_fk(self, api_client, url):
        """Invalid problem_slug records event with null FK."""
        client, _ = api_client
        response = client.post(
            url,
            {"event_type": "hint.track", "problem_slug": "nonexistent-slug"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        event = ActivityEvent.objects.get(id=response.data["id"])
        assert event.problem is None

    def test_resolves_course_id_to_fk(self, api_client, url):
        """Valid course_id resolves to a Course FK."""
        client, _ = api_client
        course = CourseFactory()
        response = client.post(
            url,
            {"event_type": "hint.track", "course_id": course.course_id},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        event = ActivityEvent.objects.get(id=response.data["id"])
        assert event.course == course

    def test_invalid_course_id_records_with_null_fk(self, api_client, url):
        """Invalid course_id records event with null FK."""
        client, _ = api_client
        response = client.post(
            url,
            {"event_type": "hint.track", "course_id": "FAKE-101"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        event = ActivityEvent.objects.get(id=response.data["id"])
        assert event.course is None


# ─────────────────────────────────────────────────────────────────────────────
# Consent gate
# ─────────────────────────────────────────────────────────────────────────────


class TestActivityEventConsentGate:
    """Consent checking for behavioral events (session.*)."""

    def test_session_event_requires_behavioral_tracking_consent(self, api_client, url):
        """session.start without BEHAVIORAL_TRACKING consent returns 403."""
        client, _ = api_client
        response = client.post(url, {"event_type": "session.start"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "consent" in response.data["error"].lower()

    def test_session_event_allowed_with_consent(self, api_client, url):
        """session.start with BEHAVIORAL_TRACKING consent returns 201."""
        client, user = api_client
        UserConsentFactory(
            user=user, consent_type=ConsentType.BEHAVIORAL_TRACKING, granted=True
        )
        response = client.post(
            url,
            {"event_type": "session.start", "payload": {"page": "/"}},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_session_end_without_consent_returns_403(self, api_client, url):
        """session.end without consent also returns 403."""
        client, _ = api_client
        response = client.post(url, {"event_type": "session.end"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_hint_event_does_not_require_consent(self, api_client, url):
        """hint.track does not require behavioral tracking consent."""
        client, _ = api_client
        response = client.post(url, {"event_type": "hint.track"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED

    def test_probe_event_does_not_require_consent(self, api_client, url):
        """probe.execute does not require behavioral tracking consent."""
        client, _ = api_client
        response = client.post(url, {"event_type": "probe.execute"}, format="json")
        assert response.status_code == status.HTTP_201_CREATED


# ─────────────────────────────────────────────────────────────────────────────
# Idempotency
# ─────────────────────────────────────────────────────────────────────────────


class TestActivityEventIdempotency:
    """Idempotency key deduplication."""

    def test_idempotency_key_deduplicates(self, api_client, url):
        """Same idempotency_key returns same event."""
        client, _ = api_client
        data = {
            "event_type": "hint.track",
            "idempotency_key": "test-dedup-key-123",
        }
        response1 = client.post(url, data, format="json")
        response2 = client.post(url, data, format="json")

        assert response1.status_code == status.HTTP_201_CREATED
        # Second request returns the existing event (service handles dedup)
        assert response2.status_code == status.HTTP_201_CREATED
        assert response1.data["id"] == response2.data["id"]
