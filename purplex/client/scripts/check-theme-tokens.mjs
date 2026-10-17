#!/usr/bin/env node
/**
 * Theme token check
 *
 * Keeps the light and dark themes in step and catches token typos that
 * would otherwise render silently as `unset`.
 *
 *   1. Parity: the dark and light theme blocks in TOKENS_FILE define the same
 *      names in the same order, hold no theme-independent token (spacing,
 *      radius, type, transitions, layout), and light comes after dark.
 *   2. Resolution: every `var(--x` in src/ and index.html (fallbacks included,
 *      because a fallback hides a typo) has a definition somewhere in src/.
 *   3. Usage: every custom property defined in src/ is read somewhere.
 *   4. Containment: `[data-theme` appears only in TOKENS_FILE.
 *
 * Usage:  node scripts/check-theme-tokens.mjs     (run from purplex/client/)
 * Exit:   1 on any problem not listed in KNOWN_OFFENDERS, or on a
 *         KNOWN_OFFENDERS entry that no longer occurs (delete it).
 */

import { readdirSync, readFileSync } from 'fs';
import { join, relative, resolve } from 'path';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** The single file allowed to define theme colours, relative to the client root. */
const TOKENS_FILE = 'src/styles/tokens.css';

const DARK_SELECTOR = ':root, [data-theme="dark"]';
const LIGHT_SELECTOR = '[data-theme="light"]';

/** Theme-independent tokens; they belong in the plain `:root` block. */
const NON_COLOUR_PREFIXES = ['--spacing-', '--radius-', '--font-', '--transition-', '--max-width-'];

/** Per-instance variables set from inline `:style` bindings, not from CSS. */
const INLINE_VARIABLES = [/^--modal-/, /^--param-count$/, /^--segment-bg-color$/];

/** Prefixes read with a computed name, e.g. getPropertyValue(`--color-category-${n}`). */
const DYNAMIC_PREFIXES = ['--color-category-'];

/**
 * Problems that exist today and are scheduled to be fixed. Each entry is
 * `<check>:<detail>`. Listed problems print as warnings; anything else fails.
 */
const KNOWN_OFFENDERS = [];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const clientRoot = resolve(import.meta.dirname, '..');

function walk(dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(path, out);
    } else if (/\.(vue|css|ts)$/.test(entry.name)) {
      out.push(path);
    }
  }
  return out;
}

/** Blank out block comments, keeping their newlines so line numbers hold. */
const stripComments = (text) =>
  text.replace(/\/\*[\s\S]*?\*\//g, (comment) => comment.replace(/[^\n]/g, ''));

/** Top-level rules of a stylesheet as { selector, body, index }. */
function topLevelRules(css) {
  const rules = [];
  let depth = 0;
  let start = 0;
  let selector = '';
  for (let i = 0; i < css.length; i++) {
    if (css[i] === '{') {
      if (depth === 0) {
        selector = css.slice(start, i).trim().replace(/\s+/g, ' ');
        start = i + 1;
      }
      depth++;
    } else if (css[i] === '}') {
      depth--;
      if (depth === 0) {
        rules.push({ selector, body: css.slice(start, i), index: rules.length });
        start = i + 1;
      }
    }
  }
  return rules;
}

const declaredNames = (css) =>
  [...css.matchAll(/(?<![\w-])(--[\w-]+)\s*:/g)].map((m) => m[1]);


// ---------------------------------------------------------------------------
// Collect
// ---------------------------------------------------------------------------

const problems = [];
const files = [...walk(join(clientRoot, 'src')), join(clientRoot, 'index.html')];

const definitions = new Map(); // name -> first file
const uses = new Map(); // name -> [file:line]
const dataThemeFiles = new Set();

for (const file of files) {
  const rel = relative(clientRoot, file);
  const text = stripComments(readFileSync(file, 'utf-8'));

  for (const name of declaredNames(text)) {
    if (!definitions.has(name)) {definitions.set(name, rel);}
  }

  const lines = text.split('\n');
  lines.forEach((line, i) => {
    for (const m of line.matchAll(/var\(\s*(--[\w-]+)(\$)?/g)) {
      const name = m[2] ? `${m[1]}*` : m[1];
      if (!uses.has(name)) {uses.set(name, []);}
      uses.get(name).push(`${rel}:${i + 1}`);
    }
    for (const m of line.matchAll(/getPropertyValue\(\s*['"](--[\w-]+)['"]/g)) {
      if (!uses.has(m[1])) {uses.set(m[1], []);}
      uses.get(m[1]).push(`${rel}:${i + 1}`);
    }
    if (line.includes('[data-theme') && rel !== TOKENS_FILE) {
      dataThemeFiles.add(rel);
    }
  });
}

// ---------------------------------------------------------------------------
// 1. Parity
// ---------------------------------------------------------------------------

const rules = topLevelRules(stripComments(readFileSync(join(clientRoot, TOKENS_FILE), 'utf-8')));
const dark = rules.find((r) => r.selector === DARK_SELECTOR);
const light = rules.find((r) => r.selector === LIGHT_SELECTOR);

if (!dark || !light) {
  problems.push(`parity:missing ${!dark ? 'dark' : 'light'} block in ${TOKENS_FILE}`);
} else {
  if (light.index < dark.index) {
    problems.push('parity:light block must come after the dark block');
  }
  const darkNames = declaredNames(dark.body);
  const lightNames = declaredNames(light.body);
  for (const [label, names] of [['dark', darkNames], ['light', lightNames]]) {
    const misplaced = names.filter((n) => NON_COLOUR_PREFIXES.some((p) => n.startsWith(p)));
    if (misplaced.length) {
      problems.push(
        `parity:theme-independent tokens in the ${label} block (${misplaced.length}x: ${misplaced.join(', ')})`,
      );
    }
  }
  const darkColour = darkNames.filter((n) => !NON_COLOUR_PREFIXES.some((p) => n.startsWith(p)));
  for (const name of darkColour) {
    if (!lightNames.includes(name)) {problems.push(`parity:missing in light: ${name}`);}
  }
  for (const name of lightNames) {
    if (!darkColour.includes(name)) {problems.push(`parity:missing in dark: ${name}`);}
  }
  const shared = darkColour.filter((n) => lightNames.includes(n));
  const lightShared = lightNames.filter((n) => darkColour.includes(n));
  const firstMismatch = shared.findIndex((n, i) => n !== lightShared[i]);
  if (firstMismatch !== -1) {
    problems.push(
      `parity:order differs at ${shared[firstMismatch]} (light has ${lightShared[firstMismatch]})`,
    );
  }
}

// ---------------------------------------------------------------------------
// 2. Resolution and 3. Usage
// ---------------------------------------------------------------------------

const isInline = (name) => INLINE_VARIABLES.some((re) => re.test(name));

for (const [name, sites] of uses) {
  if (name.endsWith('*')) {
    const prefix = name.slice(0, -1);
    if (!DYNAMIC_PREFIXES.includes(prefix)) {
      problems.push(`undefined:${name} (computed name; add to DYNAMIC_PREFIXES) at ${sites[0]}`);
    }
    continue;
  }
  if (!definitions.has(name) && !isInline(name)) {
    problems.push(`undefined:${name} (${sites.length}x, first at ${sites[0]})`);
  }
}

for (const [name, file] of definitions) {
  if (uses.has(name) || isInline(name)) {continue;}
  if (DYNAMIC_PREFIXES.some((p) => name.startsWith(p))) {continue;}
  problems.push(`unused:${name} (defined in ${file})`);
}

// ---------------------------------------------------------------------------
// 4. Containment
// ---------------------------------------------------------------------------

for (const file of [...dataThemeFiles].sort()) {
  problems.push(`data-theme:${file}`);
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

const key = (p) => p.replace(/ \(.*$/, '');
const known = new Set(KNOWN_OFFENDERS);
const errors = problems.filter((p) => !known.has(key(p)));
const warnings = problems.filter((p) => known.has(key(p)));
const found = new Set(problems.map(key));
const stale = KNOWN_OFFENDERS.filter((k) => !found.has(k));

console.log(`Theme tokens: ${TOKENS_FILE}, ${definitions.size} custom properties defined in src/`);
if (warnings.length) {
  console.log(`\nKnown offenders (${warnings.length}), scheduled for removal:`);
  warnings.forEach((p) => console.log(`  warn  ${p}`));
}
if (stale.length) {
  console.log(`\nFixed but still listed in KNOWN_OFFENDERS (${stale.length}); delete them:`);
  stale.forEach((p) => console.log(`  stale ${p}`));
}
if (errors.length) {
  console.log(`\nProblems (${errors.length}):`);
  errors.forEach((p) => console.log(`  error ${p}`));
}
if (errors.length || stale.length) {
  process.exit(1);
}
console.log('\nOK');
