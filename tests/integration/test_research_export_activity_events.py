"""
Integration tests for ActivityEvent export via the research API endpoint.
"""

import json

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import ActivityEventFactory, UserFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def admin_client():
    """Authenticated API client with admin privileges."""
    user = UserFactory(is_staff=True, is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class TestResearchExportEndpointActivityEvents:
    """Test activity events via the /api/research/export/ endpoint."""

    def test_export_endpoint_includes_activity_events(self, admin_client):
        """Research export response includes activity_events key."""
        ActivityEventFactory(event_type="probe.execute")
        ActivityEventFactory(event_type="hint.view")

        url = reverse("research_export")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = json.loads(response.content)
        assert "activity_events" in data
        assert len(data["activity_events"]) == 2

    def test_export_endpoint_event_type_filter(self, admin_client):
        """event_types query param filters activity events."""
        ActivityEventFactory(event_type="probe.execute")
        ActivityEventFactory(event_type="hint.view")
        ActivityEventFactory(event_type="refute.attempt")

        url = reverse("research_export")
        response = admin_client.get(url, {"event_types": "probe.execute"})

        data = json.loads(response.content)
        assert len(data["activity_events"]) == 1
        assert data["activity_events"][0]["event_type"] == "probe.execute"

    def test_export_endpoint_multiple_event_types(self, admin_client):
        """Comma-separated event_types filters multiple types."""
        ActivityEventFactory(event_type="probe.execute")
        ActivityEventFactory(event_type="hint.view")
        ActivityEventFactory(event_type="refute.attempt")

        url = reverse("research_export")
        response = admin_client.get(url, {"event_types": "probe.execute,hint.view"})

        data = json.loads(response.content)
        assert len(data["activity_events"]) == 2

    def test_export_endpoint_requires_admin(self):
        """Non-admin users get 403."""
        regular_user = UserFactory()
        client = APIClient()
        client.force_authenticate(user=regular_user)

        url = reverse("research_export")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
