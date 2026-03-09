---
applyTo: "purplex/**/*.py"
---

# Python Backend Review Rules

## 1. Views must not call ORM

Never call `Model.objects.*`, `instance.save()`, or `instance.delete()` in a view. Serializer `.save()` is fine.

```python
# WRONG
course = Course.objects.get(id=course_id)
# RIGHT
course = CourseService.get_course_by_id(course_id)
```

## 2. Services must not call ORM

Services call repository methods for data access.

```python
# WRONG (in a service)
submissions = Submission.objects.filter(user=user)
# RIGHT
submissions = SubmissionRepository.get_submissions_for_user(user)
```

## 3. Repository methods prefer concrete Python types over QuerySets

QuerySet returns are allowed for DRF validation, pagination, or annotated listings.

```python
# WRONG
def get_courses(self) -> QuerySet:
    return Course.objects.filter(is_active=True)
# RIGHT
def get_courses(self) -> list[Course]:
    return list(Course.objects.filter(is_active=True))
```

## 4. No bare `except Exception` in views

The custom exception handler returns JSON 500 for unhandled exceptions. Bare `except Exception` hides bugs.

```python
# WRONG
try:
    result = SomeService.do_thing()
except Exception:
    return Response({"error": "Something went wrong"}, status=500)
# RIGHT — let the exception handler do its job
result = SomeService.do_thing()
```

## 5. Views must raise DRF exceptions, not ValueError

In views/serializers, raise DRF exceptions for correct HTTP responses. Services/repos may use `ValueError`.

```python
# WRONG (in a view)
raise ValueError("Course not found")
# RIGHT (in a view)
from rest_framework.exceptions import NotFound
raise NotFound("Course not found")
```

## 6. Course.objects vs Course.all_objects

`Course.objects` excludes soft-deleted rows. For `get_or_create` and `update_or_create`, use `all_objects` to prevent unique constraint violations on deleted rows.

```python
# WRONG — misses soft-deleted slugs, causes IntegrityError
Course.objects.get_or_create(slug=slug, defaults={...})
# RIGHT
Course.all_objects.get_or_create(slug=slug, defaults={...})
```

## 7. Every APIView must declare permission_classes

```python
# WRONG
class MyCourseView(APIView):
    def get(self, request): ...
# RIGHT
class MyCourseView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request): ...
```

## 8. Use lazy logging, not f-strings

```python
# WRONG — string formatted even if log level is disabled
logger.error(f"Failed for user {user.id}: {err}")
# RIGHT — lazy evaluation + better Sentry grouping
logger.error("Failed for user %s: %s", user.id, err)
```

## 9. Use transaction.atomic() for multi-step writes

Wrap multi-step writes in `transaction.atomic()` to prevent partial state.

```python
# WRONG
course = CourseRepository.create_course(data)
CourseInstructorRepository.add_instructor(course, user, "primary")
# RIGHT
with transaction.atomic():
    course = CourseRepository.create_course(data)
    CourseInstructorRepository.add_instructor(course, user, "primary")
```

## 10. Services are static/classmethod classes

No instance state. All methods are `@staticmethod` or `@classmethod`.

```python
# WRONG
service = CourseService()
service.create_course(data)
# RIGHT
CourseService.create_course(data)
```

## 11. Celery tasks must define an explicit retry strategy

Use `bind=True` with either `autoretry_for`/`retry_backoff` or manual `self.retry()`.

```python
# WRONG — no retry strategy
@shared_task
def process(submission_id): ...
# RIGHT
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process(self, submission_id): ...
```

## 12. Repository queries must use select_related/prefetch_related

Use `select_related` (FK/OneToOne) or `prefetch_related` (M2M/reverse FK) to avoid N+1 queries.

```python
# WRONG — N+1 on problem.problem_set access
Submission.objects.filter(user=user)
# RIGHT
Submission.objects.select_related("problem", "problem__problem_set").filter(user=user)
```
