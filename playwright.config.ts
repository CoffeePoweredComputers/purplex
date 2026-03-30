import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  outputDir: './visual-tests/screenshots',

  // No parallel — sequential is fine for a screenshot walkthrough
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
    trace: 'on-first-retry',
    screenshot: 'off', // we take manual screenshots
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
      },
    },
  ],

  // No webServer — start services manually via ./start.sh
});
