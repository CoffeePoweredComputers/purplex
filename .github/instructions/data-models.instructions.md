---
applyTo: "**/models.py,**/models/*.py,**/migrations/*.py"
---

# Data Model Review Rules

## 1. FK on_delete must be intentional and documented

Every `ForeignKey` and `OneToOneField` must use the correct `on_delete` strategy. Never accept `CASCADE` without explicit justification.

**Project conventions:**
- `SET_NULL` on user/actor FKs — preserves research data and audit trails when accounts are deleted (GDPR Art. 17)
- `PROTECT` on content FKs (Problem, ProblemSet, Course) from Submission and UserProgress — prevents accidental deletion of educational content that has student work
- `CASCADE` only for true child records whose existence depends entirely on the parent (TestExecution, CodeVariation, HintActivation)

```python
# WRONG — CASCADE silently destroys research data when user is deleted
user = models.ForeignKey(User, on_delete=models.CASCADE)
# RIGHT
user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

Flag any FK missing a `help_text` explaining the deletion rationale.

## 2. Append-only / event log models: strict immutability

Models that represent audit trails, consent records, or activity events (UserConsent, DataAccessAuditLog, ActivityEvent) are **append-only**. Enforce:

- **No `auto_now` fields.** `auto_now` allows silent updates on every `save()`. Use `auto_now_add=True` for creation timestamps only.
- **Override `save()` to block updates.** If `self.pk` is set, raise `ValueError("... records are immutable")`.
- **Override `delete()` to block deletion.** Raise `ValueError` or `NotImplementedError`.
- **No `QuerySet.update()` or `bulk_update()` calls** on append-only models anywhere in the codebase.
- **Document the immutability contract** in the model docstring: "This model is append-only. Records must not be updated or deleted after creation."
- **Consider a database-level trigger** (see UserConsent migration 0005 for the pattern) for defense-in-depth against raw SQL or ORM bypass.

```python
# WRONG — allows silent mutation of audit records
class ActivityEvent(models.Model):
    updated_at = models.DateTimeField(auto_now=True)  # never on event tables

# RIGHT
class ActivityEvent(models.Model):
    """Append-only activity event log. Records must not be updated or deleted after creation."""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("ActivityEvent records are immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("ActivityEvent records cannot be deleted")
```

## 3. Event/log models: FK strategy is SET_NULL across the board

Unlike transactional models (Submission uses PROTECT on content FKs), event log models must use `SET_NULL` for all FKs. The event record must survive deletion of any referenced entity.

```python
# WRONG — deleting a problem destroys all its activity events
problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
# ALSO WRONG — blocks problem deletion entirely
problem = models.ForeignKey(Problem, on_delete=models.PROTECT)
# RIGHT — event preserved with null reference
problem = models.ForeignKey(Problem, on_delete=models.SET_NULL, null=True, blank=True)
```

Rationale: event logs are research data. Losing events is worse than losing the FK link. A null `problem_id` still tells researchers "an event of type X happened at time T" — a deleted row tells them nothing.

## 4. Timestamp fields must be indexed

Any `DateTimeField` used for ordering or time-range queries must have `db_index=True`. This is non-negotiable for tables expected to exceed 100k rows.

```python
# WRONG — will cause full table scans on time-range queries
timestamp = models.DateTimeField(auto_now_add=True)
# RIGHT
timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
```

## 5. High-volume tables need compound indexes

Models expecting >100k rows (submissions, events, progress) must define compound indexes in `Meta.indexes` for their common query patterns. Minimum for event tables:

```python
class Meta:
    indexes = [
        models.Index(fields=["user", "-timestamp"]),        # "events by user, newest first"
        models.Index(fields=["event_type", "-timestamp"]),   # "events by type, newest first"
        models.Index(fields=["course", "event_type", "-timestamp"]),  # course-scoped analytics
    ]
    ordering = ["-timestamp"]
```

Flag event/log models with fewer than 2 compound indexes.

## 6. JSONField must have documented schema and size bounds

Every `JSONField` must:
- Document its expected structure in `help_text` or model docstring
- Use `default=dict` (never `null=True` — use empty dict instead)
- Not store data that will be queried by (denormalize to a proper column + index instead)
- Not store PII (email, name, IP address) — these belong in normalized FK columns subject to deletion policies

```python
# WRONG — unstructured, no schema, stores PII
payload = models.JSONField()

# RIGHT — schema documented, no PII, bounded
payload = models.JSONField(
    default=dict,
    help_text="Event-specific data. Schema varies by event_type: "
              "probe.execute: {input: str, output: str, probe_index: int}; "
              "hint.view: {hint_type: str, problem_slug: str}"
)
```

## 7. event_type / status fields: use choices, not free-form strings

`CharField` fields representing categories, types, or statuses must define `choices` or reference a `TextChoices` enum. Free-form strings lead to typos and inconsistency.

```python
# WRONG — allows "hint_view", "hint.View", "HINT_VIEW" etc.
event_type = models.CharField(max_length=80)

# RIGHT — controlled vocabulary, typos caught at validation
event_type = models.CharField(max_length=80, db_index=True)
# With documented convention: "dot-separated namespace (e.g., probe.execute, hint.view)"
# Note: choices list can live outside the model if new types are added without migration
```

Exception: if the design intentionally avoids choices to allow new event types without migrations (as in xAPI/ProgSnap2 convention), this must be explicitly documented in the model docstring with the naming convention enforced in the service layer.

## 8. New models must have on_delete regression tests

Every new model with ForeignKey fields must have corresponding tests in `tests/integration/test_on_delete_behavior.py` that verify:
- `SET_NULL` FKs: record survives, FK field is None after parent deletion
- `PROTECT` FKs: `ProtectedError` raised on parent deletion
- `CASCADE` FKs: child record deleted with parent

Flag any model PR that adds FKs without on_delete tests.

## 9. New models must have a Factory

Every new model must have a corresponding Factory Boy factory in `tests/factories/__init__.py`. Flag PRs that add models without factories.

## 10. Migrations: no data loss, no implicit changes

- `RemoveField` and `DeleteModel` require explicit justification in PR description
- `AlterField` changing `on_delete` strategy must update `test_on_delete_behavior.py`
- `RunPython` data migrations must provide both forward and reverse functions (reverse can be `RunPython.noop` if truly irreversible, but document why)
- `RunSQL` must provide reverse SQL for rollback
- Never combine schema changes and data migrations in a single migration file

## 11. Privacy: PII must not leak into event/log tables

Event and audit log models are long-lived and may outlive user deletion. Never store:
- Email addresses, real names, or display names
- IP addresses (store in short-retention tables only, e.g., DataAccessAuditLog)
- Session tokens or cookies
- Raw user input that may contain personal information

Use FK references to User (with `SET_NULL`) instead. The user record handles PII lifecycle; the event record handles the audit trail.

## 12. Retention policy required for high-volume models

Any model expected to exceed 1M rows per year must document its retention strategy in the model docstring:
- Active retention window (e.g., "3 years")
- Archival format (e.g., "export to Parquet before purge")
- Whether a management command exists for cleanup

```python
class ActivityEvent(models.Model):
    """
    Append-only activity event log.

    Retention: 3 years active. Events older than 3 years exported to
    Parquet via `manage.py archive_activity_events` before deletion.
    Estimated volume: ~6M rows/semester (500 students x 100 events/hr x 4hr x 30d).
    """
```

Flag high-volume models with no retention documentation.

## 13. Event records must snapshot anonymized user context at write time

When a user is deleted, `SET_NULL` preserves the event but destroys the ability to group events by user or correlate across tables. Every event/log model with a nullable user FK must denormalize an **anonymized user identifier** at creation time using `AnonymizationService`.

```python
# WRONG — after user deletion, no way to correlate this user's events
class ActivityEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

# RIGHT — anonymized ID survives deletion, enables research grouping
from purplex.utils.anonymization import AnonymizationService

class ActivityEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    anonymous_user_id = models.CharField(
        max_length=16, db_index=True, blank=True,
        help_text="SHA-256 hash (first 16 chars) of user identity, set at creation time. "
                  "Survives user deletion for research correlation."
    )
```

The service layer must populate `anonymous_user_id` via `AnonymizationService.anonymize_user_id(user)` at write time — never lazily computed. Once the user FK is NULL, the original identity is unrecoverable by design.

## 14. New models with user FKs must integrate with the deletion pipeline

The 2-phase deletion system in `DataDeletionService.execute_hard_deletion()` explicitly handles every model with a user FK. If you add a new model referencing User:

1. **Add it to the deletion sequence** in `DataDeletionService.execute_hard_deletion()` with the correct operation (SET_NULL, CASCADE, or explicit delete)
2. **Add it to the return stats** dict so deletion audits are complete
3. **Add it to `DataExportService.export_user_data()`** so GDPR Art. 15 (right of access) exports include the new data
4. **Test the deletion path** — verify the model doesn't block user deletion via an untested PROTECT FK

```python
# In DataDeletionService.execute_hard_deletion():
# If your model uses SET_NULL on user:
ActivityEvent.objects.filter(user=user).update(user=None)
stats["activity_events_anonymized"] = event_count

# If your model uses CASCADE:
# Django handles it automatically, but document it and count it
```

Flag any PR adding a user FK without updating `DataDeletionService` and `DataExportService`.

## 15. Consent must be verified before recording user activity

The project enforces an AI consent gate (`PRIVACY_ENABLE_AI_CONSENT_GATE`) that blocks AI processing without explicit consent. The same principle applies to any new data collection:

- **Activity events**: Check `ConsentService.has_active_consent(user, ConsentType.BEHAVIORAL_TRACKING)` before recording behavioral events (session tracking, tab switches, editor interactions)
- **Research-specific data**: Check `ConsentService.has_active_consent(user, ConsentType.RESEARCH_USE)` before recording data explicitly collected for research purposes
- **AI-processed data**: Check `ConsentService.check_ai_consent(user)` before any AI processing (this also verifies parental consent for minors)

```python
# WRONG — records behavioral data without consent check
ActivityEventService.record(user=user, event_type="session.start", payload={...})

# RIGHT — consent-gated recording
if ConsentService.has_active_consent(user, ConsentType.BEHAVIORAL_TRACKING):
    ActivityEventService.record(user=user, event_type="session.start", payload={...})
```

Exception: events that are essential for platform operation (submission recording, grade computation) do not require separate behavioral tracking consent — they fall under the core service agreement. Document which event types are consent-gated and which are operational.

## 16. FERPA: never expose student PII without directory_info_visible check

Any serializer, view, or export that includes student names, emails, or other directory information must check `user.profile.directory_info_visible` before including PII. This is a FERPA requirement — students can opt out of directory information disclosure at any time.

```python
# WRONG — exposes email regardless of FERPA opt-out
class StudentSerializer(serializers.Serializer):
    email = serializers.EmailField(source="user.email")

# RIGHT — respects FERPA directory information opt-out
class StudentSerializer(serializers.Serializer):
    email = serializers.SerializerMethodField()

    def get_email(self, obj):
        if hasattr(obj, 'profile') and obj.profile.directory_info_visible:
            return obj.email
        return None
```

This applies to:
- Enrollment list serializers (already enforced in `CourseEnrollmentListSerializer`)
- Research export endpoints (handled by `anonymize=True` default)
- Any new endpoint that returns user data to instructors or admins
- Activity event payloads — never embed student names or emails in JSONField

## 17. COPPA: models collecting data from minors need age verification checks

The project has `AgeVerification` with `is_child` (under 13, COPPA) and `is_minor` (under 18, DPDPA) flags. Any data collection beyond core educational service requires:

- For children (`is_child=True`): Verified parental consent (`parental_consent_given=True`) before collecting behavioral tracking, AI-processed data, or research data
- For minors (`is_minor=True`): Parental consent for AI processing (already enforced in `ConsentService.check_ai_consent`)

Flag any new data collection pathway that doesn't check age verification status when processing data for minors.

## 18. Idempotent event recording to prevent research data corruption

Duplicate events corrupt research data (inflated counts, broken sequences). Event recording must be idempotent. Two patterns:

**Option A — Natural unique constraint** (preferred when a natural key exists):
```python
class Meta:
    unique_together = [["user", "problem", "event_type", "timestamp"]]
    # Or a more specific constraint for the event type
```

**Option B — Caller-provided idempotency key** (for events without a natural unique key):
```python
class ActivityEvent(models.Model):
    idempotency_key = models.CharField(
        max_length=64, unique=True, null=True, blank=True,
        help_text="Optional deduplication key. If set, prevents duplicate recording on retry."
    )
```

The service layer should use `get_or_create` or catch `IntegrityError` to handle duplicates gracefully — never silently write a second record.

## 19. JSONField payloads must include schema_version for evolution

Event payloads change over time (new fields added, old fields deprecated). Since append-only tables can't backfill old records, every JSONField payload that will be used for research must include a `schema_version` integer:

```python
# Service layer — always stamp the version
ActivityEventService.record(
    user=user,
    event_type="probe.execute",
    payload={
        "schema_version": 1,
        "input": "foo(3)",
        "output": "6",
        "probe_index": 2,
    }
)
```

When the payload schema changes:
- Bump the version number
- Document the change in the model docstring or a schema registry
- Research export code must handle all versions (transform old payloads or export with version metadata)
- **Never remove fields** — deprecate by documenting and stop populating, but don't delete the key from the schema definition

## 20. Research data access must be audit-logged

IRB compliance requires tracking who accessed research data, when, and why. The project already has `DataAccessAuditLog` and `AuditMiddleware` for instructor/admin access. New endpoints that expose research data must:

1. **Be covered by AuditMiddleware** — add the URL pattern to the middleware's audited routes
2. **Log the scope of access** — record which course, date range, and data types were queried
3. **Include record counts** — the `record_count` field in `DataAccessAuditLog` documents how many records were accessed

```python
# WRONG — research endpoint with no audit trail
class NewResearchView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        return Response(data)

# RIGHT — audit logged
class NewResearchView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        data = ResearchService.get_data(filters)
        DataAccessAuditLog.objects.create(
            accessor=request.user,
            action="export_research",
            query_parameters=filters,
            ip_address=get_client_ip(request),
            record_count=len(data),
        )
        return Response(data)
```

Flag any new research/analytics endpoint that doesn't create an audit log entry.

## 21. Retention windows must reference DATA_RETENTION settings

The project defines centralized retention windows in `settings.base.DATA_RETENTION`. New models must reference these settings rather than hardcoding retention periods:

```python
# In settings/base.py:
DATA_RETENTION = {
    "SUBMISSIONS_YEARS": 3,
    "PROGRESS_SNAPSHOTS_YEARS": 2,
    "LOGS_DAYS": 90,
    "AUDIT_LOG_RETENTION_YEARS": 7,  # FERPA requires 3+ years
    ...
}
```

New models must:
- Document which `DATA_RETENTION` key governs their lifecycle
- Be added to `cleanup_expired_data` management command if they have a finite retention window
- Audit log models (7-year retention) must never be added to short-retention cleanup

Flag models with hardcoded retention periods that should reference `DATA_RETENTION`.
