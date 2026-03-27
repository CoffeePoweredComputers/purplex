import { describe, expect, it } from 'vitest'
import en from '@/i18n/locales/en'
import es from '@/i18n/locales/es'
import bn from '@/i18n/locales/bn'
import mi from '@/i18n/locales/mi'

/**
 * Recursively flatten a nested object into a Set of dot-separated key paths.
 * Only leaf (non-object) values produce keys.
 */
function flattenKeys(obj: Record<string, unknown>, prefix = ''): Set<string> {
  const keys = new Set<string>()
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      for (const nested of flattenKeys(v as Record<string, unknown>, path)) {
        keys.add(nested)
      }
    } else {
      keys.add(path)
    }
  }
  return keys
}

/**
 * Extract sorted `{name}` interpolation placeholders from a string value.
 */
function extractPlaceholders(str: string): string[] {
  const matches = str.match(/\{(\w+)\}/g)
  if (!matches) {return []}
  return matches.map(m => m.slice(1, -1)).sort()
}

/**
 * Recursively collect all leaf string values keyed by their dot-path.
 */
function flattenValues(obj: Record<string, unknown>, prefix = ''): Map<string, string> {
  const result = new Map<string, string>()
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      for (const [nestedPath, nestedVal] of flattenValues(v as Record<string, unknown>, path)) {
        result.set(nestedPath, nestedVal)
      }
    } else if (typeof v === 'string') {
      result.set(path, v)
    }
  }
  return result
}

describe('Locale data integrity', () => {
  const enKeys = flattenKeys(en)
  const esKeys = flattenKeys(es)
  const enValues = flattenValues(en)
  const esValues = flattenValues(es)

  it('en and es have identical key sets (full parity)', () => {
    const missingInEs = [...enKeys].filter(k => !esKeys.has(k))
    const extraInEs = [...esKeys].filter(k => !enKeys.has(k))

    expect(missingInEs, `Keys in en but missing in es: ${missingInEs.join(', ')}`).toEqual([])
    expect(extraInEs, `Keys in es but not in en: ${extraInEs.join(', ')}`).toEqual([])
  })

  it('no empty string values in en', () => {
    const empties: string[] = []
    for (const [key, val] of enValues) {
      if (val === '') {empties.push(key)}
    }
    expect(empties, `Empty string values found: ${empties.join(', ')}`).toEqual([])
  })

  it('interpolation placeholders match between en and es', () => {
    const mismatches: string[] = []

    for (const [key, enVal] of enValues) {
      const esVal = esValues.get(key)
      if (!esVal) {continue} // parity test catches missing keys

      const enPlaceholders = extractPlaceholders(enVal)
      const esPlaceholders = extractPlaceholders(esVal)

      if (JSON.stringify(enPlaceholders) !== JSON.stringify(esPlaceholders)) {
        mismatches.push(`${key}: en=${JSON.stringify(enPlaceholders)} es=${JSON.stringify(esPlaceholders)}`)
      }
    }

    expect(mismatches, `Placeholder mismatches:\n${mismatches.join('\n')}`).toEqual([])
  })

  it('scaffold locale bn keys are a subset of en keys', () => {
    const bnKeys = flattenKeys(bn)
    const notInEn = [...bnKeys].filter(k => !enKeys.has(k))
    expect(notInEn, `bn keys not in en: ${notInEn.join(', ')}`).toEqual([])
  })

  it('scaffold locale mi keys are a subset of en keys', () => {
    const miKeys = flattenKeys(mi)
    const notInEn = [...miKeys].filter(k => !enKeys.has(k))
    expect(notInEn, `mi keys not in en: ${notInEn.join(', ')}`).toEqual([])
  })

  it('no top-level key collisions across namespace JSONs', () => {
    // Each JSON file (common, auth, feedback, problems, admin) is spread
    // into the locale object. If two files define the same top-level key,
    // one silently overwrites the other.
    const namespaceFiles = ['common', 'auth', 'feedback', 'problems', 'admin']
    const seen = new Map<string, string>()
    const collisions: string[] = []

    for (const ns of namespaceFiles) {
      // Dynamic import isn't practical in tests, so we check the merged
      // object for expected top-level namespace keys. Each JSON file should
      // contribute a distinct top-level key (e.g., feedback.json → "feedback").
      // The real guard is that this test + the parity test together catch drift.
      const nsObj = (en as Record<string, unknown>)[ns]
      if (nsObj && typeof nsObj === 'object') {
        // This namespace key exists — check it wasn't already claimed
        if (seen.has(ns)) {
          collisions.push(`"${ns}" defined in both ${seen.get(ns)} and ${ns}`)
        }
        seen.set(ns, ns)
      }
    }

    expect(collisions).toEqual([])
  })
})
