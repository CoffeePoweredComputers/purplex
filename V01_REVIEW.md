# Purplex — Post-V1 TODO

> **Reviewed:** 2026-02-08 | **V1 tasks completed:** 2026-02-16

All 10 review tasks from the original V1 codebase review are done. What remains below is follow-up work identified during that review.

---

## Error Handling Cleanup — Phase 2

**Severity:** Medium | **Effort:** Medium

Phase 1 (Task 7) added a custom DRF exception handler. Phase 2 is stripping the 20 `except Exception` blocks across views that are now redundant. Full plan at `docs/plans/ERROR_HANDLING_CLEANUP.md`.

**What to do:**
- Replace `except ValueError` string-matching in views with typed exceptions (`NotFoundError`, `ValidationError`)
- Remove bare `except Exception` blocks that duplicate the DRF handler
- Fix `_delete_firebase_account()` — currently raises on error but `test_returns_false_on_firebase_error` expects it to return `False` (pre-existing broken test)

**Files:** `problems_app/views/admin_views.py`, `instructor_content_views.py`, `submission_views.py`, `users_app/views/privacy_views.py`

---

## Deferred Items

| Item | Reason |
|------|--------|
| Dockerfile USER directive | Infrastructure decision, requires Docker build testing |
| CODE_OF_CONDUCT.md placeholder | Needs preferred contact method |
| Celery retry backoff on pipeline tasks | Existing retry behavior works; enhancement, not fix |
| AI consent gate in `ai_generation_service.py` | Already gated at `pipeline.py` (the only caller) |
| CI integration tests non-blocking | Appears intentional for development workflow |
| Rate limiting on privacy endpoints | Good enhancement but not V1 blocker (auth-gated, operates on `request.user` only) |
| Progress aggregate race condition | Self-correcting — each call recalculates from source of truth. `select_for_update()` would block gevent greenlets. Monitor in production. |

---

## Test Coverage Gaps

### Backend — Missing Test Files

- `ProgressService` — aggregation logic, race conditions
- `GradingService` — submission scoring
- `SubmissionService` — submission creation
- `StudentService`, `CourseService`, `InstructorAnalyticsService`
- `AuthenticationService`, `RateLimitService`

### Backend — Missing Edge Cases

- No cascade deletion tests (problem with submissions deleted)
- No concurrent submission tests
- No Docker-unavailable pipeline tests

### Backend — Missing Factories

`Submission`, `TestExecution`, `CodeVariation`, `HintActivation`, `SegmentationAnalysis`, `UserProblemSetProgress` — tests create these manually with `Model.objects.create()`.

### Frontend — No Tests

- 12+ composables (`useTokenRefresh`, `useSubmissions`, `useContentContext`, etc.)
- All 7 activity input components, all 8 feedback components
- All navigation components, all UI components (DataTable, StatusBadge, etc.)
- No error/loading state tests
- No router auth guard tests
