import { defineConfig, devices } from '@playwright/test';

const chromeDesktop = {
  ...devices['Desktop Chrome'],
  viewport: { width: 1440, height: 900 },
};

export default defineConfig({
  testDir: './e2e',
  outputDir: './visual-tests/screenshots',

  // No parallel locally — sequential is fine for a screenshot walkthrough
  // CI overrides with --workers=2
  fullyParallel: false,
  workers: 1,

  // No retries — if a page fails to load, we want to know immediately
  retries: 0,

  // API calls through Celery can be slow
  expect: { timeout: 10_000 },

  // HTML reporter for side-by-side review
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    actionTimeout: 5_000,
    trace: 'retain-on-failure',
    screenshot: 'off', // we take manual screenshots
  },

  projects: [
    {
      name: 'smoke',
      testMatch: /smoke-tests|visual-theme/,
      use: chromeDesktop,
    },
    {
      name: 'auth',
      testDir: './e2e/auth',
      use: chromeDesktop,
    },
    {
      name: 'admin',
      testDir: './e2e/admin',
      use: chromeDesktop,
    },
    {
      name: 'instructor',
      testDir: './e2e/instructor',
      use: chromeDesktop,
    },
    {
      name: 'student',
      testDir: './e2e/student',
      use: chromeDesktop,
    },
    {
      name: 'ui',
      testDir: './e2e/ui',
      use: chromeDesktop,
    },
    {
      name: 'privacy',
      testDir: './e2e/privacy',
      use: chromeDesktop,
    },
    {
      name: 'permissions',
      testDir: './e2e/permissions',
      use: chromeDesktop,
    },
  ],

  // No webServer — start services manually via ./start.sh
});
