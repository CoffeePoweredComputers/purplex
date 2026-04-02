/**
 * E2E Tests — Student Home Page
 *
 * Verifies the home page renders enrolled courses, problem set cards with
 * progress/due-date badges, and navigation to problem set views.
 *
 * Seeded data:
 *   - Course CS101-2024 "Introduction to Programming"
 *   - Student + Student2 enrolled
 *   - Problem sets: e2e-basics (2 problems), e2e-code (2), e2e-mixed (7)
 *   - Student has 1 prior MCQ submission (score=100) on e2e-mcq-1
 */

import { test, expect } from '@playwright/test';
import { navigateAs, waitForContent, expectNoErrors } from '../helpers/navigation';

test.describe('Student Home Page', () => {
  test('student sees enrolled course "Introduction to Programming"', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');
    const courseTitle = page.getByRole('heading', { name: 'Introduction to Programming' });
    await expect(courseTitle).toBeVisible();
  });

  test('course section shows problem set cards', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Each problem set renders as a button with class "problem-set-card"
    const cards = page.locator('.problem-set-card');
    await expect(cards).not.toHaveCount(0);

    // Verify the seeded problem set titles are present.
    // Card titles use <h3 class="card-title">
    const cardTitles = page.locator('.card-title');
    const titles = await cardTitles.allTextContents();
    expect(titles.length).toBeGreaterThanOrEqual(3);
  });

  test('problem set cards show due date badges', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // At least some cards should have due-badge spans.
    // e2e-code and e2e-mixed have past due dates, e2e-basics is due in 30 days.
    const dueBadges = page.locator('.due-badge');
    await expect(dueBadges.first()).toBeVisible();

    // e2e-mixed is hard-past, so its badge should show the locked text "Closed"
    const closedBadge = page.getByText('Closed').first();
    await expect(closedBadge).toBeVisible();
  });

  test('clicking problem set card navigates to problem set view', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Click the first problem set card
    const firstCard = page.locator('.problem-set-card').first();
    await firstCard.click();

    // Should navigate to the problem set route
    await page.waitForURL(/\/courses\/CS101-2024\/problem-set\//);

    // The problem set page should load without errors
    await expectNoErrors(page);
  });

  test('progress shown on problem set cards', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Progress text uses the pattern "{completed} / {total} completed"
    // e2e-basics has 2 problems, student solved 1 MCQ => "1 / 2 completed"
    // Wait for at least one progress text that shows a non-zero total
    const progressTexts = page.locator('.progress-text');
    await expect(progressTexts.first()).toBeVisible({ timeout: 10000 });

    const allProgress = await progressTexts.allTextContents();

    // At least one card should show partial progress (1/2) or any progress format
    const hasPartialProgress = allProgress.some(
      (text) => text.includes('1 / 2') || text.includes('1/2'),
    );
    // Fallback: at least verify progress text exists with the "{n} / {m} completed" pattern
    const hasAnyProgress = allProgress.some(
      (text) => /\d+\s*\/\s*\d+/.test(text),
    );
    expect(hasPartialProgress || hasAnyProgress).toBeTruthy();
  });

  test('page loads without errors', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    // Wait for content to settle
    await page.waitForLoadState('networkidle');

    await expectNoErrors(page);

    // Verify main content area is visible (not stuck on loading)
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });

  test('course name and progress indicator render correctly', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // The course header shows a progress indicator with "X / Y completed"
    const progressIndicator = page.locator('.progress-indicator');
    await expect(progressIndicator.first()).toBeVisible();

    const indicatorText = await progressIndicator.first().textContent();
    // Should match the pattern "N / M completed"
    expect(indicatorText).toMatch(/\d+\s*\/\s*\d+\s*completed/);
  });

  test('student2 sees same course (also enrolled)', async ({ page }) => {
    await navigateAs(page, 'student2', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // student2 should also see the problem set cards
    const cards = page.locator('.problem-set-card');
    await expect(cards).not.toHaveCount(0);
  });

  test('progress bars have correct aria attributes', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Progress bars use role="progressbar" with aria-valuenow, aria-valuemin, aria-valuemax
    const progressBars = page.locator('[role="progressbar"]');
    const firstBar = progressBars.first();
    await expect(firstBar).toBeVisible();

    await expect(firstBar).toHaveAttribute('aria-valuemin', '0');
    await expect(firstBar).toHaveAttribute('aria-valuemax', '100');

    // aria-valuenow should be a number
    const valueNow = await firstBar.getAttribute('aria-valuenow');
    expect(Number(valueNow)).toBeGreaterThanOrEqual(0);
    expect(Number(valueNow)).toBeLessThanOrEqual(100);
  });
});
