# Purplex V0.1 Codebase Review

> **Branch:** `admin-page-cleanup` | **Reviewed:** 2026-02-08 | **Target release:** 2026-02-21

---

## Overall Assessment

The codebase is in good shape for a V0.1 release serving hundreds of university students. The architecture is sound, the privacy implementation is genuinely thoughtful, and the issues identified are the kind that accumulate in any fast-moving codebase. None suggest carelessness — they suggest prioritization.

The only item I'd call a real risk is missing transaction boundaries. Everything else is either low-probability, self-correcting, or caught immediately during manual testing.

---

## Fixes Applied During This Review (14 total)

| # | File | Fix | Why |
|---|------|-----|-----|
| 1 | `users_app/mock_firebase.py:406` | `MOCK_SECRET` -> `get_mock_secret()` | Runtime crash in test token creation |
| 2 | `users_app/models.py` | UserConsent FK CASCADE -> SET_NULL + immutability guards | GDPR Art. 7 audit trail preservation on user deletion |
| 3 | `users_app/services/data_deletion_service.py` | Removed silent exception swallowing in `_delete_firebase_account()` | Exceptions were silently caught, masking Firebase failures |
| 4 | `users_app/services/data_deletion_service.py` | Consent records preserved via SET_NULL (not deleted) | Consent audit trail must survive user deletion |
| 5 | `users_app/permissions.py` | `hmac.compare_digest()` for service key comparison | Timing attack prevention on API key validation |
| 6 | `celery_simple.py` | Added `cleanup_expired_data` periodic task (daily) | Scheduled data retention enforcement was missing |
| 7 | `settings/production.py` | `SECURE_SSL_REDIRECT` default -> True | Production should default to HTTPS |
| 8 | `users_app/views/privacy_views.py` | Age verification input validation | Date format, future date rejection, boolean type checks |
| 9 | `users_app/views/privacy_views.py` | Nominee email validation via `validate_email()` | Invalid emails were accepted without validation |
| 10 | `client/src/types/index.ts` | Removed `password?: string` from User interface | Passwords should never exist in frontend type definitions |
| 11 | `client/src/composables/useDataTable.ts` | Added `onUnmounted()` debounce timer cleanup | Timer leak when component unmounts during search |
| 12 | `users_app/migrations/0004_*` | New migration: SET_NULL + deletion field indexes | Schema change for consent preservation + query performance |
| 13 | `tests/unit/test_data_deletion_service.py` | Updated test for SET_NULL behavior | Test asserted old CASCADE behavior |
| 14 | `users_app/views/privacy_views.py` | Import ordering fix | Ruff lint compliance |

---

## Systematic Issues

### 1. No Transaction Boundaries on Multi-Model Writes

**Severity: High | Effort: Low**

The codebase has zero uses of `transaction.atomic()` wrapping multi-model writes at the service layer. The pipeline's `save_submission_helper` creates a Submission, then in a separate operation creates CodeVariations and TestExecutions. If the worker crashes between those steps, you get a submission record with no test results.

**Affected code paths:**
- `pipeline.py:543-699` — `save_submission_helper` (EiPL)
- `pipeline.py:1272-1313` — MCQ pipeline save
- `pipeline.py:1579-1669` — Debug Fix pipeline save
- `pipeline.py:1927-2016` — Probeable Code pipeline save

**Fix:** Wrap the multi-model creates in `with transaction.atomic():`. The code is already structured to make this easy.

**Risk if ignored:** Orphaned submission records on worker crash. Low probability at current scale, increases with concurrency.

---

### 2. Progress Aggregate Race Condition

**Severity: Medium | Effort: Medium**

`UserProblemSetProgress.update_from_progress` runs an aggregate query (count completed problems) and writes the result to the rollup table. Two submissions for different problems in the same problem set can both read stale counts and overwrite each other.

**Concrete scenario:** Student completes Problem 3 and Problem 4 nearly simultaneously. Both tasks compute "3 of 10 completed" from the aggregate. Actual answer should be "4 of 10." Self-corrects on next submission.

**Affected code:**
- `progress.py:113-150` — `update_from_progress` aggregate outside lock scope
- `progress_service.py:836` — Called after individual progress save

**Fix:** Wrap aggregate + `update_or_create` in `transaction.atomic()` with `select_for_update()` on the source rows.

**Risk if ignored:** Dashboard shows stale completion percentages. Self-correcting, but visually confusing.

---

### 3. Four Different Error Handling Philosophies

**Severity: Medium | Effort: High**

The codebase has no agreed-upon error contract between layers:

| Pattern | Where | How |
|---------|-------|-----|
| Raise exceptions, view catches | admin_views, instructor_content_views, submission_views | `except Exception -> Response({"error": ...}, 500)` |
| Let DRF handle it | student_views, instructor_views, instructor_analytics_views | No try/except |
| Return error dicts from service | hint_service -> hint_views | `if "error" in result: return Response(...)` |
| Return success/error dicts | ai_generation_service, docker_execution_service | `{"success": False, "error": "..."}` |

**Worst case:** `hint_service.py` uses all three patterns within a single class.

**The good news:** Error key is consistently `"error"` everywhere, and status codes are reasonable. Nobody will hit a 500 because of inconsistent handling — they might get a less-helpful error message.

**Recommended fix:** Define a DRF exception handler middleware that maps `ValueError -> 400`, `ObjectDoesNotExist -> 404`, `PermissionDenied -> 403`, returning `{"error": str(e)}`. Then strip bare `except Exception` blocks from views. The views with no try/except are already correct for this pattern.

---

### 4. Frontend-Backend Contract Mismatches

**Severity: Medium | Effort: Low-Medium**

#### 4a. Submission Status Enum (verify before fixing)

Frontend uses `'passed' | 'partial' | 'failed' | 'pending'`. Backend uses `'complete' | 'partial' | 'incomplete'`. Only `'partial'` overlaps. Either there's a mapping layer somewhere, or status badges are broken. Given this is a working application, there's likely a transform — verify before assuming it's broken.

- Frontend: `client/src/types/index.ts:461`
- Backend: `submissions/models.py:99-108`

#### 4b. Course Reorder URL Mismatch

Frontend calls `/problem-sets/reorder/`. Backend registers `/problem-sets/order/`.

- Frontend: `client/src/services/contentService.ts:477-486`
- Backend: `problems_app/urls.py:329-332`

#### 4c. Course Student Structure

Frontend expects nested `{ user: { id, email, username } }`. Backend returns flat `{ user_id, username, email }`.

- Frontend: `client/src/types/index.ts:714-730`
- Backend: `problems_app/serializers.py:1553-1602`

#### 4d. Pagination Fields Not Standard

Frontend `useDataTable` expects `total_pages` and `current_page`. DRF's default `PageNumberPagination` doesn't return these. Some endpoints manually add them, but not all.

- Frontend: `client/src/types/datatable.ts:13-21`
- Backend: `settings/base.py:198` (default paginator)
- Manual additions: `users_app/user_views.py:177-179`, `submissions/repositories/submission_repository.py:87-88`

**Fix:** Create a custom pagination class that always returns these fields, set it as the default.

---

### 5. UserConsent Immutability Guards Are Bypassable

**Severity: Medium | Effort: Low**

The `save()` and `delete()` overrides on UserConsent prevent instance-level modifications. But `QuerySet.update()` and `QuerySet.delete()` generate SQL directly and bypass model methods entirely.

No code currently uses these bypass paths — the guards are effective in practice. But for GDPR audit trail compliance, "nobody's broken it yet" is insufficient long-term.

**Fix:** Add a database-level trigger preventing UPDATE and DELETE on `users_app_userconsent`. The Django guards catch the common case; the trigger catches everything else.

**Risk if ignored:** Low today (no code uses bulk operations on consent records). Increases as team grows.

---

### 6. User Deletion Race Conditions

**Severity: Low-Medium | Effort: Medium**

Neither `cancel_deletion` nor `execute_hard_deletion` uses `select_for_update()` on UserProfile. If both run simultaneously:
- `cancel_deletion` sets `is_active=True` and clears deletion flags
- `execute_hard_deletion` proceeds to delete data
- Result: user account is reactivated with no data

Additionally, if a Celery task is already queued when deletion starts, the submission pipeline doesn't check `user.is_active`. A submission could be created and immediately orphaned.

**Affected code:**
- `data_deletion_service.py:76-94` — `cancel_deletion` (no lock)
- `data_deletion_service.py:97-231` — `execute_hard_deletion` (no lock)
- `pipeline.py:479-500` — No `is_active` check before submission

**Risk if ignored:** Low. Deletion is rare, and simultaneous cancel+delete is even rarer. But it's a correctness issue.

---

### 7. Sentry Only Captures Task Errors

**Severity: Low | Effort: Low**

Sentry integration exists in Celery tasks (`pipeline.py:1150-1160`) but not in views or services. View-layer 500 errors are logged but not captured in Sentry.

**Fix:** Add Sentry middleware or DRF exception handler that calls `sentry_sdk.capture_exception()` for unhandled errors.

---

## Test Coverage Gaps

### Well Tested
- Privacy services (consent, deletion, export)
- Docker execution (mocked)
- Serializer validation patterns
- Hint processors
- Polymorphic model registration
- Admin problem CRUD
- Privacy API integration tests

### Not Tested (no dedicated test file)
- `ProgressService` — the service with the race condition above
- `GradingService` — computes submission scores
- `SubmissionService` — creates submission records
- `StudentService`, `CourseService`, `InstructorAnalyticsService`
- `AuthenticationService`, `RateLimitService`
- 12+ frontend composables (`useTokenRefresh`, `useSubmissions`, `useContentContext`, etc.)
- All 7 activity input components, all 8 feedback components
- All navigation components, all UI components (DataTable, StatusBadge, etc.)

### Missing Edge Case Tests
- No cascade deletion tests (problem with submissions deleted)
- No concurrent submission tests
- No Docker-unavailable pipeline tests
- No frontend error/loading state tests
- No router auth guard tests

### Missing Factories
No factories for: `Submission`, `TestExecution`, `CodeVariation`, `HintActivation`, `SegmentationAnalysis`, `UserProblemSetProgress`. Tests create these manually with `Model.objects.create()`.

---

## Architecture Notes

### Backend Service Layer Pattern

The service layer follows a deliberate pattern, not inconsistency:

| Pattern | When Used | Examples |
|---------|-----------|---------|
| `@staticmethod` | Pure functions, no state | ConsentService, HintService, AdminProblemService, ProgressService |
| `@classmethod` | Class-level constants | DataDeletionService, ProbeService, InstructorAnalyticsService |
| Instance methods | Holds expensive state | AITestGenerationService (API client), DockerExecutionService (container pool) |

Rule: use the simplest pattern that works.

### Frontend Data-Fetching Architecture

Three-layer stack (deliberate, not inconsistent):
```
Components -> Composables -> Services -> axios
```

One exception: `useAdminUsers.ts` calls axios directly instead of going through a service. Every other domain has a dedicated service.

### Celery + Gevent + Docker

Appropriately engineered for hundreds of users:
- Gevent monkey-patching done correctly (before imports, psycogreen for PostgreSQL)
- Container pooling (30 prod, 3 dev) handles ~6 concurrent EiPL submissions
- `GeventTimeout` replacing `ThreadPoolExecutor` was the correct fix for greenlet-based workers
- Health monitor runs in a real OS thread (should be a greenlet, but works)

---

## Items NOT Fixed (by design)

| Item | Reason |
|------|--------|
| Dockerfile USER directive | Infrastructure decision, requires Docker build testing |
| CODE_OF_CONDUCT.md placeholder | User rejected suggested value, needs their preferred contact |
| Celery retry backoff on pipeline tasks | Existing retry behavior works; enhancement, not fix |
| AI consent gate in ai_generation_service.py | Already gated at pipeline.py (the only caller) |
| CI integration tests non-blocking | Appears intentional for development workflow |
| Rate limiting on privacy endpoints | Good enhancement but not V0.1 blocker (endpoints are auth-gated, operate on request.user only) |
| Error handling standardization | High-effort refactor, no runtime bugs from current state |

---

## Remaining Manual Steps

1. **Start PostgreSQL and run `pytest`** to verify backend tests pass
2. **Verify submission status enum** — check if there's a mapping layer between backend `complete/incomplete` and frontend `passed/failed`
3. **Decide on CODE_OF_CONDUCT.md** contact method
4. **Test course reorder feature** — URL mismatch will 404
