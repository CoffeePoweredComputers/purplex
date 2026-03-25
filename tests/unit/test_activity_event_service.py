"""
Unit tests for ActivityEventService.
"""

import pytest

from purplex.submissions.activity_event_service import ActivityEventService
from purplex.submissions.models import ActivityEvent
from tests.factories import CourseFactory, EiplProblemFactory, UserFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


class TestActivityEventServiceRecord:
    """Tests for ActivityEventService.record()."""

    def test_record_creates_event(self):
        """record() creates an ActivityEvent with all fields populated."""
        user = UserFactory()
        event = ActivityEventService.record(
            user=user,
            event_type="probe.execute",
            payload={"input": "foo(1)", "output": "2"},
        )

        assert event.pk is not None
        assert event.user == user
        assert event.event_type == "probe.execute"
        assert event.payload == {"input": "foo(1)", "output": "2"}
        assert event.timestamp is not None

    def test_record_populates_anonymous_user_id(self):
        """record() sets anonymous_user_id via AnonymizationService."""
        user = UserFactory()
        event = ActivityEventService.record(user=user, event_type="hint.view")

        assert event.anonymous_user_id != ""
        assert len(event.anonymous_user_id) == 16

    def test_record_validates_event_type_format(self):
        """record() rejects event types not matching prefix.action format."""
        user = UserFactory()

        with pytest.raises(ValueError, match="dot-separated"):
            ActivityEventService.record(user=user, event_type="noDot")

        with pytest.raises(ValueError, match="dot-separated"):
            ActivityEventService.record(user=user, event_type="too.many.dots")

        with pytest.raises(ValueError, match="dot-separated"):
            ActivityEventService.record(user=user, event_type="UPPER.case")

    def test_record_rejects_unknown_prefix(self):
        """record() rejects event types with unregistered prefixes."""
        user = UserFactory()
        with pytest.raises(ValueError):
            ActivityEventService.record(user=user, event_type="foo.bar")

    def test_record_idempotency_key_deduplication(self):
        """Duplicate idempotency_key returns existing event."""
        user = UserFactory()
        event1 = ActivityEventService.record(
            user=user,
            event_type="probe.execute",
            idempotency_key="unique-key-123",
        )
        event2 = ActivityEventService.record(
            user=user,
            event_type="probe.execute",
            idempotency_key="unique-key-123",
        )

        assert event1.pk == event2.pk
        assert (
            ActivityEvent.objects.filter(idempotency_key="unique-key-123").count() == 1
        )

    def test_record_sets_schema_version(self):
        """record() sets schema_version (defaults to 1)."""
        user = UserFactory()

        event_default = ActivityEventService.record(user=user, event_type="hint.view")
        assert event_default.schema_version == 1

        event_v2 = ActivityEventService.record(
            user=user, event_type="hint.view", schema_version=2
        )
        assert event_v2.schema_version == 2

    def test_record_with_problem_and_course(self):
        """record() accepts optional problem and course FKs."""
        user = UserFactory()
        problem = EiplProblemFactory()
        course = CourseFactory()

        event = ActivityEventService.record(
            user=user,
            event_type="probe.execute",
            problem=problem,
            course=course,
        )

        assert event.problem == problem
        assert event.course == course

    def test_record_without_user(self):
        """record() handles None user gracefully (system events)."""
        event = ActivityEventService.record(user=None, event_type="session.start")

        assert event.pk is not None
        assert event.user is None
        assert event.anonymous_user_id == ""

    def test_record_default_payload_is_empty_dict(self):
        """record() defaults payload to empty dict when not provided."""
        user = UserFactory()
        event = ActivityEventService.record(user=user, event_type="session.start")
        assert event.payload == {}
