"""
Service for recording activity events.

All user-facing event recording flows through this service, which handles
anonymization, validation, and idempotency.
"""

import logging
import re
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction

from purplex.utils.anonymization import AnonymizationService

from .models import ActivityEvent

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from purplex.problems_app.models import Course, Problem

logger = logging.getLogger(__name__)

# Dot-separated namespace: prefix.action
_EVENT_TYPE_RE = re.compile(r"^[a-z_]+\.[a-z_]+$")
_VALID_PREFIXES = frozenset({"probe", "hint", "refute", "session"})


class ActivityEventService:
    """
    Central service for recording activity events.

    All methods are classmethods — no instance state.
    """

    @classmethod
    def _validate_event_type(cls, event_type: str) -> None:
        """Validate event_type matches dot-separated namespace convention."""
        if not _EVENT_TYPE_RE.match(event_type):
            raise ValueError(
                "event_type must be dot-separated lowercase: "
                f"'prefix.action', got '{event_type}'"
            )
        prefix = event_type.split(".")[0]
        if prefix not in _VALID_PREFIXES:
            raise ValueError(
                "event_type prefix must be one of %s, got '%s'",
                _VALID_PREFIXES,
                prefix,
            )

    @classmethod
    def _prepare_event(
        cls,
        user: "User | None",
        event_type: str,
        payload: dict | None = None,
        problem: "Problem | None" = None,
        course: "Course | None" = None,
        schema_version: int = 1,
        idempotency_key: str | None = None,
    ) -> ActivityEvent:
        """Build an ActivityEvent instance without saving.

        Populates anonymous_user_id via AnonymizationService at write time.
        Validates event_type format.
        """
        cls._validate_event_type(event_type)

        anonymous_user_id = ""
        if user is not None:
            anonymous_user_id = AnonymizationService.anonymize_user_id(user)

        return ActivityEvent(
            user=user,
            event_type=event_type,
            payload=payload or {},
            problem=problem,
            course=course,
            anonymous_user_id=anonymous_user_id,
            schema_version=schema_version,
            idempotency_key=idempotency_key or None,
        )

    @classmethod
    def record(
        cls,
        user: "User | None",
        event_type: str,
        payload: dict | None = None,
        problem: "Problem | None" = None,
        course: "Course | None" = None,
        schema_version: int = 1,
        idempotency_key: str | None = None,
    ) -> ActivityEvent:
        """Record a single activity event.

        Idempotent if idempotency_key is provided — a duplicate key returns
        the existing record instead of creating a new one.

        Args:
            user: The user performing the action (None for system events).
            event_type: Dot-separated namespace (e.g., "probe.execute").
            payload: Event-specific data dict.
            problem: Optional related problem.
            course: Optional related course.
            schema_version: Payload schema version (default 1).
            idempotency_key: Optional deduplication key.

        Returns:
            The created (or existing, if deduplicated) ActivityEvent.

        Raises:
            ValueError: If event_type format is invalid.
        """
        event = cls._prepare_event(
            user=user,
            event_type=event_type,
            payload=payload,
            problem=problem,
            course=course,
            schema_version=schema_version,
            idempotency_key=idempotency_key,
        )

        try:
            with transaction.atomic():
                event.save()
        except IntegrityError:
            if idempotency_key:
                existing = ActivityEvent.objects.get(idempotency_key=idempotency_key)
                logger.info(
                    "Duplicate idempotency_key %s, returning existing event %s",
                    idempotency_key,
                    existing.id,
                )
                return existing
            raise

        logger.info(
            "Recorded %s event for user %s (problem=%s, course=%s)",
            event_type,
            user.id if user else None,
            problem.id if problem else None,
            course.id if course else None,
        )
        return event
