## Translation PR

**Locale code:** `<code>`
**Language:** <English name> (<native name>)

### Checklist

- [ ] Locale scaffolded with `node scripts/scaffold-locale.mjs <code>`
- [ ] All 5 namespace files translated:
  - [ ] `common.json`
  - [ ] `auth.json`
  - [ ] `problems.json`
  - [ ] `feedback.json`
  - [ ] `admin.json`
- [ ] Locale registered in `src/i18n/index.ts` and `src/i18n/languages.ts`
- [ ] Tested locally -- switched language in Account Settings and verified strings render
- [ ] `yarn i18n:check` reports 100% coverage for this locale
- [ ] No broken `{interpolation}` variables
- [ ] Brand name "Purplex" is not translated
- [ ] JSON is valid (no trailing commas, correct quoting)

### Notes

<!-- Any context about dialect choices, terms you were unsure about, etc. -->
