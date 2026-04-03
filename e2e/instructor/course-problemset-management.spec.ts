/**
 * E2E Tests: Course-Problem Set Association Management
 *
 * Verified via Playwright scripts:
 * - Page: /instructor/courses/{id}/problem-sets
 * - "Current Problem Sets" section with order ↑↓, due date, deadline type, required checkbox, Remove
 * - "Add Problem Sets" section with available items, each with an add button
 * - Add: POST → 201, appears in current section
 * - Remove: custom dialog (.dialog-overlay), not browser confirm
 * - Deadline options: None, Soft, Hard
 */

import { test, expect } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';

const COURSE_ID = 'CS101-2024';

async function goToCourseProblemSets(page: import('@playwright/test').Page) {
  await navigateAs(page, 'instructor', `/instructor/courses/${COURSE_ID}/problem-sets`);
  await page.waitForTimeout(3000);
}

test.describe('Course-Problem Set Management', () => {
  test('page shows current and available problem sets', async ({ page }) => {
    await goToCourseProblemSets(page);

    await expect(page.locator('text=Current Problem Sets')).toBeVisible();
    await expect(page.locator('text=Add Problem Sets')).toBeVisible();

    // Should have some current problem sets
    const currentCount = await page.locator('.action-button.remove-button').count();
    expect(currentCount).toBeGreaterThanOrEqual(1);

    // Should have available problem sets to add
    const availableCount = await page.locator('.add-button').count();
    expect(availableCount).toBeGreaterThanOrEqual(1);
  });

  test('add problem set to course', async ({ page }) => {
    await goToCourseProblemSets(page);

    const initialCount = await page.locator('.action-button.remove-button').count();

    // Click add on the first available PS
    const addResponse = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'POST',
      { timeout: 10000 },
    );
    await page.locator('.add-button').first().click();
    const resp = await addResponse;
    expect(resp.status()).toBe(201);

    await page.waitForTimeout(1000);
    const afterCount = await page.locator('.action-button.remove-button').count();
    expect(afterCount).toBe(initialCount + 1);
  });

  test('remove problem set from course via dialog', async ({ page }) => {
    await goToCourseProblemSets(page);

    const initialCount = await page.locator('.action-button.remove-button').count();
    expect(initialCount).toBeGreaterThan(0);

    // Click Remove on the last current PS
    await page.locator('.action-button.remove-button').last().click();

    // Confirm in the custom dialog
    const dialog = page.locator('.dialog-overlay');
    await dialog.waitFor({ state: 'visible', timeout: 5000 });

    const deleteResponse = page.waitForResponse(
      r => r.request().method() === 'DELETE',
      { timeout: 10000 },
    );
    await dialog.locator('.btn-danger').click();
    const resp = await deleteResponse;
    expect(resp.status()).toBe(204);

    await page.waitForTimeout(1000);
    const afterCount = await page.locator('.action-button.remove-button').count();
    expect(afterCount).toBe(initialCount - 1);
  });

  test('deadline type dropdown has None, Soft, Hard options', async ({ page }) => {
    await goToCourseProblemSets(page);

    const select = page.locator('.deadline-select, select').first();
    await expect(select).toBeVisible();

    const options = await select.locator('option').allTextContents();
    expect(options).toContain('None');
    expect(options).toContain('Soft');
    expect(options).toContain('Hard');
  });

  test('required checkbox toggles', async ({ page }) => {
    await goToCourseProblemSets(page);

    const checkbox = page.locator('.required-checkbox, input[type=checkbox]').first();
    await expect(checkbox).toBeVisible();

    const initialChecked = await checkbox.isChecked();

    // Toggle
    await checkbox.click();
    await page.waitForTimeout(1000);

    const afterChecked = await checkbox.isChecked();
    expect(afterChecked).toBe(!initialChecked);

    // Toggle back to restore state
    await checkbox.click();
    await page.waitForTimeout(500);
  });

  test('order buttons exist for reordering', async ({ page }) => {
    await goToCourseProblemSets(page);

    const upButtons = page.locator('.order-btn').filter({ hasText: '↑' });
    const downButtons = page.locator('.order-btn').filter({ hasText: '↓' });

    expect(await upButtons.count()).toBeGreaterThanOrEqual(1);
    expect(await downButtons.count()).toBeGreaterThanOrEqual(1);
  });

  test('set due date and verify persistence', async ({ page }) => {
    await goToCourseProblemSets(page);

    // Set due date on the first PS row
    const dueDateInput = page.locator('input[type=datetime-local]').first();
    await dueDateInput.fill('2027-06-15T14:00');
    await dueDateInput.blur();
    await page.waitForTimeout(2000);

    // Reload to verify it persisted
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const afterReload = await page.locator('input[type=datetime-local]').first().inputValue();
    expect(afterReload).toContain('2027-06-15');
  });

  test('change deadline type and verify persistence', async ({ page }) => {
    await goToCourseProblemSets(page);

    // Find the first enabled deadline select (one that has a due date)
    const enabledSelect = page.locator('select:not([disabled])').first();
    const isVisible = await enabledSelect.isVisible().catch(() => false);

    if (isVisible) {
      await enabledSelect.selectOption('hard');
      await page.waitForTimeout(2000);

      await page.reload({ waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);

      const afterReload = await page.locator('select:not([disabled])').first().inputValue();
      expect(afterReload).toBe('hard');
    } else {
      // No PS has a due date — skip gracefully
      test.skip();
    }
  });
});
