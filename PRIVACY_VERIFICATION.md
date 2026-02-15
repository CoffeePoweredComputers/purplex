# Privacy Feature Verification Checklist

## 1. Consent Management (GDPR Art. 7, DPDPA Sec. 4, CCPA)

- [ ] `GET /api/users/me/consents/` — returns status for all 6 consent types
- [ ] `POST /api/users/me/consents/` with `{"consent_type": "ai_processing"}` — grants consent, returns 201
- [ ] `DELETE /api/users/me/consents/ai_processing/` — withdraws consent, creates a `withdrawn_at` record
- [ ] Append-only audit trail: granting then withdrawing produces 2 separate `UserConsent` rows (not update-in-place)
- [ ] Invalid consent_type returns 400 with helpful error
- [ ] Frontend: `/settings/privacy` — toggle switches work; required types (privacy_policy, terms_of_service) are non-toggleable

## 2. Registration Flow (COPPA, DPDPA, GDPR)

- [ ] Start registration with email + password — advances to age gate (Step 2)
- [ ] Enter DOB making user under 13 — flow terminates at "Parental Consent Required" (COPPA block)
- [ ] Enter DOB making user 13-17 — sets is_minor=true, advances to consent form (Step 3)
- [ ] Enter DOB making user 18+ — advances to consent form normally
- [ ] Consent form requires privacy_policy + terms_of_service checkboxes before proceeding
- [ ] Optional checkboxes (ai_processing, research_use, behavioral_tracking) can be skipped
- [ ] After consent granted: Firebase account created, age verification submitted, consents stored, redirects to Home
- [ ] `POST /api/users/me/age-verification/` stores the record correctly

## 3. Data Export (GDPR Art. 15 + Art. 20, CCPA Right to Know)

- [ ] `GET /api/users/me/data-export/` — returns complete JSON package
- [ ] Exported data includes: profile, submissions, progress records, course enrollments, hint activations, segmentation analyses, consent history, age verification, nominee
- [ ] An audit log entry with action=DATA_EXPORT is created for the request
- [ ] Frontend: PrivacySettings page "Download My Data" button triggers browser file download
- [ ] Downloaded file is valid JSON and machine-readable

## 4. Account Deletion (GDPR Art. 17, CCPA Right to Delete)

- [ ] `DELETE /api/users/me/delete/` — sets user.is_active=False, records deletion_requested_at and deletion_scheduled_at (now + 30 days)
- [ ] Repeat request returns "already_requested" with dates
- [ ] `POST /api/users/me/cancel-deletion/` — re-activates user, clears timestamps
- [ ] Frontend: AccountDeletion component shows confirmation checkbox, pending state with scheduled date, cancel button
- [ ] Hard deletion (via `cleanup_expired_data --dry-run`): verify the 10-step ordered cleanup:
  - [ ] Submissions anonymized (user FK nulled, not deleted)
  - [ ] Hint activations, segmentation analyses, feedback deleted
  - [ ] Progress anonymized/deleted
  - [ ] Enrollments deleted
  - [ ] Consent records, age verification, nominee deleted
  - [ ] Firebase account deleted (mock in dev)
  - [ ] Audit log entry created with AuditAction.DELETE_USER
  - [ ] Django user deleted (CASCADE)
- [ ] `cleanup_expired_data` management command runs without error in --dry-run mode

## 5. FERPA Directory Info Opt-Out

- [ ] `PATCH /api/users/me/directory-info/` with `{"directory_info_visible": false}` — sets opt-out
- [ ] CourseEnrollmentSerializer: when directory_info_visible=false, email/first_name/last_name return None in roster API responses
- [ ] CourseEnrollmentSerializer: when directory_info_visible=true, PII is returned normally
- [ ] Frontend: PrivacySettings toggle for "Show my name and email in course rosters" works
- [ ] Data export includes the directory_info_visible field

## 6. Nominee Management (DPDPA Sec. 8(7))

- [ ] `POST /api/users/me/nominee/` with name/email/relationship — creates nominee, returns 201
- [ ] `GET /api/users/me/nominee/` — returns current nominee details
- [ ] `POST` again — updates existing nominee (returns 200, not 201)
- [ ] `DELETE /api/users/me/nominee/` — removes nominee, returns 204
- [ ] `DELETE` with no nominee — returns 404
- [ ] `GET` with no nominee — returns `{"nominee": null}` with 200
- [ ] Missing required fields return 400

## 7. Audit Logging Middleware (FERPA, GDPR Art. 30/32)

- [ ] `GET /api/admin/users/` — creates VIEW_USER_LIST audit entry
- [ ] `GET /api/admin/users/?search=test` — creates SEARCH_USERS audit entry (not VIEW_USER_LIST)
- [ ] `POST /api/admin/user/<id>/` — creates CHANGE_ROLE audit entry
- [ ] `GET /api/instructor/courses/<id>/students/` — creates VIEW_STUDENT_DETAIL entry
- [ ] `GET /api/instructor/courses/<id>/submissions/` — creates VIEW_SUBMISSIONS entry
- [ ] Failed requests (4xx/5xx) do NOT create audit entries
- [ ] Unauthenticated requests do NOT create audit entries
- [ ] Audit log entries contain: accessor, action, query_parameters, ip_address, timestamp
- [ ] Audit log retention: cleanup_expired_data deletes logs older than 7 years

## 8. AI Consent Gate (GDPR Art. 6/7, DPDPA)

- [ ] With PRIVACY_ENABLE_AI_CONSENT_GATE=True and ai_processing consent NOT granted: generate_variations_helper raises "AI processing consent not granted"
- [ ] With ai_processing consent granted: pipeline proceeds normally
- [ ] segment_prompt_helper returns None (skips segmentation) when consent not granted
- [ ] For minors (is_minor=True): check_ai_consent additionally verifies parental_consent_given
- [ ] With PRIVACY_ENABLE_AI_CONSENT_GATE=False: consent check is skipped entirely

## 9. Cookie Consent Banner (ePrivacy Directive, GDPR)

- [ ] On first visit (no localStorage key): banner appears at bottom of page
- [ ] "Essential Only" button: stores `{essential: true, analytics: false, timestamp: ...}` in localStorage, banner hides
- [ ] "Accept All" button: stores `{essential: true, analytics: true, timestamp: ...}`, banner hides
- [ ] On subsequent visits: banner does not appear (localStorage check)
- [ ] Banner has ARIA role="dialog" for accessibility
- [ ] "Learn more" links to /privacy page

## 10. FERPA Instructor Access Scoping

- [ ] Instructor can only see students/submissions from their own courses (IsCourseInstructor permission)
- [ ] Instructor cannot access `/api/instructor/courses/<other_course>/students/` — returns 403
- [ ] Instructor cannot access `/api/instructor/courses/<other_course>/submissions/` — returns 403
- [ ] Router guard: non-instructor users are blocked from instructor panel routes
- [ ] Submissions endpoint filters by course_filter=course.course_id (the "FERPA-critical filter")

## 11. Research Data Anonymization (FERPA, GDPR Art. 89)

- [ ] ResearchExportService.export_complete_dataset(anonymize=True) replaces user IDs with SHA-256 hashes
- [ ] Same user maps to same anonymous ID within a session (referential integrity preserved)
- [ ] include_code=False omits student code from export
- [ ] Anonymization is deterministic: "user_{id}_{username}" → SHA-256 → 16 hex chars
- [ ] Default behavior is anonymize=True (safe default)

## 12. Privacy Policy and Terms Pages (GDPR Art. 13/14, DPDPA, CCPA)

- [ ] `/privacy` route loads PrivacyPolicy.vue without authentication required
- [ ] `/terms` route loads TermsOfService.vue without authentication required
- [ ] Privacy policy covers all required sections (controller, data collected, purposes, third-party processors, rights, retention, children's privacy, Do Not Sell, cookies, contact, changes)
- [ ] Footer links to /privacy and /terms are present in App.vue
- [ ] Login page links to /privacy and /terms are present

## 13. Data Retention Cleanup Command (GDPR Art. 5(1)(e), DPDPA Sec. 9)

- [ ] `python manage.py cleanup_expired_data --dry-run` runs without error and reports what would be cleaned
- [ ] Processes pending deletions (accounts past 30-day grace)
- [ ] Warns inactive accounts (no login in 12+ months)
- [ ] Cleans audit logs older than 7 years
- [ ] Cleans progress snapshots older than 2 years
- [ ] Retention periods match DATA_RETENTION settings in base.py
