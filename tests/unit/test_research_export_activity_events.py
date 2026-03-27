"""
Unit tests for ActivityEvent export in ResearchExportService.

Tests filtering (course, date range, event_type), anonymization,
null FK handling, and integration with the full export dataset.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from purplex.problems_app.services.research_export_service import (
    ResearchExportService,
)
from purplex.submissions.models import ActivityEvent
from tests.factories import (
    ActivityEventFactory,
    CourseFactory,
    EiplProblemFactory,
    UserFactory,
)


def _create_event_at(timestamp, **kwargs):
    """Create an ActivityEvent with a specific timestamp.

    auto_now_add prevents setting timestamp at creation time,
    so we temporarily disable it for the insert.
    """
    field = ActivityEvent._meta.get_field("timestamp")
    field.auto_now_add = False
    try:
        event = ActivityEventFactory(timestamp=timestamp, **kwargs)
    finally:
        field.auto_now_add = True
    return event


pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# ─────────────────────────────────────────────────────────────────────────────
# Basic export
# ─────────────────────────────────────────────────────────────────────────────


class TestExportActivityEventsBasic:
    """Core export functionality."""

    def test_export_single_event(self):
        """Single event exports with all expected fields."""
        ActivityEventFactory(
            event_type="probe.execute",
            payload={"input": {"x": 1}, "output": 2},
        )

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert len(result) == 1
        exported = result[0]
        assert exported["event_type"] == "probe.execute"
        assert exported["payload"] == {"input": {"x": 1}, "output": 2}
        assert exported["schema_version"] == 1
        assert "user_id" in exported
        assert "timestamp" in exported
        assert "problem_slug" in exported
        assert "course_id" in exported

    def test_export_multiple_event_types(self):
        """Multiple event types all appear in export."""
        user = UserFactory()
        ActivityEventFactory(user=user, event_type="probe.execute")
        ActivityEventFactory(user=user, event_type="hint.view")
        ActivityEventFactory(user=user, event_type="refute.attempt")

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert len(result) == 3
        types = {e["event_type"] for e in result}
        assert types == {"probe.execute", "hint.view", "refute.attempt"}

    def test_export_preserves_payload(self):
        """Payload dict is exported as-is, not modified."""
        payload = {"input": {"x": -5}, "claim_disproven": True, "nested": {"a": [1, 2]}}
        ActivityEventFactory(event_type="refute.attempt", payload=payload)

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert result[0]["payload"] == payload

    def test_export_empty_result(self):
        """No events returns empty list."""
        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# Anonymization
# ─────────────────────────────────────────────────────────────────────────────


class TestExportActivityEventsAnonymization:
    """Anonymization uses pre-computed anonymous_user_id."""

    def test_anonymized_export_uses_stored_anonymous_id(self):
        """Anonymized export uses the pre-computed anonymous_user_id field."""
        event = ActivityEventFactory()

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert result[0]["user_id"] == event.anonymous_user_id
        assert len(result[0]["user_id"]) == 16  # SHA-256 first 16 chars

    def test_non_anonymized_export_uses_username(self):
        """Non-anonymized export uses the username."""
        user = UserFactory()
        ActivityEventFactory(user=user)

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=False,
        )

        assert result[0]["user_id"] == user.username

    def test_deleted_user_anonymized_export(self):
        """Deleted user (NULL FK) still exports with anonymous_user_id."""
        user = UserFactory()
        event = ActivityEventFactory(user=user)
        original_anon_id = event.anonymous_user_id

        # Simulate user deletion (SET_NULL)
        user.delete()

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert result[0]["user_id"] == original_anon_id

    def test_deleted_user_non_anonymized_export(self):
        """Deleted user falls back to anonymous_user_id when not anonymized."""
        user = UserFactory()
        event = ActivityEventFactory(user=user)
        original_anon_id = event.anonymous_user_id

        user.delete()

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=False,
        )

        # Falls back to anonymous_user_id since user is deleted
        assert result[0]["user_id"] == original_anon_id


# ─────────────────────────────────────────────────────────────────────────────
# Filtering
# ─────────────────────────────────────────────────────────────────────────────


class TestExportActivityEventsFiltering:
    """Filtering by course, date range, and event type."""

    def test_filter_by_course(self):
        """Course filter returns only events for that course."""
        course_a = CourseFactory()
        course_b = CourseFactory()
        ActivityEventFactory(course=course_a)
        ActivityEventFactory(course=course_a)
        ActivityEventFactory(course=course_b)
        ActivityEventFactory(course=None)

        result = ResearchExportService._export_activity_events(
            course=course_a,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert len(result) == 2

    def test_filter_by_date_range(self):
        """Date range filter returns only events within range."""
        now = timezone.now()

        _create_event_at(now - timedelta(days=30))  # too old
        _create_event_at(now - timedelta(days=5))  # in range
        _create_event_at(now + timedelta(days=5))  # too new

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=now - timedelta(days=10),
            end_date=now,
            event_types=None,
            anonymize=True,
        )

        assert len(result) == 1

    def test_filter_by_event_types(self):
        """Event type filter returns only matching types."""
        ActivityEventFactory(event_type="probe.execute")
        ActivityEventFactory(event_type="hint.view")
        ActivityEventFactory(event_type="refute.attempt")

        # Single type
        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=["probe.execute"],
            anonymize=True,
        )
        assert len(result) == 1
        assert result[0]["event_type"] == "probe.execute"

        # Multiple types
        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=["probe.execute", "hint.view"],
            anonymize=True,
        )
        assert len(result) == 2

    def test_filter_combined_course_and_date(self):
        """Combined filters return correct intersection."""
        now = timezone.now()
        course = CourseFactory()

        # In course, in range — should match
        _create_event_at(now - timedelta(days=5), course=course)
        # In course, out of range — should NOT match
        _create_event_at(now - timedelta(days=60), course=course)
        # Different course, in range — should NOT match
        _create_event_at(now - timedelta(days=5), course=CourseFactory())

        result = ResearchExportService._export_activity_events(
            course=course,
            start_date=now - timedelta(days=10),
            end_date=now,
            event_types=None,
            anonymize=True,
        )

        assert len(result) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Null FKs
# ─────────────────────────────────────────────────────────────────────────────


class TestExportActivityEventsNullFKs:
    """Graceful handling of deleted related objects."""

    def test_deleted_problem_exports_null_slug(self):
        """Deleted problem (SET_NULL) exports as None slug."""
        problem = EiplProblemFactory()
        ActivityEventFactory(problem=problem)
        problem.delete()

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert result[0]["problem_slug"] is None

    def test_deleted_course_exports_null_id(self):
        """Deleted course (SET_NULL) exports as None course_id."""
        course = CourseFactory()
        ActivityEventFactory(course=course)
        course.delete()

        result = ResearchExportService._export_activity_events(
            course=None,
            start_date=None,
            end_date=None,
            event_types=None,
            anonymize=True,
        )

        assert result[0]["course_id"] is None


# ─────────────────────────────────────────────────────────────────────────────
# Full export integration
# ─────────────────────────────────────────────────────────────────────────────


class TestExportCompleteDatasetIncludesActivityEvents:
    """Activity events are included in the full research export."""

    def test_full_export_has_activity_events_key(self):
        """export_complete_dataset() includes activity_events section."""
        ActivityEventFactory(event_type="probe.execute")
        ActivityEventFactory(event_type="hint.view")

        dataset = ResearchExportService.export_complete_dataset()

        assert "activity_events" in dataset
        assert len(dataset["activity_events"]) == 2

    def test_metadata_includes_event_types_filter(self):
        """Metadata records the event_types filter when provided."""
        dataset = ResearchExportService.export_complete_dataset(
            event_types=["probe.execute"]
        )

        assert dataset["metadata"]["filters"]["event_types"] == ["probe.execute"]

    def test_metadata_event_types_none_when_unfiltered(self):
        """Metadata shows None for event_types when no filter applied."""
        dataset = ResearchExportService.export_complete_dataset()

        assert dataset["metadata"]["filters"]["event_types"] is None
