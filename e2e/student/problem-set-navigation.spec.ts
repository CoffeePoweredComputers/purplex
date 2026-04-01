/**
 * E2E Tests — Problem Set Navigation
 *
 * Verifies problem set page rendering: problem progress bars, prev/next
 * navigation, deadline banners, and problem status indicators.
 *
 * Seeded data:
 *   - e2e-basics: 2 problems (e2e-mcq-1 completed, e2e-eipl-1 not started)
 *   - e2e-code:   2 problems, soft deadline 7 days ago
 *   - e2e-mixed:  7 problems, hard deadline 7 days ago (locked)
 */

import { test, expect } from '@playwright/test';
import { navigateAs, waitForContent, expectNoErrors } from '../helpers/navigation';

test.describe('Problem Set Navigation', () => {
  test('e2e-basics shows 2 problem buttons', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-basics');

    // Wait for the problem set to load (loading message disappears)
    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    // Problem navigation uses buttons with class "progress-bar"
    const problemButtons = page.locator('.progress-bar');
    await expect(problemButtons).toHaveCount(2);
  });

  test('clicking problem button switches displayed problem', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-basics');

    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    const problemButtons = page.locator('.progress-bar');
    await expect(problemButtons).toHaveCount(2);

    // First problem button should have "active" class by default
    await expect(problemButtons.nth(0)).toHaveClass(/active/);

    // Click the second problem button
    await problemButtons.nth(1).click();

    // Second button should now be active, first should not
    await expect(problemButtons.nth(1)).toHaveClass(/active/);
    await expect(problemButtons.nth(0)).not.toHaveClass(/active/);
  });

  test('next button advances to next problem', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-basics');

    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    const problemButtons = page.locator('.progress-bar');

    // Starts on problem 0
    await expect(problemButtons.nth(0)).toHaveClass(/active/);

    // Click next (right arrow)
    const nextBtn = page.getByLabel('Next problem');
    await nextBtn.click();

    // Should now be on problem 1
    await expect(problemButtons.nth(1)).toHaveClass(/active/);
  });

  test('previous button goes back', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-basics');

    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    const problemButtons = page.locator('.progress-bar');

    // Go to problem 1 first
    const nextBtn = page.getByLabel('Next problem');
    await nextBtn.click();
    await expect(problemButtons.nth(1)).toHaveClass(/active/);

    // Click previous (left arrow)
    const prevBtn = page.getByLabel('Previous problem');
    await prevBtn.click();

    // Should be back on problem 0
    await expect(problemButtons.nth(0)).toHaveClass(/active/);
  });

  test('navigation wraps around at boundaries', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-basics');

    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    const problemButtons = page.locator('.progress-bar');

    // At first problem (index 0), clicking previous should wrap to last problem
    const prevBtn = page.getByLabel('Previous problem');
    await prevBtn.click();

    // Should wrap to last problem (index 1 for a 2-problem set)
    await expect(problemButtons.nth(1)).toHaveClass(/active/);

    // At last problem (index 1), clicking next should wrap to first
    const nextBtn = page.getByLabel('Next problem');
    await nextBtn.click();

    await expect(problemButtons.nth(0)).toHaveClass(/active/);
  });

  test('MCQ problem shows completed status indicator', async ({ page }) => {
    // Use student2 who has NO submissions — ensures clean progress state.
    // First submit the MCQ to create a "completed" status.
    await navigateAs(page, 'student2', '/courses/CS101-2024/problem-set/e2e-basics?p=0');
    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    // Submit the correct MCQ answer
    const mcqOption = page.locator('.mcq-option').first();
    await mcqOption.click();
    const submitBtn = page.locator('#submitButton');
    await expect(submitBtn).toBeEnabled({ timeout: 5000 });
    await submitBtn.click();
    await page.waitForTimeout(1000);

    // Reload to see updated progress indicators
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    const completedButtons = page.locator('.progress-bar.completed');
    const notStartedButtons = page.locator('.progress-bar.not_started');

    const completedCount = await completedButtons.count();
    const notStartedCount = await notStartedButtons.count();
    expect(completedCount).toBeGreaterThanOrEqual(1);
    expect(notStartedCount).toBeGreaterThanOrEqual(1);
  });

  test('e2e-code shows soft past deadline banner', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-code');

    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    // Soft past-due deadline banner should be visible
    const deadlineBanner = page.locator('.deadline-banner');
    await expect(deadlineBanner).toBeVisible();

    // Soft past-due has class "deadline-soft" or "deadline-past" (not "deadline-locked")
    // and shows "Late Submission" text
    await expect(deadlineBanner).not.toHaveClass(/deadline-locked/);
    await expect(deadlineBanner).toContainText('Late Submission');
  });

  test('e2e-mixed shows hard past deadline (locked) banner', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-mixed');

    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    // Hard past-due deadline banner should show "Submissions Closed"
    const deadlineBanner = page.locator('.deadline-banner');
    await expect(deadlineBanner).toBeVisible();

    await expect(deadlineBanner).toHaveClass(/deadline-locked/);
    await expect(deadlineBanner).toContainText('Submissions Closed');
  });

  test('problem set page loads without errors', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-basics');

    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    await expectNoErrors(page);

    // Progress summary should show counts
    const completedStat = page.locator('.progress-stat.completed');
    await expect(completedStat).toBeVisible();
  });
});
