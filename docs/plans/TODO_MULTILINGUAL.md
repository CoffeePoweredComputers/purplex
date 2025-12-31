# Multilingual Support Implementation

## Overview

Purplex multilingual support for 17 languages:
- **Latin**: English (en), Portuguese (pt), Vietnamese (vi), Spanish (es), French (fr), German (de)
- **Indic**: Hindi (hi), Bengali (bn), Telugu (te), Punjabi (pa), Marathi (mr), Kannada (kn), Tamil (ta)
- **East Asian**: Japanese (ja), Chinese (zh), Thai (th)
- **Pacific**: Maori (mi)

---

## Stage 1: Infrastructure Verification

### 1.1 Database
- [x] Verify migration exists for `UserProfile.language_preference` field
  - Migration: `users_app/migrations/0002_add_language_preference.py`
- [ ] Verify migration has been applied to all environments (dev, staging, prod)
- [ ] Test that language_preference persists correctly via Django admin
- [ ] Update migration to include Maori (mi) - currently missing from migration choices

### 1.2 API Endpoints
- [x] Verify `PATCH /api/user/me/language/` endpoint works
  - Implemented in `LanguagePreferenceView` in `user_views.py`
- [x] Verify `GET /api/user/me/` returns `language_preference`
  - Confirmed in `UserRoleView`
- [x] Verify `GET /api/auth/status/` returns `language_preference`
  - Confirmed in `AuthStatusView`
- [ ] Add API tests for language preference endpoints

### 1.3 Frontend Locale Persistence
- [x] Verify localStorage persistence for anonymous users
  - Implemented in `i18n/index.ts` via `setLocale()` storing to `purplex_locale`
- [x] Verify backend sync for authenticated users
  - `LanguageSwitcher.vue` calls `PATCH /api/user/me/language/` on change
- [x] Verify locale restoration on app load (main.ts `initializeLocale`)
  - Confirmed in `main.ts` lines 33-39
- [x] Verify locale syncs when user logs in (auth store `checkAuthState`)
  - Confirmed in `auth.module.ts` - calls `setLocale()` after fetching user data

### 1.4 Font Loading
- [ ] Add Google Fonts import for Noto Sans family:
  - Currently only Exo 2 is loaded in `index.html`
  - Need to add: Noto Sans (base), Noto Sans Devanagari (hi, mr), Noto Sans Bengali (bn),
    Noto Sans Telugu (te), Noto Sans Gurmukhi (pa), Noto Sans Kannada (kn),
    Noto Sans Tamil (ta), Noto Sans JP (ja), Noto Sans SC (zh), Noto Sans Thai (th)
- [x] CSS fallback configured in `NavBar.vue` for non-Latin scripts
  - Uses system font stack with Noto Sans variants as fallback
- [ ] Verify all scripts render correctly in navbar brand
- [ ] Verify all scripts render correctly in language switcher dropdown

---

## Stage 2: Frontend Translation Coverage

### 2.1 Audit & Inventory
- [ ] Audit all Vue components for hardcoded English strings
- [ ] Create inventory of strings needing translation
- [ ] Categorize by namespace (common, auth, problems, feedback, admin)

### 2.2 Core Components (High Priority)
- [ ] `NavBar.vue` - nav items still hardcoded: "Instructor", "Admin", "Account"
- [ ] `AccountModal.vue` - hardcoded: "Account Settings", "Account Type", "Member Since", "Sign Out", "User"
- [x] `LanguageSwitcher.vue` - uses `$t('auth.account.language')` and `$t('auth.account.languageDescription')`
- [ ] `LoginPage.vue` - needs audit for hardcoded strings
- [ ] `Home.vue` - hardcoded: "Welcome to Purplex!", "Get started by joining...", "Join a Course",
      "completed", "No problems yet", "No problem sets available...", "Review", "Continue", "Start"

### 2.3 Problem/Submission Components
- [ ] `ProblemSet.vue` - status labels, instructions
- [ ] `ProblemCard.vue` - status badges, labels
- [ ] `EiplInput.vue` - placeholder text, submit button
- [ ] `EiplFeedback.vue` - all feedback labels and sections
- [ ] `McqInput.vue` - labels, buttons
- [ ] `McqFeedback.vue` - result text
- [ ] `HintPanel.vue` - hint labels, buttons

### 2.4 Admin Components
- [ ] `AdminLayout.vue` - navigation labels
- [ ] `AdminUsers.vue` - table headers, buttons
- [ ] `AdminProblems.vue` - all labels
- [ ] `AdminProblemEditor.vue` - form labels, buttons
- [ ] `AdminSubmissions.vue` - table headers, status labels

### 2.5 Shared Components
- [ ] All modal components - titles, buttons
- [ ] Error messages and toast notifications
- [ ] Loading states
- [ ] Empty states

---

## Stage 3: Translation Content

### 3.1 English Locale Completion
- [x] Review `en/common.json` - has brand, nav, common action strings
- [x] Review `en/auth.json` - has login form, errors, account settings strings
- [x] Review `en/problems.json` - has status, editor, submission, hints strings
- [x] Review `en/feedback.json` - has comprehension, correctness, tests strings
- [x] Review `en/admin.json` - has nav, users, problems management strings
- [ ] Add missing strings identified in Stage 2 audit

### 3.2 Translation Process
- [ ] Export English strings for translation
- [ ] Determine translation source (professional, community, AI-assisted)
- [ ] Create translation guidelines document (tone, terminology)

### 3.3 Populate Locale Files
Locale file status:
- [x] `mi/` - Maori - FULLY TRANSLATED (common, auth, problems, feedback, admin)
- [ ] `bn/` - Bengali - placeholder only (brand translated, rest English)
- [ ] `hi/` - Hindi - not created
- [ ] `te/` - Telugu - not created
- [ ] `pa/` - Punjabi - not created
- [ ] `mr/` - Marathi - not created
- [ ] `kn/` - Kannada - not created
- [ ] `ta/` - Tamil - not created
- [ ] `ja/` - Japanese - not created
- [ ] `zh/` - Chinese (Simplified) - not created
- [ ] `pt/` - Portuguese - not created
- [ ] `vi/` - Vietnamese - not created
- [ ] `th/` - Thai - not created
- [ ] `es/` - Spanish - not created
- [ ] `fr/` - French - not created
- [ ] `de/` - German - not created

---

## Stage 4: AI Integration

### 4.1 Feedback Generation
- [ ] Verify `get_feedback_message()` is called in grading service
- [ ] Verify user's language_preference is passed to feedback generation
- [ ] Update `purplex/submissions/grading_service.py` to use localized templates
- [ ] Update `purplex/problems_app/services/segmentation_service.py` for localized comprehension feedback

### 4.2 EiPL Understanding
- [ ] Verify OpenAI prompts handle non-English input
- [ ] Test EiPL submissions in various languages
- [ ] Consider adding language hint to AI prompts based on user preference

### 4.3 AI Response Localization
- [ ] Update AI system prompts to respond in user's preferred language
- [ ] Add language instruction to code generation prompts
- [ ] Add language instruction to feedback/hint generation prompts

### 4.4 Template Expansion
- [ ] Add more feedback templates to `FEEDBACK_TEMPLATES` as needed
- [ ] Add hint templates for localized hints
- [ ] Add error message templates

---

## Stage 5: Testing & QA

### 5.1 Unit Tests
- [ ] Test `language_utils.py` functions (file does not exist - referenced in old completed section)
- [ ] Test language preference API endpoints
- [ ] Test vue-i18n setup and locale switching
- [ ] Test brand transliteration functions

### 5.2 Integration Tests
- [ ] Test full flow: change language -> persists -> reload -> restored
- [ ] Test authenticated user language sync
- [ ] Test anonymous user localStorage persistence

### 5.3 Visual QA (Per Language)
For each language, verify:
- [ ] Navbar brand renders correctly (no clipping)
- [ ] Language switcher displays native names correctly
- [ ] All translated text displays properly
- [ ] No layout breaks from longer/shorter translations
- [ ] Document title updates correctly

### 5.4 AI QA
- [ ] Test EiPL submission in Hindi
- [ ] Test EiPL submission in Japanese
- [ ] Test EiPL submission in Chinese
- [ ] Verify AI feedback returned in correct language

---

## Stage 6: Polish & Accessibility

### 6.1 Loading States
- [ ] Add loading indicator during async locale load
- [x] Handle locale load failures gracefully
  - Implemented in `i18n/index.ts` - logs warning and falls back to English
- [x] Fallback to English on locale load error
  - Confirmed in `loadLocaleMessages()` catch block

### 6.2 Accessibility
- [x] Verify `lang` attribute updates on `<html>` element
  - Implemented in `setLocale()`: `document.documentElement.setAttribute('lang', locale)`
- [ ] Test with screen readers in multiple languages
- [ ] Ensure language switcher is keyboard accessible
- [ ] Add ARIA labels where needed

### 6.3 Performance
- [x] Verify lazy loading works (non-English locales not in main bundle)
  - Implemented via dynamic `import()` in `loadLocaleMessages()`
- [ ] Consider preloading common secondary locales
- [ ] Measure bundle size impact

### 6.4 Edge Cases
- [x] Handle missing translation keys gracefully
  - vue-i18n configured with `fallbackLocale: 'en'`
  - Warnings only shown in dev mode via `missingWarn`/`fallbackWarn`
- [x] Handle unsupported browser language detection
  - `getStoredLocale()` validates with `isValidLocale()` before using
- [ ] Handle language preference mismatch (user changes on another device)

---

## Stage 7: Documentation

- [ ] Update README with multilingual support info
- [ ] Document how to add a new language
- [ ] Document translation contribution process
- [ ] Add inline code comments for i18n patterns

---

## Completed Summary

### Infrastructure
- [x] UserProfile.language_preference field added (migration 0002)
- [x] LanguageChoice enum with 17 languages (includes Maori)
- [x] Django LANGUAGES setting configured
- [x] API endpoints for language preference (GET /user/me/, PATCH /user/me/language/, POST /auth/status/)

### Frontend Core
- [x] vue-i18n configured with lazy loading and Composition API
- [x] `brand.ts` with transliterations for all 17 languages (including etymology for mi, zh)
- [x] LanguageSwitcher component with backend sync
- [x] NavBar dynamic brand name with non-Latin script styling
- [x] Document title updates on locale change
- [x] localStorage persistence for anonymous users
- [x] Locale sync on authenticated user login
- [x] HTML lang attribute updates

### Locale Files
- [x] English locale files structure (common, auth, feedback, problems, admin)
- [x] Bengali locale placeholder files created (brand only, rest English)
- [x] Maori locale fully translated (all 5 namespace files)

---

## Issues to Address

1. **Migration out of sync**: The database migration (0002) is missing Maori (mi) and Bengali (bn) in choices
2. **No `language_utils.py`**: Referenced in completed section but file does not exist
3. **Hardcoded strings**: NavBar.vue, AccountModal.vue, Home.vue have untranslated English strings
4. **Missing fonts**: Noto Sans family not loaded for non-Latin scripts - only fallback to system fonts
5. **Missing locale files**: 14 of 17 languages have no locale files created

---

## Notes

- **LTR only**: No RTL languages currently supported (Arabic, Hebrew, Urdu)
- **Feedback style**: Template-based (pre-written translations, not AI-generated per request)
- **Translation source**: User will provide translations
- **Maori addition**: Language added post-initial planning, includes meaningful translation "Panga Poroporo" (Purple Puzzle)
