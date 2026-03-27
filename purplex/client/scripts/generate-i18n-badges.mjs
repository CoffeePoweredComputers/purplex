#!/usr/bin/env node
/**
 * Generate shields.io badge URLs for i18n coverage and inject them into
 * the project README.md between marker comments.
 *
 * Reads:  <project-root>/i18n-coverage.json  (produced by check-i18n.mjs)
 * Writes: <project-root>/README.md           (between i18n-badges markers)
 *
 * Usage:  node scripts/generate-i18n-badges.mjs   (run from purplex/client/)
 */

import { existsSync, readFileSync, writeFileSync } from 'fs';
import { join, resolve } from 'path';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const LOCALE_LABELS = {
  mi: 'Te Reo M\u0101ori',
  bn: 'Bengali',
  es: 'Spanish',
  fr: 'French',
  de: 'German',
  pt: 'Portuguese',
  ja: 'Japanese',
  ko: 'Korean',
  zh: 'Chinese',
  hi: 'Hindi',
  ar: 'Arabic',
};

function badgeColor(percent) {
  if (percent >= 100) {return 'brightgreen';}
  if (percent >= 50) {return 'yellow';}
  if (percent >= 1) {return 'red';}
  return 'lightgrey';
}

function badgeUrl(locale, percent) {
  const label = LOCALE_LABELS[locale] || locale;
  const encodedLabel = encodeURIComponent(label);
  const message = encodeURIComponent(`${percent}%`);
  const color = badgeColor(percent);
  return `https://img.shields.io/badge/${encodedLabel}-${message}-${color}`;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const projectRoot = resolve(import.meta.dirname, '..', '..', '..');
const coveragePath = join(projectRoot, 'i18n-coverage.json');
const readmePath = join(projectRoot, 'README.md');

if (!existsSync(coveragePath)) {
  console.error(
    `${coveragePath} not found. Run "yarn i18n:check" first to generate it.`,
  );
  process.exit(1);
}

if (!existsSync(readmePath)) {
  console.error(`${readmePath} not found.`);
  process.exit(1);
}

const coverage = JSON.parse(readFileSync(coveragePath, 'utf-8'));
const locales = Object.entries(coverage.locales).sort(
  ([, a], [, b]) => b.percent - a.percent,
);

// Build badge markdown lines.
const badges = locales.map(
  ([locale, data]) =>
    `[![${LOCALE_LABELS[locale] || locale} translation](${badgeUrl(locale, data.percent)})](purplex/client/src/i18n/locales/${locale}/)`,
);

const badgeBlock = badges.join('\n');

// Inject into README between markers.
const START_MARKER = '<!-- i18n-badges:start -->';
const END_MARKER = '<!-- i18n-badges:end -->';

let readme = readFileSync(readmePath, 'utf-8');
const startIdx = readme.indexOf(START_MARKER);
const endIdx = readme.indexOf(END_MARKER);

if (startIdx === -1 || endIdx === -1) {
  console.error(
    `Could not find badge markers in README.md.\nExpected:\n  ${START_MARKER}\n  ${END_MARKER}`,
  );
  process.exit(1);
}

const before = readme.slice(0, startIdx + START_MARKER.length);
const after = readme.slice(endIdx);
readme = `${before}\n${badgeBlock}\n${after}`;

writeFileSync(readmePath, readme);
console.log(`Updated ${readmePath} with ${locales.length} locale badge(s).`);
