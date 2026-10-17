import { readFileSync } from 'fs'
import { resolve } from 'path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const STORAGE_KEY = 'purplex_theme'

// Node 25+ ships its own localStorage global that shadows happy-dom's, and
// happy-dom's matchMedia never matches, so both are stubbed explicitly.
let store: Map<string, string>
let storageThrows: boolean
let systemLight: boolean
let mediaListeners: Array<() => void>

const localStorageStub = {
  getItem: vi.fn((key: string) => {
    if (storageThrows) {throw new Error('storage disabled')}
    return store.get(key) ?? null
  }),
  setItem: vi.fn((key: string, value: string) => {
    if (storageThrows) {throw new Error('storage disabled')}
    store.set(key, value)
  }),
}

function matchMediaStub(query: string) {
  const wantsLight = /prefers-color-scheme:\s*light/.test(query)
  return {
    matches: wantsLight ? systemLight : !systemLight,
    media: query,
    addEventListener: (_event: string, handler: () => void) => {
      mediaListeners.push(handler)
    },
  }
}

async function loadUseTheme() {
  vi.resetModules()
  const mod = await import('../useTheme')
  return mod.useTheme
}

const dataTheme = () => document.documentElement.getAttribute('data-theme')

beforeEach(() => {
  store = new Map()
  storageThrows = false
  systemLight = false
  mediaListeners = []
  vi.stubGlobal('localStorage', localStorageStub)
  vi.stubGlobal('matchMedia', matchMediaStub)
  window.matchMedia = matchMediaStub as unknown as typeof window.matchMedia
  localStorageStub.setItem.mockClear()
  document.documentElement.removeAttribute('data-theme')
  document.body.style.colorScheme = ''
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useTheme', () => {
  describe('initial preference', () => {
    it.each([
      ['light', false, 'light'],
      ['dark', true, 'dark'],
      ['auto', true, 'light'],
      ['auto', false, 'dark'],
      ['sepia', true, 'light'],
    ])('stored %s with system light=%s resolves to %s', async (stored, light, expected) => {
      store.set(STORAGE_KEY, stored)
      systemLight = light
      const { theme, effectiveTheme } = (await loadUseTheme())()

      expect(theme.value).toBe(['light', 'dark', 'auto'].includes(stored) ? stored : 'auto')
      expect(effectiveTheme.value).toBe(expected)
      expect(dataTheme()).toBe(expected)
    })

    it('falls back to auto when nothing is stored', async () => {
      systemLight = true
      const { theme, effectiveTheme } = (await loadUseTheme())()

      expect(theme.value).toBe('auto')
      expect(effectiveTheme.value).toBe('light')
    })

    it('falls back to auto when localStorage throws', async () => {
      storageThrows = true
      const { theme, effectiveTheme } = (await loadUseTheme())()

      expect(theme.value).toBe('auto')
      expect(effectiveTheme.value).toBe('dark')
    })
  })

  describe('setTheme', () => {
    it('persists the preference and applies data-theme', async () => {
      const { setTheme, theme, effectiveTheme } = (await loadUseTheme())()

      setTheme('light')

      expect(localStorageStub.setItem).toHaveBeenCalledWith(STORAGE_KEY, 'light')
      expect(theme.value).toBe('light')
      expect(effectiveTheme.value).toBe('light')
      expect(dataTheme()).toBe('light')
      expect(document.body.style.colorScheme).toBe('light')
    })

    it('resolves auto against the system preference', async () => {
      store.set(STORAGE_KEY, 'dark')
      systemLight = true
      const { setTheme, effectiveTheme } = (await loadUseTheme())()

      setTheme('auto')

      expect(store.get(STORAGE_KEY)).toBe('auto')
      expect(effectiveTheme.value).toBe('light')
      expect(dataTheme()).toBe('light')
    })
  })

  describe('system theme listener', () => {
    it('follows the system under auto', async () => {
      const { effectiveTheme } = (await loadUseTheme())()
      expect(effectiveTheme.value).toBe('dark')

      systemLight = true
      mediaListeners.forEach((handler) => handler())

      expect(effectiveTheme.value).toBe('light')
      expect(dataTheme()).toBe('light')
    })

    it('ignores the system under an explicit preference', async () => {
      store.set(STORAGE_KEY, 'dark')
      const { effectiveTheme } = (await loadUseTheme())()

      systemLight = true
      mediaListeners.forEach((handler) => handler())

      expect(effectiveTheme.value).toBe('dark')
      expect(dataTheme()).toBe('dark')
    })

    it('registers one listener however often the composable is called', async () => {
      const useTheme = await loadUseTheme()
      useTheme()
      useTheme()

      expect(mediaListeners).toHaveLength(1)
    })
  })

  describe('editorTheme', () => {
    it.each([
      ['light', 'chrome'],
      ['dark', 'tomorrow_night'],
    ] as const)('maps %s to the %s Ace theme', async (effective, aceTheme) => {
      const { setTheme, editorTheme } = (await loadUseTheme())()

      setTheme(effective)

      expect(editorTheme.value).toBe(aceTheme)
    })
  })
})

// The inline script in index.html sets data-theme before first paint. It
// must agree with useTheme, or the page flashes the wrong theme on load.
describe('index.html FOUC script', () => {
  const html = readFileSync(resolve(__dirname, '../../../index.html'), 'utf-8')
  const inline = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1])

  function runFoucScript(): string | null {
    let attribute: string | null = null
    const documentStub = {
      documentElement: {
        setAttribute: (name: string, value: string) => {
          if (name === 'data-theme') {attribute = value}
        },
      },
    }
    new Function('localStorage', 'matchMedia', 'document', inline[0])(
      localStorageStub,
      matchMediaStub,
      documentStub,
    )
    return attribute
  }

  it('is a single inline script', () => {
    expect(inline).toHaveLength(1)
  })

  it.each([
    ['light', false],
    ['light', true],
    ['dark', false],
    ['dark', true],
    ['auto', false],
    ['auto', true],
    ['sepia', true],
    [null, false],
    [null, true],
  ])('agrees with useTheme for stored %s and system light=%s', async (stored, light) => {
    if (stored !== null) {store.set(STORAGE_KEY, stored)}
    systemLight = light

    const fouc = runFoucScript()
    const { effectiveTheme } = (await loadUseTheme())()

    expect(fouc).toBe(effectiveTheme.value)
  })

  it('agrees with useTheme when localStorage throws', async () => {
    storageThrows = true

    const fouc = runFoucScript()
    const { effectiveTheme } = (await loadUseTheme())()

    expect(fouc).toBe(effectiveTheme.value)
  })
})
