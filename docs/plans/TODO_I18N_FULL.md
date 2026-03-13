# Full Internationalization Plan for Purplex

> **Status**: Complete
> **Branch**: `feature/i18n-full-extraction`
> **Supersedes**: `TODO_MULTILINGUAL.md` (infrastructure-focused predecessor)
> **GitHub Issue**: #55

## Context

Purplex supports 17 languages in its settings dropdown, but only 2 `$t()` calls exist in the entire frontend — everything else is hardcoded English. The i18n infrastructure (vue-i18n, lazy loading, persistence, backend API) is solid but unused. This plan connects the wiring.

**Fallback safety:** vue-i18n is configured with `fallbackLocale: 'en'` — any missing translation silently shows the English string. The site never breaks from incomplete translations.

---

## Phase 0: Setup

- [x] Ensure on `master` branch and pull latest
- [x] Open GitHub issue with this plan (#55)
- [x] Create and switch to `feature/i18n-full-extraction` branch
- [x] Write this plan to `docs/plans/TODO_I18N_FULL.md`
- [x] Update `docs/plans/TODO_MULTILINGUAL.md` to reference this plan

---

## Phase 1: Big-Bang String Extraction

### 1a. Expand English locale JSON files

- [x] `en/common.json` — expanded to ~47 keys
- [x] `en/auth.json` — expanded to ~105 keys
- [x] `en/problems.json` — expanded to ~163 keys
- [x] `en/feedback.json` — expanded to ~87 keys
- [x] `en/admin.json` — expanded to ~515 keys

**Total: 917 English locale keys**

### 1b. Convert Vue components — high priority

- [x] `NavBar.vue` — "Instructor", "Admin", "Account"
- [x] `Home.vue` — welcome text, course cards, due date labels, progress, empty states
- [x] `Login.vue` — form labels, error message map
- [x] `AccountModal.vue` — settings labels, fix hardcoded `'en-US'` date formatting

### 1c. Convert Vue components — problem/submission

- [x] `ProblemSet.vue` — 25+ notification strings, status labels, due date formatting
- [x] `EiplInput.vue` — submission form labels
- [x] `EiplFeedback.vue` — thin wrapper, delegates to children
- [x] `McqInput.vue` — MCQ form labels
- [x] `McqFeedback.vue` — MCQ result text
- [x] `Feedback.vue` — computed property strings (~30 strings)
- [x] Activity inputs: DescriptionInput, DebugFixInput, ProbeableCodeInput, ProbeableSpecInput, PromptInput, RefuteInput, ProbePanel
- [x] Activity feedback: CodeSubmissionFeedback, RefuteFeedback, FeedbackSelector, InputSelector

### 1d. Convert Vue components — admin

- [x] `AdminNavBar.vue` — navigation labels
- [x] `AdminUsers.vue` — table headers, buttons, search, roles
- [x] Admin editor components — EiplProblemEditor, McqProblemEditor, PromptProblemEditor, RefuteProblemEditor, DebugFixProblemEditor, ProbeableCodeProblemEditor, ProbeableSpecProblemEditor
- [x] Admin shared editors — BasicInfoSection, EditorToolbar, ProbeSettingsSection, SegmentationConfigSection, TestCasesSection
- [x] Content management — ContentEditorLayout, CourseEditorShell, CourseList, CourseProblemSetsPage, CourseStudentsPage, ProblemEditorShell, ProblemList, ProblemSetEditorShell, ProblemSetManager, SubmissionDetailPage, SubmissionsPage

### 1e. Convert Vue components — other

- [x] Modal components — CourseEnrollmentModal, ViewSubmissionModal, PyTutorModal
- [x] Privacy components — ConsentForm, PrivacySettings, AccountDeletion, AgeGate, CookieConsent, DataExport
- [x] Instructor components — CourseTeamManager, InstructorDashboard
- [x] UI components — ConfirmDialog, AsyncLoader, AsyncError
- [x] LanguageSwitcher — fixed duplicate imports

**Not converted (intentionally):** PrivacyPolicy.vue, TermsOfService.vue (long-form legal text — separate concern)

### 1f. Verification

- [x] `yarn lint` — 1194 problems (down from 1201 on master; no new errors introduced)
- [ ] `yarn typecheck` — pre-existing failure due to Node.js v25 / vue-tsc incompatibility
- [x] `yarn test` — 372/373 pass (1 pre-existing failure in problemTypeHandlers unrelated to i18n)
- [x] Vitest setup file added (`src/test/setup.ts`) for global i18n plugin injection

---

## Phase 2: Translation Coverage Report + README Badges

- [x] Create `purplex/client/scripts/check-i18n.mjs`
- [x] Create `purplex/client/scripts/generate-i18n-badges.mjs`
- [x] Add `"i18n:check"` and `"i18n:badges"` scripts to `package.json`
- [x] Add i18n report step to `.github/workflows/ci.yml`
- [x] Add "Translation Status" section to `README.md` with badge markers
- [x] Add `i18n-coverage.json` to `.gitignore`

---

## Phase 3: Community Contributor Workflow

- [x] Create `purplex/client/scripts/scaffold-locale.mjs`
- [x] Create `CONTRIBUTING_TRANSLATIONS.md`
- [x] Create `.github/ISSUE_TEMPLATE/new-language.yml`
- [x] Create `.github/PULL_REQUEST_TEMPLATE/translation.md`

---

## Phase 4: AI Content Localization (Backend)

- [x] Thread `language_preference` through `pipeline.py` → `segmentation_service.py`
- [x] Add `language` param to `segment_prompt()` and `_create_segmentation_prompt()`
- [x] Add unit tests for language instruction in segmentation prompt (6 tests)

---

## Phase 5: Sync Existing Locales

- [x] `mi/` — synced to 100% key coverage (917/917), existing Māori translations preserved
- [x] `bn/` — synced to 100% key coverage (917/917), existing Bengali brand name preserved

---

## String Handling Reference

| Pattern | Example | Approach |
|---------|---------|----------|
| Plain template text | `<h1>Welcome!</h1>` | `{{ $t('problems.home.welcome') }}` |
| Interpolation | `{{ n }} completed` | `$t('problems.home.completed', { n })` |
| Plurals | `1 segment / 3 segments` | `$t('feedback.segmentCount', count)` with pipe syntax |
| Computed strings | `return { label: 'Great!' }` | `return { label: t('feedback.comprehension.level.relational') }` |
| Date formatting | `toLocaleDateString('en-US')` | `toLocaleDateString(locale.value)` via `useI18n()` |
| ARIA labels | `aria-label="Progress"` | `:aria-label="$t('common.aria.progress')"` |
| Error maps | `{ 'auth/email-in-use': 'Email taken' }` | `{ 'auth/email-in-use': () => t('auth.errors.emailInUse') }` |
