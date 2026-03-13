import { createI18n, type I18n } from 'vue-i18n';
import en from './locales/en';
import { getBrandName } from './brand';
import { log } from '../utils/logger';

// Type for message schema based on English locale
export type MessageSchema = typeof en;

// Supported locale codes
export type SupportedLocale =
  | 'en' | 'hi' | 'bn' | 'te' | 'pa' | 'mr' | 'kn' | 'ta'
  | 'ja' | 'zh' | 'pt' | 'vi' | 'th' | 'es' | 'fr' | 'de' | 'mi';

// Create i18n instance with Composition API mode
export const i18n = createI18n<[MessageSchema], SupportedLocale>({
  legacy: false, // Use Composition API
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en,
  },
  missingWarn: import.meta.env.DEV,
  fallbackWarn: import.meta.env.DEV,
});

// Track loaded locales to avoid duplicate loading
const loadedLocales = new Set<string>(['en']);

/**
 * Dynamically load locale messages
 */
async function loadLocaleMessages(locale: SupportedLocale): Promise<MessageSchema> {
  if (locale === 'en') {
    return en;
  }

  try {
    const messages = await import(`./locales/${locale}/index.ts`);
    return messages.default;
  } catch {
    // Fallback to English if locale not found
    log.warn(`Locale "${locale}" not found, falling back to English`);
    return en;
  }
}

/**
 * Set the active locale
 * Loads locale messages if not already loaded
 */
export async function setLocale(locale: SupportedLocale): Promise<void> {
  // Load locale if not already loaded
  if (!loadedLocales.has(locale)) {
    const messages = await loadLocaleMessages(locale);
    i18n.global.setLocaleMessage(locale, messages);
    loadedLocales.add(locale);
  }

  // Set the active locale
  i18n.global.locale.value = locale;

  // Update HTML lang attribute for accessibility
  document.documentElement.setAttribute('lang', locale);

  // Update document title with localized brand name
  document.title = getBrandName(locale);

  // Store preference in localStorage for anonymous users
  localStorage.setItem('purplex_locale', locale);
}

/**
 * Get the current locale from storage or browser
 */
export function getStoredLocale(): SupportedLocale {
  // Check localStorage first
  const stored = localStorage.getItem('purplex_locale');
  if (stored && isValidLocale(stored)) {
    return stored as SupportedLocale;
  }

  // Fall back to browser language
  const browserLang = navigator.language.split('-')[0];
  if (isValidLocale(browserLang)) {
    return browserLang as SupportedLocale;
  }

  return 'en';
}

/**
 * Check if a locale code is valid
 */
export function isValidLocale(locale: string): locale is SupportedLocale {
  const validLocales: SupportedLocale[] = [
    'en', 'hi', 'bn', 'te', 'pa', 'mr', 'kn', 'ta',
    'ja', 'zh', 'pt', 'vi', 'th', 'es', 'fr', 'de', 'mi'
  ];
  return validLocales.includes(locale as SupportedLocale);
}

/**
 * Get the i18n instance for use in setup functions
 */
export function useI18nInstance(): I18n<[MessageSchema], object, object, SupportedLocale, false> {
  return i18n as I18n<[MessageSchema], object, object, SupportedLocale, false>;
}
