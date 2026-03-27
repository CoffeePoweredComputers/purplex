"""
Tests for ActivityEvent immutability enforcement.

Verifies both Python-level guards (save/delete overrides) and
database-level trigger protection against mutation.
"""

import pytest
from django.db import connection, transaction
from django.db.utils import IntegrityError

from purplex.submissions.models import ActivityEvent
from tests.factories import (
    ActivityEventFactory,
    CourseFactory,
    EiplProblemFactory,
    UserFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


# ─────────────────────────────────────────────────────────────────────────────
# Python-level guards
# ─────────────────────────────────────────────────────────────────────────────


class TestActivityEventPythonGuards:
    """Python save()/delete() overrides prevent ORM-level mutation."""

    def test_save_existing_raises_value_error(self):
        """Cannot modify an existing event via save()."""
        event = ActivityEventFactory()
        event.event_type = "hint.view"
        with pytest.raises(ValueError, match="immutable"):
            event.save()

    def test_delete_raises_value_error(self):
        """Cannot delete an event via the ORM delete() method."""
        event = ActivityEventFactory()
        with pytest.raises(ValueError, match="cannot be deleted"):
            event.delete()

    def test_new_record_creation_succeeds(self):
        """Creating a new event works normally."""
        event = ActivityEventFactory()
        assert event.pk is not None
        assert ActivityEvent.objects.filter(pk=event.pk).exists()

    def test_bulk_create_succeeds(self):
        """bulk_create bypasses save() but should work for new records."""
        user = UserFactory()
        events = [
            ActivityEvent(
                user=user,
                event_type="probe.execute",
                payload={"n": i},
                anonymous_user_id="abc123",
            )
            for i in range(3)
        ]
        created = ActivityEvent.objects.bulk_create(events)
        assert len(created) == 3


# ─────────────────────────────────────────────────────────────────────────────
# Database-level trigger
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.usefixtures("_activityevent_immutability_trigger")
class TestActivityEventTrigger:
    """PostgreSQL trigger blocks mutations that bypass Python guards."""

    def test_queryset_update_blocked(self):
        """QuerySet.update() is blocked by the trigger."""
        event = ActivityEventFactory()
        with pytest.raises(IntegrityError, match="activityevent_immutable"):
            with transaction.atomic():
                ActivityEvent.objects.filter(pk=event.pk).update(event_type="hint.view")

    def test_queryset_delete_blocked(self):
        """QuerySet.delete() is blocked by the trigger."""
        event = ActivityEventFactory()
        with pytest.raises(IntegrityError, match="activityevent_immutable"):
            with transaction.atomic():
                ActivityEvent.objects.filter(pk=event.pk).delete()

    def test_raw_sql_update_blocked(self):
        """Raw SQL UPDATE is blocked by the trigger."""
        event = ActivityEventFactory()
        with pytest.raises(IntegrityError, match="activityevent_immutable"):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE submissions_activityevent SET event_type = 'hacked' WHERE id = %s",
                        [event.pk],
                    )

    def test_raw_sql_delete_blocked(self):
        """Raw SQL DELETE is blocked by the trigger."""
        event = ActivityEventFactory()
        with pytest.raises(IntegrityError, match="activityevent_immutable"):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM submissions_activityevent WHERE id = %s",
                        [event.pk],
                    )

    def test_set_null_user_id_allowed(self):
        """SET_NULL on user_id is allowed (user deletion path)."""
        user = UserFactory()
        event = ActivityEventFactory(user=user)
        event_id = event.id

        # Simulate Django's on_delete=SET_NULL
        ActivityEvent.objects.filter(pk=event_id).update(user=None)

        event.refresh_from_db()
        assert event.user is None

    def test_set_null_problem_id_allowed(self):
        """SET_NULL on problem_id is allowed (problem deletion path)."""
        problem = EiplProblemFactory()
        event = ActivityEventFactory(problem=problem)
        event_id = event.id

        ActivityEvent.objects.filter(pk=event_id).update(problem=None)

        event.refresh_from_db()
        assert event.problem is None

    def test_set_null_course_id_allowed(self):
        """SET_NULL on course_id is allowed (course deletion path)."""
        course = CourseFactory()
        event = ActivityEventFactory(course=course)
        event_id = event.id

        ActivityEvent.objects.filter(pk=event_id).update(course=None)

        event.refresh_from_db()
        assert event.course is None

    def test_set_null_plus_data_mutation_blocked(self):
        """SET_NULL combined with a data change is blocked."""
        user = UserFactory()
        event = ActivityEventFactory(user=user)
        with pytest.raises(IntegrityError, match="activityevent_immutable"):
            with transaction.atomic():
                ActivityEvent.objects.filter(pk=event.pk).update(
                    user=None, event_type="tampered"
                )

    def test_reassign_user_fk_blocked(self):
        """Changing user FK to a different user (not NULL) is blocked."""
        user1 = UserFactory()
        user2 = UserFactory()
        event = ActivityEventFactory(user=user1)
        with pytest.raises(IntegrityError, match="activityevent_immutable"):
            with transaction.atomic():
                ActivityEvent.objects.filter(pk=event.pk).update(user=user2)
