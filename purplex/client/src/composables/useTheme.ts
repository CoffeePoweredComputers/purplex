import { computed, readonly, ref } from 'vue'

export type ThemePreference = 'light' | 'dark' | 'auto'
export type EffectiveTheme = 'light' | 'dark'

const STORAGE_KEY = 'purplex_theme'

function getStoredPreference(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'auto') {
    return stored
  }
  return 'auto'
}

function getSystemTheme(): EffectiveTheme {
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

function resolveTheme(preference: ThemePreference): EffectiveTheme {
  return preference === 'auto' ? getSystemTheme() : preference
}

function applyTheme(effective: EffectiveTheme): void {
  document.documentElement.setAttribute('data-theme', effective)
  document.body.style.colorScheme = effective
}

// Module-level singleton state
const theme = ref<ThemePreference>(getStoredPreference())
const effectiveTheme = ref<EffectiveTheme>(resolveTheme(theme.value))

let initialized = false

function setTheme(preference: ThemePreference): void {
  theme.value = preference
  localStorage.setItem(STORAGE_KEY, preference)

  effectiveTheme.value = resolveTheme(preference)
  applyTheme(effectiveTheme.value)
}

function initialize(): void {
  if (initialized) {
    return
  }
  initialized = true

  // Apply immediately
  applyTheme(effectiveTheme.value)

  // Listen for OS theme changes (matters when preference is 'auto')
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  const handler = () => {
    if (theme.value === 'auto') {
      effectiveTheme.value = getSystemTheme()
      applyTheme(effectiveTheme.value)
    }
  }
  mediaQuery.addEventListener('change', handler)
}

/**
 * Composable for managing the application theme (light/dark/auto).
 *
 * Module-level singleton — all components share the same reactive state.
 * Call once in App.vue setup to initialize the media query listener.
 */
export function useTheme() {
  initialize()

  const editorTheme = computed(() =>
    effectiveTheme.value === 'light' ? 'chrome' : 'tomorrow_night'
  )

  return {
    theme: readonly(theme),
    effectiveTheme: computed(() => effectiveTheme.value),
    editorTheme,
    setTheme,
  }
}
