#!/usr/bin/env node
/**
 * Scaffold a new locale directory for translation.
 *
 * Copies every English JSON file into a new locale directory and generates
 * the barrel `index.ts` so the locale can be imported by vue-i18n.
 *
 * Usage:  node scripts/scaffold-locale.mjs <locale-code>
 *         e.g.  node scripts/scaffold-locale.mjs es
 *
 * The script refuses to overwrite an existing locale directory.
 */

import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  writeFileSync,
} from 'fs';
import { join, resolve } from 'path';

// ---------------------------------------------------------------------------
// Validate arguments
// ---------------------------------------------------------------------------

const localeCode = process.argv[2];

if (!localeCode) {
  console.error('Usage: node scripts/scaffold-locale.mjs <locale-code>');
  console.error('  e.g. node scripts/scaffold-locale.mjs es');
  process.exit(1);
}

if (!/^[a-z]{2,3}(-[A-Z]{2})?$/.test(localeCode)) {
  console.error(
    `Invalid locale code "${localeCode}". Expected ISO 639-1 format (e.g., es, pt-BR).`,
  );
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

const clientRoot = resolve(import.meta.dirname, '..');
const localesDir = join(clientRoot, 'src', 'i18n', 'locales');
const enDir = join(localesDir, 'en');
const targetDir = join(localesDir, localeCode);

// ---------------------------------------------------------------------------
// Guard against overwrite
// ---------------------------------------------------------------------------

if (existsSync(targetDir)) {
  console.error(
    `Locale directory already exists: ${targetDir}\nRemove it first if you want to re-scaffold.`,
  );
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Copy English JSON files
// ---------------------------------------------------------------------------

const jsonFiles = readdirSync(enDir).filter((f) => f.endsWith('.json'));

if (jsonFiles.length === 0) {
  console.error('No English JSON files found. Is the en/ directory correct?');
  process.exit(1);
}

mkdirSync(targetDir, { recursive: true });

for (const file of jsonFiles) {
  const content = readFileSync(join(enDir, file), 'utf-8');
  writeFileSync(join(targetDir, file), content);
  console.log(`  Created ${localeCode}/${file}`);
}

// ---------------------------------------------------------------------------
// Generate index.ts barrel
// ---------------------------------------------------------------------------

const enIndex = readFileSync(join(enDir, 'index.ts'), 'utf-8');
writeFileSync(join(targetDir, 'index.ts'), enIndex);
console.log(`  Created ${localeCode}/index.ts`);

// ---------------------------------------------------------------------------
// Next steps
// ---------------------------------------------------------------------------

console.log(`
Locale "${localeCode}" scaffolded successfully!

Next steps:
  1. Translate the JSON files in src/i18n/locales/${localeCode}/
     - ${jsonFiles.join('\n     - ')}
  2. Register the locale in src/i18n/index.ts (add the import + messages entry)
  3. Add the locale to the language selector in src/i18n/languages.ts
  4. Test locally: switch language in Account Settings and verify strings render
  5. Run "yarn i18n:check" to confirm 100% coverage
  6. Submit a PR with the "translation" label

See CONTRIBUTING_TRANSLATIONS.md for full guidelines.
`);
