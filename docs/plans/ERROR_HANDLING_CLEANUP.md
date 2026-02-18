# Error Handling Cleanup Plan

> **Status:** Planned | **Prerequisite:** DRF exception handler (done) | **Branch:** `improve/error-handling-cleanup`

## Problem

Services raise `ValueError` for both "not found" and "bad input". Views catch `Exception` broadly and either return a generic 500 or string-match on the error message to pick a status code. One view (`admin_views.py:852`) sniffs exception class names via string comparison.

The custom DRF exception handler (`purplex/utils/exception_handler.py`) covers framework-level normalization but can't fix view/service-level issues.

## Approach

Work bottom-up: fix what services raise first, then simplify what views catch.

---

## Step 1: Service-Layer Exception Classes

Create `purplex/utils/exceptions.py` with two classes:

```python
class NotFoundError(Exception):
    """Raised when a requested resource doesn't exist."""
    pass

class ValidationError(Exception):
    """Raised when input fails service-layer validation (not DRF serializer validation)."""
    pass
```

Why not reuse DRF's exceptions in services? Services shouldn't depend on DRF — they're called from Celery tasks too.

**Add to exception handler** (`purplex/utils/exception_handler.py`):

```python
from purplex.utils.exceptions import NotFoundError, ValidationError as ServiceValidationError

# After the ObjectDoesNotExist block:
if isinstance(exc, NotFoundError):
    return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)

if isinstance(exc, ServiceValidationError):
    return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
```

This means views don't even need to catch these — the handler does it.

---

## Step 2: Migrate Services (one file at a time)

Replace `raise ValueError("X not found")` with `raise NotFoundError("X not found")` in:

| File | Lines | Current | Change to |
|------|-------|---------|-----------|
| `hint_service.py` | 447, 505 | `ValueError("Problem with slug X not found")` | `NotFoundError(...)` |
| `progress_service.py` | 156, 187, 435, 444, 507 | `ValueError("Problem/ProblemSet X not found")` | `NotFoundError(...)` |

Leave `ValueError` in place where it genuinely means "bad input":

| File | Lines | Reason to keep as ValueError |
|------|-------|------------------------------|
| `hint_service.py` | 508, 520, 523 | Input validation ("hints must be an array", "must have type field") |
| `docker_execution_service.py` | 908, 913, 939 | Security validation (forbidden imports/functions) |
| `progress_service.py` | 931 | Input validation |

Consider migrating the input validation `ValueError`s to `ServiceValidationError` for clarity, but this is lower priority since they already map to 400 correctly in views.

---

## Step 3: Simplify Views

Once services raise typed exceptions and the handler catches them, views can drop their try/except blocks for those cases.

### Group A: Remove `except Exception` entirely (handler catches everything)

These views only catch exceptions to map them to error responses. Once the handler does that, the try/except is redundant:

| File | Line | Current pattern |
|------|------|-----------------|
| `instructor_analytics_views.py` | 84 | `except Exception` → 404 (assumes not found) |
| `submission_views.py` | 243 | `except Exception` → 500 |

### Group B: Narrow `except Exception` to specific types

These views do logging or have specific error messages worth keeping:

| File | Line | Change |
|------|------|--------|
| `admin_views.py` | 115, 230, 442, 526 | Narrow to `except (NotFoundError, ServiceValidationError)` + let unknown exceptions propagate |
| `instructor_content_views.py` | 207, 264, 371, 456, 546 | Same |
| `submission_views.py` | 183 | Keep for logging, but remove the 400 response — let handler decide status |
| `admin_views.py` | 308 | Keep — reference solution testing has legitimate catch-all needs |

### Group C: Fix the string-sniffing hack

`admin_views.py:851-852`:
```python
# Before
except Exception as e:
    if "DoesNotExist" in str(type(e).__name__):

# After — just catch the right type
except ObjectDoesNotExist:
    return Response({"error": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)
```

### Group D: Leave alone

| File | Lines | Reason |
|------|-------|--------|
| `health_views.py` | 53, 72, 96 | Correct pattern — health probes should catch everything |
| `sse.py` | 168, 330 | Correct pattern — SSE streams must send error events |
| `privacy_views.py` | 87, 226 | Narrow `ValueError` catches with good error messages |
| `research_views.py` | 80, 89, 179, 189 | Narrow `ValueError` catches for date parsing |
| `hint_views.py` | 155 | Narrow `ValueError` catch for validation |

---

## Step 4: Remove `except ValueError` blocks that mapped to 404

Once `hint_service` and `progress_service` raise `NotFoundError` instead of `ValueError`, these become dead code:

| File | Line | Was |
|------|------|-----|
| `hint_views.py` | 131 | `except ValueError` → 404 |
| `progress_views.py` | 89 | `except ValueError` → 404 |
| `progress_views.py` | 157-161 | `except ValueError` with string matching |

---

## Order of Operations

1. Create `purplex/utils/exceptions.py` and update exception handler — no behavior change yet
2. Migrate `hint_service.py` raises + remove `hint_views.py:131` catch — test with `pytest tests/integration/test_hint_api.py`
3. Migrate `progress_service.py` raises + simplify `progress_views.py` catches
4. Fix `admin_views.py:852` string-sniffing — trivial, independent
5. Narrow remaining `except Exception` blocks one file at a time
6. Each step is independently deployable and testable

## What Not To Do

- Don't catch `ValueError` globally in the exception handler — it hides bugs
- Don't remove try/except blocks from health_views or sse — those are correct
- Don't introduce a base exception class hierarchy with 10 subclasses — two classes are enough
- Don't touch Celery task error handling — different concern, different patterns
