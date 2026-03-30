/**
 * E2E Tests — Student Progress
 *
 * Verifies progress tracking both via the REST API (using apiAs) and
 * via the UI state rendered on the home page and problem set views.
 *
 * Seeded data:
 *   - Student has 1 prior submission on e2e-mcq-1 (score=100, correct)
 *   - e2e-eipl-1 has no submissions (not started)
 *   - e2e-basics contains both problems (2 total, 1 completed)
 */

import { test, expect } from '@playwright/test';
import { navigateAs, waitForContent } from '../helpers/navigation';
import { apiAs } from '../helpers/api';

test.describe('Student Progress', () => {
  test('API: completed problem returns is_completed=true and best_score=100', async ({ page }) => {
    // Need to be on the origin for page.evaluate to work
    await navigateAs(page, 'student', '/home');

    const result = await apiAs(page, 'student', 'GET', '/api/progress/e2e-mcq-1/');

    expect(result.status).toBe(200);
    expect(result.data).toBeTruthy();

    // The MCQ problem was solved with score=100
    expect(result.data.is_completed).toBe(true);
    expect(result.data.best_score).toBe(100);
  });

  test('API: unattempted problem returns not started status', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    const result = await apiAs(page, 'student', 'GET', '/api/progress/e2e-eipl-1/');

    expect(result.status).toBe(200);
    expect(result.data).toBeTruthy();

    // No submissions yet — should show not completed
    expect(result.data.is_completed).toBe(false);
    // best_score should be 0 or null for unattempted
    expect(result.data.best_score == null || result.data.best_score === 0).toBeTruthy();
  });

  test('API: problem set progress shows partial completion', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    const result = await apiAs(
      page,
      'student',
      'GET',
      '/api/problem-sets/e2e-basics/progress/',
    );

    expect(result.status).toBe(200);
    expect(result.data).toBeTruthy();

    // e2e-basics has 2 problems, 1 completed
    // The response should indicate partial completion
    if (result.data.completed_problems !== undefined) {
      expect(result.data.completed_problems).toBe(1);
      expect(result.data.total_problems).toBe(2);
    } else if (result.data.problems) {
      // Alternative response shape: array of per-problem progress
      const completed = result.data.problems.filter(
        (p: { is_completed: boolean }) => p.is_completed,
      );
      expect(completed.length).toBe(1);
    }
  });

  test('home page card shows partial progress for e2e-basics', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Find the progress text that shows "1 / 2 completed"
    const progressTexts = page.locator('.progress-text');
    const allTexts = await progressTexts.allTextContents();

    // At least one card should indicate partial completion (1 of 2)
    const hasPartialProgress = allTexts.some(
      (text) => text.includes('1 / 2') || text.includes('1/2'),
    );
    expect(hasPartialProgress).toBeTruthy();

    // The progress bar for e2e-basics should show 50% (1/2 completed)
    const progressBars = page.locator('[role="progressbar"]');
    const count = await progressBars.count();

    let foundFiftyPercent = false;
    for (let i = 0; i < count; i++) {
      const valueNow = await progressBars.nth(i).getAttribute('aria-valuenow');
      if (valueNow === '50') {
        foundFiftyPercent = true;
        break;
      }
    }
    expect(foundFiftyPercent).toBeTruthy();
  });

  test('problem set view shows completed vs not-started problem indicators', async ({ page }) => {
    await navigateAs(page, 'student', '/courses/CS101-2024/problem-set/e2e-basics');

    await page.waitForSelector('.problem-set-container', { timeout: 15_000 });

    // The progress bar buttons carry CSS classes for status:
    //   .completed  — green (solved)
    //   .not_started — gray (never attempted)
    //   .in_progress — partial

    const completedDots = page.locator('.progress-bar.completed');
    const notStartedDots = page.locator('.progress-bar.not_started');

    // MCQ is completed, EiPL is not started
    await expect(completedDots).toHaveCount(1);
    await expect(notStartedDots).toHaveCount(1);

    // The progress summary should show "1 completed" and "1 remaining"
    const completedStat = page.locator('.progress-stat.completed');
    await expect(completedStat).toContainText('1 completed');

    const remainingStat = page.locator('.progress-stat.remaining');
    await expect(remainingStat).toContainText('1 remaining');
  });
});
