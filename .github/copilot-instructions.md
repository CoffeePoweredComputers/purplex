# Purplex — Copilot Review Instructions

## Architecture: Three-Layer Separation (STRICT)

Views (controllers) -> Services (business logic) -> Repositories (data access).

- **Views** must not import model classes or call Django ORM (`Model.objects.*`, `instance.save()`, `instance.delete()`). Serializer `.save()` is fine.
- **Services** never import or call Django ORM — they call repository methods.
- **Repositories** prefer concrete types (`list[Model]`, `Model | None`, primitives) over QuerySets. Intentional QuerySet returns for DRF validation, pagination, or annotated listings are allowed.

Flag any violation of these boundaries.

## Error Response Format

All API errors return `{"error": ...}` (string or structured validation payload). A custom exception handler in `purplex/utils/exception_handler.py` normalizes DRF exceptions automatically. Views should raise DRF exceptions (`NotFound`, `ValidationError`, `PermissionDenied`), not `ValueError`.

## Soft-Delete: Course Model

`Course.objects` excludes soft-deleted rows (`is_deleted=True`) via `ActiveCourseManager`.
Use `Course.all_objects` for:
- `get_or_create` / `update_or_create` (to avoid unique constraint violations)
- Uniqueness checks, admin views, or any query that must include deleted rows

Flag `Course.objects.get_or_create` or `Course.objects.update_or_create` as bugs.

## Permission Classes Required

Every DRF `APIView` subclass must declare `permission_classes`. Flag views missing it.

## No Course.instructor FK

The `Course.instructor` foreign key has been removed. All instructor data lives in the `CourseInstructor` through-table. Flag any reference to `Course.instructor` or `course.instructor`.

## Logging

- Python: Use `logging.getLogger(__name__)`. No `print()` statements.
- TypeScript: No `console.log` in production code.

## FERPA Compliance

Never expose student emails or real names in API responses without checking `user.profile.directory_info_visible`. This applies to enrollment serializers and any user-facing list.

## Data Models: Strict Review Policy

See `.github/instructions/data-models.instructions.md` for the full 21-rule policy. Key areas:

**Structural integrity:**
- FK `on_delete` must be intentional: `SET_NULL` for user/actor FKs, `PROTECT` for content FKs on transactional models, `SET_NULL` across the board on event/audit log models.
- Append-only models (events, audit logs, consent records) must enforce immutability at both Python and database levels.
- Every `JSONField` must have a documented schema, `schema_version` in payloads, and no PII.
- Every new model needs: on_delete regression tests, a Factory Boy factory, and compound indexes for expected query patterns.

**Privacy & compliance (FERPA, COPPA, GDPR):**
- Event records must snapshot an anonymized user ID at write time (survives user deletion for research correlation).
- New user FK models must be wired into `DataDeletionService`, `DataExportService`, and the `cleanup_expired_data` command.
- Consent must be verified before recording behavioral/research data (`ConsentService` checks).
- Never expose student PII without checking `directory_info_visible`. Never store PII in event payloads.
- Age verification required before collecting data from minors (COPPA under-13, DPDPA under-18).

**Research data integrity:**
- Idempotent event recording (unique constraints or idempotency keys) to prevent duplicate corruption.
- Research endpoints must create `DataAccessAuditLog` entries (IRB compliance).
- Retention windows must reference centralized `DATA_RETENTION` settings, not hardcoded values.

## Tests Use Factory Boy

Tests must use factories from `tests/factories/`, never `Model.objects.create()`. If no factory exists for a model, add one.
