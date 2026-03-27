"""
Repository for ActivityEvent data access.

All ORM operations on ActivityEvent are centralized here.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from django.db.models import QuerySet

from .models import ActivityEvent

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from purplex.problems_app.models import Course


class ActivityEventRepository:
    """Data access layer for ActivityEvent."""

    @classmethod
    def create(cls, event: ActivityEvent) -> ActivityEvent:
        """Persist a prepared (unsaved) ActivityEvent."""
        event.save()
        return event

    @classmethod
    def get_by_idempotency_key(cls, key: str) -> ActivityEvent:
        """Retrieve an event by its idempotency key."""
        return ActivityEvent.objects.get(idempotency_key=key)

    @classmethod
    def anonymize_for_user(cls, user: "User") -> int:
        """SET_NULL on user FK for all events belonging to user.

        Returns the number of events anonymized.
        """
        return ActivityEvent.objects.filter(user=user).update(user=None)

    @classmethod
    def get_for_user_export(cls, user: "User") -> QuerySet:
        """Get all events for a user (GDPR Art. 15 export)."""
        return (
            ActivityEvent.objects.filter(user=user)
            .select_related("problem", "course")
            .order_by("timestamp")
        )

    @classmethod
    def get_for_research_export(
        cls,
        course: "Course | None" = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        event_types: list[str] | None = None,
    ) -> QuerySet:
        """Get events for research export with optional filters."""
        queryset = ActivityEvent.objects.select_related("user", "problem", "course")

        if course:
            queryset = queryset.filter(course=course)
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)

        return queryset.order_by("timestamp")
