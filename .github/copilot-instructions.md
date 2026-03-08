# Purplex — Copilot Review Instructions

## Architecture: Three-Layer Separation (STRICT)

Views (controllers) -> Services (business logic) -> Repositories (data access).

- **Views** never import or call Django ORM (`.objects`, `.filter`, `.get`, `.save`).
- **Services** never import or call Django ORM — they call repository methods.
- **Repositories** never return QuerySets — they return `list[Model]`, `Model | None`, or Python primitives.

Flag any violation of these boundaries.

## Error Response Format

All API errors return `{"error": "..."}`. A custom exception handler in `purplex/utils/exception_handler.py` normalizes DRF exceptions automatically. Views should raise DRF exceptions (`NotFound`, `ValidationError`, `PermissionDenied`), not `ValueError`.

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

## Tests Use Factory Boy

Tests must use factories from `tests/factories/`, never `Model.objects.create()`.
