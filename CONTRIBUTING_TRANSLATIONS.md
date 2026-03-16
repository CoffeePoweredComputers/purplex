# Contributing Translations

Thank you for helping make Purplex accessible to more students and educators! This guide covers everything you need to add or improve a translation.

## How Translation Files Are Structured

Translations live in `purplex/client/src/i18n/locales/`. Each locale has its own directory containing five JSON namespace files:

| File | Content |
|------|---------|
| `common.json` | Brand name, navigation, shared UI labels (buttons, status text) |
| `auth.json` | Login, registration, consent, privacy, account settings |
| `problems.json` | Problem sets, editor, submissions, hints, enrollment |
| `feedback.json` | AI feedback panels, test results, correctness/abstraction metrics |
| `admin.json` | Admin dashboard, user management, instructor views, course teams |

Each file uses nested JSON objects. The key hierarchy maps to dotted paths used in the code (e.g., `common.loading`, `auth.login.title`).

### Key Conventions

- Keys are `camelCase`
- Interpolation variables use single curly braces: `{count}`, `{name}`
- Pluralization is not currently used -- most counts are handled inline

## Step-by-Step: Adding a New Language

### 1. Fork and Clone

```bash
git clone https://github.com/<your-fork>/purplex.git
cd purplex
```

### 2. Scaffold the Locale

From the `purplex/client/` directory:

```bash
node scripts/scaffold-locale.mjs <locale-code>
# Example: node scripts/scaffold-locale.mjs es
```

This creates `src/i18n/locales/<code>/` with copies of the English files. The script will refuse to overwrite an existing locale.

### 3. Translate

Open each of the five JSON files and replace the English values with your translations. Keep the JSON keys unchanged.

**Important:**
- Preserve `{interpolation}` variables exactly as they appear
- Do not translate the brand name "Purplex"
- Keep translations concise -- UI space is limited
- Match the tone of the English text (friendly, clear, direct)

### 4. Register the Locale

Add your locale to the i18n configuration:

1. **`src/i18n/index.ts`** -- Import the locale messages and add them to the `messages` object
2. **`src/i18n/languages.ts`** -- Add an entry with the locale code, English name, and native name

### 5. Test Locally

```bash
cd purplex/client
yarn dev
```

1. Sign in and go to Account Settings
2. Switch the language selector to your new locale
3. Navigate through all major pages: Home, Problem Sets, Editor, Feedback, Admin
4. Verify that strings render correctly and no raw keys (`auth.login.title`) appear

### 6. Check Coverage

```bash
cd purplex/client
yarn i18n:check
```

This prints a coverage report showing any missing or extra keys compared to English. Aim for 100% before submitting.

### 7. Submit a Pull Request

```bash
git checkout -b translation/<locale-code>
git add purplex/client/src/i18n/locales/<locale-code>/
git commit -m "Add <Language> (<code>) translation"
git push origin translation/<locale-code>
```

Open a PR and add the `translation` label. Use the translation PR template if available.

## Style Guide

| Guideline | Example |
|-----------|---------|
| Keep it concise | "Save" not "Save your changes to the server" |
| Preserve variables | `{count} Passing` becomes `{count} Pasando` |
| Match English tone | Friendly and direct, not overly formal |
| No markup in values | Plain text only; HTML lives in components |
| Use native punctuation | Guillemets for French, etc. |

## Improving Existing Translations

If you find a typo or awkward phrasing in an existing locale:

1. Open the relevant JSON file
2. Fix the value (do not change the key)
3. Submit a PR with a description of what changed and why

## Review Process

- Translation PRs are labeled `translation`
- A native or fluent speaker should review the PR when possible
- Maintainers check for structural correctness (valid JSON, no missing keys, interpolation variables intact)
- Once approved, translations are merged into `main` and available in the next deployment

## Questions?

Open an issue with the `translation` label or start a discussion. We are happy to help!
