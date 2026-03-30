import { test, expect } from '@playwright/test';
import { injectAuth } from './helpers/auth';
import { setTheme } from './helpers/theme';
import * as fs from 'fs';
import * as path from 'path';

// ---------------------------------------------------------------------------
// Route definitions — every static route in router.ts, grouped by auth level
// ---------------------------------------------------------------------------

type AuthRole = 'student' | 'instructor' | 'admin' | null;

interface RouteEntry {
  path: string;
  auth: AuthRole;
}

const ROUTES: Record<string, RouteEntry> = {
  // Public (no auth required)
  'login':              { path: '/', auth: null },
  'privacy':            { path: '/privacy', auth: 'student' },
  'terms':              { path: '/terms', auth: 'student' },

  // Student (requiresAuth)
  'home':               { path: '/home', auth: 'student' },
  'privacy-settings':   { path: '/settings/privacy', auth: 'student' },

  // Instructor
  'instructor-dashboard':    { path: '/instructor', auth: 'instructor' },
  'instructor-courses':      { path: '/instructor/courses', auth: 'instructor' },
  'instructor-course-new':   { path: '/instructor/courses/new', auth: 'instructor' },
  'instructor-problems':     { path: '/instructor/problems', auth: 'instructor' },
  'instructor-problem-new':  { path: '/instructor/problems/new', auth: 'instructor' },
  'instructor-problem-sets': { path: '/instructor/problem-sets', auth: 'instructor' },
  'instructor-ps-new':       { path: '/instructor/problem-sets/new', auth: 'instructor' },

  // Admin
  'admin-users':        { path: '/admin/users', auth: 'admin' },
  'admin-problems':     { path: '/admin/problems', auth: 'admin' },
  'admin-problem-sets': { path: '/admin/problem-sets', auth: 'admin' },
  'admin-submissions':  { path: '/admin/submissions', auth: 'admin' },
  'admin-courses':      { path: '/admin/courses', auth: 'admin' },
  'admin-course-new':   { path: '/admin/courses/new', auth: 'admin' },
};

// Data-dependent routes — uncomment after seeding the dev database.
// These require the backend to be running with test data loaded.
//
// 'course-detail':              { path: '/courses/ENGGEN131', auth: 'student' },
// 'course-problem-set':         { path: '/courses/ENGGEN131/problem-set/demo-problem-set', auth: 'student' },
// 'instructor-course-overview': { path: '/instructor/courses/ENGGEN131', auth: 'instructor' },
// 'instructor-course-students': { path: '/instructor/courses/ENGGEN131/students', auth: 'instructor' },
// 'instructor-course-subs':     { path: '/instructor/courses/ENGGEN131/submissions', auth: 'instructor' },
// 'instructor-course-ps':       { path: '/instructor/courses/ENGGEN131/problem-sets', auth: 'instructor' },
// 'admin-course-students':      { path: '/admin/courses/ENGGEN131/students', auth: 'admin' },
// 'admin-course-ps':            { path: '/admin/courses/ENGGEN131/problem-sets', auth: 'admin' },

const THEMES = ['dark', 'light'] as const;
const SCREENSHOT_ROOT = path.resolve(__dirname, '..', 'visual-tests', 'screenshots');

// ---------------------------------------------------------------------------
// Main audit: screenshot every route × every theme
// ---------------------------------------------------------------------------

for (const theme of THEMES) {
  test.describe(`Theme: ${theme}`, () => {
    for (const [name, route] of Object.entries(ROUTES)) {
      test(`${name} (${route.path})`, async ({ page }) => {
        // Ensure output directory exists
        const dir = path.join(SCREENSHOT_ROOT, theme);
        fs.mkdirSync(dir, { recursive: true });

        // 1. Inject auth (if needed) — this navigates to origin first
        if (route.auth) {
          await injectAuth(page, route.auth);
        } else {
          // Still need to establish origin for theme localStorage
          await page.goto('/', { waitUntil: 'commit' });
          // Dismiss cookie banner for clean screenshots
          await page.evaluate(() => {
            localStorage.setItem('purplex_cookie_consent', 'accepted');
          });
        }

        // 2. Set theme
        await setTheme(page, theme);

        // 3. Navigate to the target route
        await page.goto(route.path, {
          waitUntil: 'networkidle',
          timeout: 15_000,
        });

        // 4. Let animations and transitions settle
        await page.waitForTimeout(500);

        // 5. Take full-page screenshot
        const screenshotPath = path.join(dir, `${name}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });

        // Sanity check: file was actually written
        expect(fs.existsSync(screenshotPath)).toBe(true);
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Special cases
// ---------------------------------------------------------------------------

test.describe('Special cases', () => {
  for (const theme of THEMES) {
    test(`cookie-consent-banner — ${theme}`, async ({ page }) => {
      const dir = path.join(SCREENSHOT_ROOT, theme);
      fs.mkdirSync(dir, { recursive: true });

      await page.goto('/', { waitUntil: 'commit' });

      // Explicitly remove cookie consent so the banner is visible
      await page.evaluate(() => {
        localStorage.removeItem('purplex_cookie_consent');
        localStorage.setItem('purplex_theme', 'placeholder');
      });
      await setTheme(page, theme);

      await page.goto('/', { waitUntil: 'networkidle', timeout: 15_000 });
      await page.waitForTimeout(500);

      await page.screenshot({
        path: path.join(dir, 'cookie-consent-banner.png'),
        fullPage: true,
      });
    });

    test(`account-modal — ${theme}`, async ({ page }) => {
      const dir = path.join(SCREENSHOT_ROOT, theme);
      fs.mkdirSync(dir, { recursive: true });

      await injectAuth(page, 'student');
      await setTheme(page, theme);

      await page.goto('/home', {
        waitUntil: 'networkidle',
        timeout: 15_000,
      });
      await page.waitForTimeout(500);

      // Open the account modal via the nav bar button
      const accountBtn = page.locator('button.account-item');
      await accountBtn.click();
      await page.waitForSelector('#account-modal-title', { timeout: 3_000 });
      await page.waitForTimeout(300);

      await page.screenshot({
        path: path.join(dir, 'account-modal.png'),
        fullPage: true,
      });
    });
  }
});
