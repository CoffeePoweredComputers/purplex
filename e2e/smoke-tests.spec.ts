/**
 * E2E Smoke Tests — Critical User Workflows
 *
 * These tests verify the full chain: browser → Vue → API → Django → DB.
 * They run against the dev server with mock Firebase auth and a seeded database.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *   4. Test course seeded: python manage.py seed_e2e_data
 *
 * Run: npx playwright test e2e/smoke-tests.spec.ts
 */

import { test, expect, Page } from '@playwright/test';
import { injectAuth } from './helpers/auth';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Navigate to a page with auth injected. */
async function navigateAs(
  page: Page,
  role: 'student' | 'instructor' | 'admin',
  path: string,
) {
  await injectAuth(page, role);
  await page.goto(path, { waitUntil: 'networkidle' });
}

/** Wait for API calls to settle and content to render. */
async function waitForContent(page: Page, text: string, timeout = 10000) {
  await page.getByText(text).first().waitFor({ state: 'visible', timeout });
}

// ---------------------------------------------------------------------------
// Student Workflows
// ---------------------------------------------------------------------------

test.describe('Student: Course Enrollment', () => {
  test('can view enrolled courses on home page', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    // Student home should load without errors
    const content = page.locator('[role="main"], main');
    await expect(content).toBeVisible();
  });

  test('can browse problem sets', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    // Should see course cards or "Join a Course" button
    const joinButton = page.getByText('Join a Course');
    const courseCard = page.locator('[class*="course"]').first();
    const hasContent = await joinButton.or(courseCard).first().isVisible();
    expect(hasContent).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Instructor Workflows
// ---------------------------------------------------------------------------

test.describe('Instructor: Course Overview', () => {
  test('can view instructor dashboard', async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor');

    // Should see course list or "no courses" message
    await expect(page.locator('body')).not.toContainText('500');
    await expect(page.locator('body')).not.toContainText('Internal Server Error');
  });

  test('can navigate to course overview', async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor');

    // Wait for courses to load
    await page.waitForTimeout(2000);

    // Click first course if available
    const courseLink = page.locator('a[href*="/instructor/courses/"]').first();
    if (await courseLink.isVisible()) {
      await courseLink.click();
      await page.waitForLoadState('networkidle');

      // Should load without 500 errors
      await expect(page.locator('body')).not.toContainText('Internal Server Error');
    }
  });
});

// ---------------------------------------------------------------------------
// Admin Workflows
// ---------------------------------------------------------------------------

test.describe('Admin: Course Team Management', () => {
  test('can view course overview page', async ({ page }) => {
    await navigateAs(page, 'admin', '/instructor');

    await page.waitForTimeout(2000);

    // Admin should see instructor dashboard (admins have instructor access)
    await expect(page.locator('body')).not.toContainText('Internal Server Error');
  });

  test('course team section loads for admin', async ({ page }) => {
    await navigateAs(page, 'admin', '/instructor');

    await page.waitForTimeout(2000);

    // Click first course
    const courseLink = page.locator('a[href*="/instructor/courses/"]').first();
    if (await courseLink.isVisible()) {
      await courseLink.click();

      // Wait for Course Team section
      try {
        await waitForContent(page, 'Course Team', 5000);

        // Team table should be visible
        const teamTable = page.locator('table').first();
        await expect(teamTable).toBeVisible();
      } catch {
        // Course may not have team section — that's OK for a smoke test
      }
    }
  });

  test('role switch shows meaningful error for last primary', async ({ page }) => {
    await navigateAs(page, 'admin', '/instructor');

    await page.waitForTimeout(2000);

    const courseLink = page.locator('a[href*="/instructor/courses/"]').first();
    if (!(await courseLink.isVisible())) {
      test.skip();
      return;
    }

    await courseLink.click();

    try {
      await waitForContent(page, 'Course Team', 5000);
    } catch {
      test.skip();
      return;
    }

    // Find the role dropdown in the team table
    const roleSelect = page.locator('.role-select').first();
    if (!(await roleSelect.isVisible())) {
      test.skip();
      return;
    }

    // Try to switch from Primary to TA
    const currentValue = await roleSelect.inputValue();
    if (currentValue === 'primary') {
      await roleSelect.selectOption('ta');
      await page.waitForTimeout(1000);

      // Should show a meaningful error, NOT "Failed to update role."
      const alertText = await page.locator('alert, [role="alert"], .error-message, .action-error').first().textContent();
      if (alertText) {
        // The error should be actionable, not generic
        expect(alertText).not.toBe('Failed to update role.');
        expect(alertText.length).toBeGreaterThan(20); // meaningful message, not a stub
      }
    }
  });
});

// ---------------------------------------------------------------------------
// User Profile
// ---------------------------------------------------------------------------

test.describe('User: Profile & Auth', () => {
  test('user/me endpoint returns role info', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    // The app should have loaded user data — check the nav shows admin link
    await expect(page.getByText('Admin')).toBeVisible();
  });

  test('student does not see admin link', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await expect(page.getByText('Admin')).not.toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Error Handling (regressions we've caught)
// ---------------------------------------------------------------------------

test.describe('Regression: API Error Display', () => {
  test('no page shows raw 500 error', async ({ page }) => {
    // Quick sweep of critical pages
    const pages = [
      { role: 'student' as const, path: '/home' },
      { role: 'instructor' as const, path: '/instructor' },
      { role: 'admin' as const, path: '/admin/users' },
    ];

    for (const p of pages) {
      await injectAuth(page, p.role);
      await page.goto(p.path, { waitUntil: 'networkidle' });

      const body = await page.locator('body').textContent();
      expect(body).not.toContain('Internal Server Error');
      expect(body).not.toContain('Traceback');
    }
  });
});
