/**
 * Vitest global setup — injects vue-i18n into every @vue/test-utils mount() call.
 *
 * Components that call useI18n() or use $t() in templates require the i18n plugin.
 * Rather than adding it per-test, we configure it globally here so every mount()
 * has access to the English message catalog.
 */
import { config } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import en from '@/i18n/locales/en'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: { en },
  missingWarn: false,
  fallbackWarn: false,
})

config.global.plugins.push(i18n)
