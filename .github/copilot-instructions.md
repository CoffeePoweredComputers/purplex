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

## Tests Use Factory Boy

Tests must use factories from `tests/factories/`, never `Model.objects.create()`. If no factory exists for a model, add one.
