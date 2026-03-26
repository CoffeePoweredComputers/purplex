"""
Service for recording activity events.

All user-facing event recording flows through this service, which handles
anonymization, validation, consent gating, and idempotency.
"""

import logging
import re
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction

from purplex.utils.anonymization import AnonymizationService

from .activity_event_repository import ActivityEventRepository

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from purplex.problems_app.models import Course, Problem
    from purplex.submissions.models import ActivityEvent

logger = logging.getLogger(__name__)

# Dot-separated namespace: prefix.action
_EVENT_TYPE_RE = re.compile(r"^[a-z_]+\.[a-z_]+$")
_VALID_PREFIXES = frozenset({"probe", "hint", "refute", "session"})

# Prefixes that require behavioral tracking consent
_CONSENT_REQUIRED_PREFIXES = frozenset({"session"})


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
                f"event_type prefix must be one of {_VALID_PREFIXES}, got '{prefix}'"
            )

    @classmethod
    def _check_consent(cls, user: "User | None", event_type: str) -> None:
        """Check behavioral tracking consent for session events.

        Defense in depth — the view layer also checks, but the service is
        the general entry point and must enforce consent independently.

        Raises:
            ValueError: If consent is required but not granted.
        """
        prefix = event_type.split(".")[0]
        if prefix in _CONSENT_REQUIRED_PREFIXES and user is not None:
            from purplex.users_app.models import ConsentType
            from purplex.users_app.services.consent_service import ConsentService

            if not ConsentService.has_active_consent(
                user, ConsentType.BEHAVIORAL_TRACKING
            ):
                raise ValueError(
                    "Behavioral tracking consent required for session events"
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
    ) -> "ActivityEvent":
        """Build an ActivityEvent instance without saving.

        Populates anonymous_user_id via AnonymizationService at write time.
        Validates event_type format.
        """
        from .models import ActivityEvent

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
    ) -> "ActivityEvent":
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
            ValueError: If event_type format is invalid or consent missing.
        """
        cls._check_consent(user, event_type)

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
                ActivityEventRepository.create(event)
        except IntegrityError:
            if idempotency_key:
                existing = ActivityEventRepository.get_by_idempotency_key(
                    idempotency_key
                )
                logger.info(
                    "Duplicate idempotency_key %s, returning existing event %s",
                    idempotency_key,
                    existing.id,
                )
                return existing
            raise

        logger.debug(
            "Recorded %s event for user %s (problem=%s, course=%s)",
            event_type,
            user.id if user else None,
            problem.id if problem else None,
            course.id if course else None,
        )
        return event

    @classmethod
    def record_best_effort(
        cls,
        user: "User | None",
        event_type: str,
        payload: dict | None = None,
        problem: "Problem | None" = None,
        course: "Course | None" = None,
        schema_version: int = 1,
        idempotency_key: str | None = None,
    ) -> "ActivityEvent | None":
        """Fire-and-forget wrapper around record().

        Failures are logged at WARNING level but never raised.
        Use this in views where recording must not break the primary flow.
        """
        try:
            return cls.record(
                user=user,
                event_type=event_type,
                payload=payload,
                problem=problem,
                course=course,
                schema_version=schema_version,
                idempotency_key=idempotency_key,
            )
        except Exception:
            logger.warning(
                "Failed to record %s event for user=%s",
                event_type,
                user.id if user else None,
                exc_info=True,
            )
            return None
