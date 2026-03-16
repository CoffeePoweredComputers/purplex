/**
 * Vitest global setup — injects vue-i18n into every @vue/test-utils mount() call.
 *
 * Components that call useI18n() or use $t() in templates require the i18n plugin.
 * Rather than adding it per-test, we configure it globally here so every mount()
 * has access to the English message catalog.
 */
import { createApp, defineComponent } from 'vue'
import { config } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import en from '@/i18n/locales/en'

export const testI18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: { en },
  missingWarn: false,
  fallbackWarn: false,
})

config.global.plugins.push(testI18n)

/**
 * Run a composable inside a temporary Vue app with i18n installed.
 * Use this when testing composables that call useI18n().
 */
export function withSetup<T>(composable: () => T): T {
  let result!: T
  const app = createApp(defineComponent({
    setup() {
      result = composable()
      return () => null
    },
  }))
  app.use(testI18n)
  app.mount(document.createElement('div'))
  return result
}
