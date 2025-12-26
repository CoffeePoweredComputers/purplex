/**
 * Brand transliterations for Purplex across all supported languages.
 * These are kept separate from regular translations as they are:
 * 1. Always needed (loaded in main bundle)
 * 2. Special rendering requirements (fonts, styling)
 */

export const BRAND_TRANSLITERATIONS: Record<string, string> = {
  en: 'Purplex',
  hi: 'पुर्प्लेक्स',     // Devanagari
  bn: 'পার্পলেক্স',     // Bengali
  te: 'పర్ప్లెక్స్',   // Telugu
  pa: 'ਪਰਪਲੈਕਸ',      // Gurmukhi
  mr: 'पुर्प्ळेक्स',     // Devanagari (Marathi-specific ळ)
  kn: 'ಪರ್ಪ್ಲೆಕ್ಸ್',   // Kannada
  ta: 'பர்ப்லெக்ஸ்',   // Tamil
  ja: 'パープレックス',   // Katakana
  zh: '紫翎思',         // Simplified Chinese
  pt: 'Purplex',       // Latin (no change)
  vi: 'Purplex',       // Latin (no change)
  th: 'เพอร์เพล็กซ์',   // Thai
  es: 'Purplex',       // Latin (no change)
  fr: 'Purplex',       // Latin (no change)
  de: 'Purplex',       // Latin (no change)
  mi: 'Panga Poroporo',  // Te Reo Māori - "Purple Puzzle"
};

export const BRAND_LATIN = 'Purplex';

/**
 * Language metadata for UI display
 */
export interface LanguageInfo {
  code: string;
  name: string;
  native: string;
  brand: string;
}

export const SUPPORTED_LANGUAGES: LanguageInfo[] = [
  { code: 'en', name: 'English', native: 'English', brand: 'Purplex' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी', brand: 'पुर्प्लेक्स' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা', brand: 'পার্পলেক্স' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు', brand: 'పర్ప్లెక్స్' },
  { code: 'pa', name: 'Punjabi', native: 'ਪੰਜਾਬੀ', brand: 'ਪਰਪਲੈਕਸ' },
  { code: 'mr', name: 'Marathi', native: 'मराठी', brand: 'पुर्प्ळेक्स' },
  { code: 'kn', name: 'Kannada', native: 'ಕನ್ನಡ', brand: 'ಪರ್ಪ್ಲೆಕ್ಸ್' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்', brand: 'பர்ப்லெக்ஸ்' },
  { code: 'ja', name: 'Japanese', native: '日本語', brand: 'パープレックス' },
  { code: 'zh', name: 'Chinese', native: '中文', brand: '紫翎思' },
  { code: 'pt', name: 'Portuguese', native: 'Português', brand: 'Purplex' },
  { code: 'vi', name: 'Vietnamese', native: 'Tiếng Việt', brand: 'Purplex' },
  { code: 'th', name: 'Thai', native: 'ไทย', brand: 'เพอร์เพล็กซ์' },
  { code: 'es', name: 'Spanish', native: 'Español', brand: 'Purplex' },
  { code: 'fr', name: 'French', native: 'Français', brand: 'Purplex' },
  { code: 'de', name: 'German', native: 'Deutsch', brand: 'Purplex' },
  { code: 'mi', name: 'Māori', native: 'Te Reo Māori', brand: 'Panga Poroporo' },
];

/**
 * Etymology/explanation for brand translations that have meaningful translations
 * (as opposed to pure transliterations)
 */
export interface BrandEtymology {
  translation: string;        // English meaning, e.g., "Purple Puzzle"
  breakdown: string[];        // Breakdown of each word/component
  note?: string;              // Additional cultural context
}

export const BRAND_ETYMOLOGY: Partial<Record<string, BrandEtymology>> = {
  mi: {
    translation: 'Purple Puzzle',
    breakdown: [
      'Panga — puzzles, puzzle-like problems',
      'Poroporo — purple (from a native plant used to make purple dye)'
    ],
    note: 'Poroporo is a traditional te reo Māori word for deep purple, derived from the name of a native plant with purple flowers that was used to make purple-coloured dye.'
  },
  zh: {
    translation: 'Purple Thought Spirit',
    breakdown: [
      '紫 (zǐ) — purple',
      '翎 (líng) — feather/plume',
      '思 (sī) — thought/thinking'
    ]
  }
};

/**
 * Get etymology data for a given locale
 */
export function getEtymology(locale: string): BrandEtymology | undefined {
  return BRAND_ETYMOLOGY[locale];
}

/**
 * Get the brand name for a given locale
 */
export function getBrandName(locale: string): string {
  return BRAND_TRANSLITERATIONS[locale] || BRAND_LATIN;
}

/**
 * Get language info by code
 */
export function getLanguageInfo(code: string): LanguageInfo | undefined {
  return SUPPORTED_LANGUAGES.find(lang => lang.code === code);
}

/**
 * Check if a locale uses non-Latin script for the brand
 */
export function usesNonLatinBrand(locale: string): boolean {
  const latinLocales = ['en', 'pt', 'vi', 'es', 'fr', 'de'];
  return !latinLocales.includes(locale);
}
