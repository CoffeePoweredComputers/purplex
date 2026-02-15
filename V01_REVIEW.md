# Purplex V1 Codebase Review

> **Branch:** `admin-page-cleanup` | **Reviewed:** 2026-02-08 | **Updated:** 2026-02-15 | **Target release:** 2026-02-21

---

## Overall Assessment

The codebase is in good shape for a V1 release serving hundreds of university students. The architecture is sound, the privacy implementation is genuinely thoughtful, and the issues identified are the kind that accumulate in any fast-moving codebase. None suggest carelessness — they suggest prioritization.

The only item I'd call a real risk is missing transaction boundaries. Everything else is either low-probability, self-correcting, or caught immediately during manual testing.

---

## Commits Landed (2026-02-15)

The `admin-page-cleanup` branch was organized into 5 logical commits and pushed:

| # | Commit | Scope | Files |
|---|--------|-------|------:|
| 1 | `a877d5c` | Ruff formatting fixes (zero behavior change) | 23 |
| 2 | `d8a7dad` | Security hardening (hmac, creds, SSL) | 4 |
| 3 | `39e0a42` | Admin page cleanup + DataTable component | 19 |
| 4 | `92b67bf` | Privacy/consent system (GDPR/FERPA/DPDPA) | 54 |
| 5 | `33ee24c` | Infrastructure, deps, scripts, docs | 38 |

---

## Fixes Applied During Review (14 total)

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

## Remaining Work — Agent Task List

Each task below is scoped for an independent branch. Context-gathering instructions are included so any agent (or developer) can pick up a task cold.

---

### TASK 1: Transaction Boundaries on Pipeline Writes

**Branch name:** `fix/pipeline-transaction-boundaries`
**Severity:** High | **Effort:** Low | **Status:** TODO — next priority

**Problem:** The pipeline's multi-model writes (Submission + CodeVariations + TestExecutions) are not wrapped in `transaction.atomic()`. Worker crash between steps = orphaned records.

**How to get context:**
1. Read `purplex/problems_app/tasks/pipeline.py` — search for `save_submission_helper`, `_save_mcq_result`, `_save_debug_fix_result`, `_save_probeable_code_result`
2. Read `purplex/submissions/models.py` to understand the Submission -> TestExecution -> CodeVariation relationships
3. Grep for `transaction.atomic` across the codebase to confirm there are zero existing uses

**What to do:**
- Wrap each save helper's multi-model create block in `with transaction.atomic():`
- Four code paths need it (search for `Submission.objects.create` in pipeline.py)
- Do NOT add retries or change Celery task behavior — just wrap the DB writes
- Run `pytest -m unit -k pipeline` after to verify nothing breaks

**Affected code paths:**
- `pipeline.py` — `save_submission_helper` (EiPL)
- `pipeline.py` — MCQ pipeline save
- `pipeline.py` — Debug Fix pipeline save
- `pipeline.py` — Probeable Code pipeline save

---

### TASK 2: Verify and Fix Submission Status Enum

**Branch name:** `fix/submission-status-enum`
**Severity:** Medium | **Effort:** Low | **Status:** DONE (2026-02-15)

**Problem:** Frontend uses `'passed' | 'partial' | 'failed' | 'pending'`. Backend uses `'complete' | 'partial' | 'incomplete'`. Only `'partial'` overlaps. Either there's a mapping layer, or status badges are silently wrong.

**How to get context:**
1. Read `purplex/submissions/models.py` — find the status field choices (~line 99-108)
2. Read `purplex/client/src/types/index.ts` — search for `SubmissionStatus` or the status union type (~line 461)
3. Grep frontend for `passed`, `failed`, `complete`, `incomplete` to find where status values are consumed or transformed
4. Grep backend serializers (`problems_app/serializers.py`, `submissions/`) for any `SerializerMethodField` or property that maps status values
5. Check `purplex/client/src/components/ui/StatusBadge.vue` to see what values it actually renders

**What to do:**
- If a mapping exists: document it, ensure it's consistent, done
- If no mapping exists: decide on canonical values (recommend backend wins), add a mapping in the frontend service layer or serializer, update the TypeScript type
- Either way, add a comment in both locations cross-referencing the other

---

### TASK 3: Fix Course Reorder URL Mismatch

**Branch name:** `fix/course-reorder-url`
**Severity:** Medium | **Effort:** Trivial | **Status:** DONE (2026-02-15)

**Problem:** Frontend calls `/problem-sets/reorder/`. Backend registers `/problem-sets/order/`. This is a 404.

**How to get context:**
1. Read `purplex/client/src/services/contentService.ts` — search for `reorder` (~line 477-486)
2. Read `purplex/problems_app/urls.py` — search for `order` (~line 329-332)

**What to do:**
- Pick one name (recommend `reorder` since it's more descriptive)
- Update whichever side is wrong (probably the backend URL)
- Grep both codebases for the old name to catch any other references
- If changing the backend URL, check if any other frontend service calls the old path

---

### TASK 4: Fix Course Student Response Structure

**Branch name:** `fix/course-student-serializer`
**Severity:** Medium | **Effort:** Low | **Status:** DONE (2026-02-15)

**Problem:** Frontend expects nested `{ user: { id, email, username } }`. Backend returns flat `{ user_id, username, email }`.

**How to get context:**
1. Read `purplex/client/src/types/index.ts` — search for `CourseStudent` or similar (~line 714-730)
2. Read `purplex/problems_app/serializers.py` — search for `CourseEnrollmentSerializer` (~line 1553-1602)
3. Read `purplex/client/src/components/content/CourseStudentsPage.vue` to see how the data is consumed

**What to do:**
- Either nest the backend response (update serializer) or flatten the frontend type (update type + component)
- Recommend updating the frontend type to match backend since the flat structure is simpler
- Update `CourseStudentsPage.vue` if it accesses `student.user.email` etc.

---

### TASK 5: Standardize Pagination Across All Endpoints

**Branch name:** `fix/pagination-standard`
**Severity:** Medium | **Effort:** Low-Medium | **Status:** TODO

**Problem:** Frontend `useDataTable` expects `total_pages` and `current_page`. DRF's default `PageNumberPagination` doesn't return these. Some endpoints manually add them, others don't.

**How to get context:**
1. Read `purplex/client/src/types/datatable.ts` (~line 13-21) for expected response shape
2. Read `purplex/settings/base.py` (~line 198) for the default paginator config
3. Grep backend for `total_pages` and `current_page` to find which endpoints already return them
4. Read `purplex/users_app/user_views.py` — `AdminUserManagementView.get()` as an example of manual pagination

**What to do:**
- Create a custom `StandardPagination` class (extends `PageNumberPagination`) that adds `total_pages` and `current_page` to every response
- Set it as `DEFAULT_PAGINATION_CLASS` in `settings/base.py`
- Remove manual pagination logic from `user_views.py` and any other views that duplicate it
- Verify `useDataTable` works against the standardized response

---

### TASK 6: Progress Aggregate Race Condition

**Branch name:** `fix/progress-race-condition`
**Severity:** Medium | **Effort:** Medium | **Status:** TODO — defer to post-V1 unless concurrency is high

**Problem:** `UserProblemSetProgress.update_from_progress` runs an aggregate query then writes the rollup. Concurrent submissions for different problems in the same problem set can both read stale counts.

**How to get context:**
1. Read `purplex/problems_app/models/progress.py` — find `update_from_progress` (~line 113-150)
2. Read `purplex/problems_app/services/progress_service.py` — find where `update_from_progress` is called (~line 836)
3. Understand the `UserProgress` -> `UserProblemSetProgress` rollup relationship

**What to do:**
- Wrap the aggregate + `update_or_create` in `transaction.atomic()`
- Add `select_for_update()` on the UserProgress rows being aggregated
- Add a test that simulates concurrent progress updates (use `threading` or mock the race)
- Self-correcting bug — low urgency unless you see stale dashboards in production

---

### TASK 7: DRF Exception Handler (Error Standardization — Phase 1)

**Branch name:** `improve/drf-exception-handler`
**Severity:** Medium | **Effort:** Low (phase 1 only) | **Status:** TODO — post-V1

**Problem:** Four different error handling patterns across views. Phase 1 is just the exception handler (~20 lines) that gets 80% of the benefit.

**How to get context:**
1. Grep views for `except Exception` to find bare catches: `purplex/problems_app/views/admin_views.py`, `instructor_content_views.py`, `submission_views.py`
2. Grep for `"error"` in Response calls to see the current error format
3. Read DRF docs on custom exception handlers: `REST_FRAMEWORK['EXCEPTION_HANDLER']`

**What to do (Phase 1 only):**
- Create `purplex/utils/exception_handler.py` with a custom handler that maps: `ValueError -> 400`, `ObjectDoesNotExist -> 404`, `PermissionDenied -> 403`
- All return `{"error": str(e)}` format (already the convention)
- Set it in `settings/base.py` under `REST_FRAMEWORK`
- Do NOT strip existing try/except blocks yet — that's Phase 2

---

### TASK 8: User Deletion Race Condition

**Branch name:** `fix/deletion-race-condition`
**Severity:** Low-Medium | **Effort:** Medium | **Status:** TODO — defer to post-V1

**Problem:** `cancel_deletion` and `execute_hard_deletion` don't use `select_for_update()`. Concurrent cancel + delete = reactivated user with no data. Also, pipeline doesn't check `user.is_active`.

**How to get context:**
1. Read `purplex/users_app/services/data_deletion_service.py` — `cancel_deletion` (~line 76-94) and `execute_hard_deletion` (~line 97-231)
2. Read `purplex/problems_app/tasks/pipeline.py` — early section (~line 479-500) where submission is created

**What to do:**
- Add `select_for_update()` on UserProfile reads in both `cancel_deletion` and `execute_hard_deletion`
- Add `if not user.is_active: raise` check early in the pipeline before creating a Submission
- Add tests for the race condition scenario

---

### TASK 9: Sentry View-Layer Integration

**Branch name:** `improve/sentry-views`
**Severity:** Low | **Effort:** Low | **Status:** TODO — post-V1

**Problem:** Sentry captures Celery task errors but not view-layer 500s.

**How to get context:**
1. Grep for `sentry_sdk` across the codebase to see current usage
2. Read `purplex/problems_app/tasks/pipeline.py` (~line 1150-1160) for the existing Sentry integration pattern
3. Check `requirements.txt` for `sentry-sdk` version

**What to do:**
- If sentry-sdk is installed, add `DjangoIntegration` to `sentry_sdk.init()` in settings (it auto-captures view errors)
- If not installed, add `sentry-sdk[django]` to requirements and init in `settings/production.py`
- Combine with Task 7's exception handler if doing both

---

### TASK 10: UserConsent Database-Level Immutability

**Branch name:** `improve/consent-db-trigger`
**Severity:** Medium | **Effort:** Low | **Status:** TODO — post-V1

**Problem:** Python-level `save()`/`delete()` overrides are bypassed by `QuerySet.update()` and `QuerySet.delete()`. No code currently does this, but the audit trail is legally required.

**How to get context:**
1. Read `purplex/users_app/models.py` — `UserConsent.save()` and `UserConsent.delete()` overrides
2. Read `purplex/users_app/migrations/` to understand the current schema

**What to do:**
- Create a migration that adds a PostgreSQL trigger: `BEFORE UPDATE OR DELETE ON users_app_userconsent RAISE EXCEPTION`
- Test that both Django ORM `.update()` and raw SQL `DELETE` are blocked
- The Python guards stay in place for better error messages

---

## Test Coverage Gaps (reference — not individual tasks)

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
| CODE_OF_CONDUCT.md placeholder | Needs preferred contact method |
| Celery retry backoff on pipeline tasks | Existing retry behavior works; enhancement, not fix |
| AI consent gate in ai_generation_service.py | Already gated at pipeline.py (the only caller) |
| CI integration tests non-blocking | Appears intentional for development workflow |
| Rate limiting on privacy endpoints | Good enhancement but not V1 blocker (endpoints are auth-gated, operate on request.user only) |
