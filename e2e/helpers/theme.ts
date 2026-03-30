import { Page } from '@playwright/test';

/**
 * Set the theme preference in localStorage before navigation.
 *
 * The FOUC script in index.html (line 13-19) reads `purplex_theme`
 * synchronously before the Vue app mounts and sets `data-theme` on <html>.
 * The useTheme composable (useTheme.ts:8) also reads this key on init.
 *
 * Call this AFTER injectAuth (which navigates to establish the origin)
 * but BEFORE navigating to the target route.
 */
export async function setTheme(
  page: Page,
  theme: 'light' | 'dark',
): Promise<void> {
  await page.evaluate(
    (t) => { localStorage.setItem('purplex_theme', t); },
    theme,
  );
}
