#!/usr/bin/env node
/**
 * i18n Coverage Report
 *
 * Compares every non-English locale against the English source keys and
 * prints a per-locale coverage summary.  Writes `i18n-coverage.json` to the
 * project root for downstream tooling (badge generation, CI comments, etc.).
 *
 * Usage:  node scripts/check-i18n.mjs          (run from purplex/client/)
 * Exit:   always 0 -- this is a report, not a gate.
 */

import { readdirSync, readFileSync, statSync, writeFileSync } from 'fs';
import { join, resolve } from 'path';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Recursively flatten a nested JSON object into dotted key paths. */
function flattenKeys(obj, prefix = '') {
  const keys = new Set();
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      for (const nested of flattenKeys(v, path)) {
        keys.add(nested);
      }
    } else {
      keys.add(path);
    }
  }
  return keys;
}

/** Read all JSON files in a locale directory and return the merged flat key set. */
function readLocaleKeys(localeDir) {
  const keys = new Set();
  let files;
  try {
    files = readdirSync(localeDir).filter((f) => f.endsWith('.json'));
  } catch {
    return keys;
  }
  for (const file of files) {
    const namespace = file.replace(/\.json$/, '');
    const content = JSON.parse(readFileSync(join(localeDir, file), 'utf-8'));
    for (const key of flattenKeys(content, namespace)) {
      keys.add(key);
    }
  }
  return keys;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const clientRoot = resolve(import.meta.dirname, '..');
const localesDir = join(clientRoot, 'src', 'i18n', 'locales');
const projectRoot = resolve(clientRoot, '..', '..');

// 1. Build the English key set (source of truth).
const enDir = join(localesDir, 'en');
const enKeys = readLocaleKeys(enDir);
const totalKeys = enKeys.size;

if (totalKeys === 0) {
  console.error('No English keys found -- is the locales directory correct?');
  process.exit(0);
}

console.log(`English (en): ${totalKeys} keys\n`);

// 2. Discover non-English locale directories.
const localeDirs = readdirSync(localesDir).filter((name) => {
  if (name === 'en') {return false;}
  return statSync(join(localesDir, name)).isDirectory();
});

if (localeDirs.length === 0) {
  console.log('No additional locales found.');
  process.exit(0);
}

// 3. Compare each locale against English.
const coverage = {};

for (const locale of localeDirs.sort()) {
  const localeKeys = readLocaleKeys(join(localesDir, locale));
  const missing = [...enKeys].filter((k) => !localeKeys.has(k)).sort();
  const extra = [...localeKeys].filter((k) => !enKeys.has(k)).sort();
  const translated = totalKeys - missing.length;
  const percent = Math.round((translated / totalKeys) * 100);

  coverage[locale] = {
    total: totalKeys,
    translated,
    missing: missing.length,
    extra: extra.length,
    percent,
    missingKeys: missing,
    extraKeys: extra,
  };

  console.log(`${locale}: ${percent}% (${translated}/${totalKeys})`);
  if (missing.length > 0) {
    console.log(`  Missing (${missing.length}):`);
    for (const key of missing) {
      console.log(`    - ${key}`);
    }
  }
  if (extra.length > 0) {
    console.log(`  Extra (${extra.length}):`);
    for (const key of extra) {
      console.log(`    + ${key}`);
    }
  }
  console.log();
}

// 4. Write summary JSON.
const summary = {
  generated: new Date().toISOString(),
  sourceLocale: 'en',
  totalKeys,
  locales: {},
};

for (const [locale, data] of Object.entries(coverage)) {
  summary.locales[locale] = {
    translated: data.translated,
    missing: data.missing,
    extra: data.extra,
    percent: data.percent,
  };
}

const outPath = join(projectRoot, 'i18n-coverage.json');
writeFileSync(outPath, JSON.stringify(summary, null, 2) + '\n');
console.log(`Coverage summary written to ${outPath}`);
