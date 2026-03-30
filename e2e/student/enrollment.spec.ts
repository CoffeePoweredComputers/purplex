/**
 * E2E Tests — Course Enrollment
 *
 * Verifies the enrollment modal behavior: opening, input validation,
 * "already enrolled" detection, and modal dismissal.
 *
 * The student is already enrolled in CS101-2024, so we can test the
 * "already enrolled" flow directly. For new enrollment, we test what
 * we can without requiring a second seeded course.
 */

import { test, expect } from '@playwright/test';
import { navigateAs, waitForContent } from '../helpers/navigation';

test.describe('Course Enrollment', () => {
  test('open enrollment modal via floating button', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // The floating "+" button opens the enrollment modal
    const floatingBtn = page.locator('.add-course-btn.floating');
    await expect(floatingBtn).toBeVisible();
    await floatingBtn.click();

    // Modal should appear with the dialog role
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Modal title should be "Join a Course"
    const modalTitle = page.locator('#enrollment-modal-title');
    await expect(modalTitle).toHaveText('Join a Course');

    // Input and lookup button should be present
    const courseInput = page.locator('#course-id');
    await expect(courseInput).toBeVisible();

    const lookupBtn = page.getByRole('button', { name: 'Lookup Course' });
    await expect(lookupBtn).toBeVisible();
  });

  test('enter invalid course code shows error message', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Open modal
    await page.locator('.add-course-btn.floating').click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Type an invalid course code
    const courseInput = page.locator('#course-id');
    await courseInput.fill('NONEXISTENT-999');

    // Click lookup
    const lookupBtn = page.getByRole('button', { name: 'Lookup Course' });
    await lookupBtn.click();

    // Should show an error message
    const errorMessage = page.locator('.error-message');
    await expect(errorMessage).toBeVisible({ timeout: 10_000 });
  });

  test('already enrolled in CS101-2024 shows enrolled message', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Open modal
    await page.locator('.add-course-btn.floating').click();

    // Look up the course the student is already enrolled in
    const courseInput = page.locator('#course-id');
    await courseInput.fill('CS101-2024');

    const lookupBtn = page.getByRole('button', { name: 'Lookup Course' });
    await lookupBtn.click();

    // Should show the course preview with "already enrolled" indicator
    const alreadyEnrolled = page.locator('.already-enrolled');
    await expect(alreadyEnrolled).toBeVisible({ timeout: 10_000 });

    // The text should indicate enrollment
    await expect(alreadyEnrolled).toContainText('already enrolled');

    // The "Join Course" enroll button should NOT be visible (replaced by enrolled message)
    const enrollBtn = page.locator('.enroll-btn');
    await expect(enrollBtn).not.toBeVisible();
  });

  test('modal close via close button', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Open modal
    await page.locator('.add-course-btn.floating').click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Click the close button (x)
    const closeBtn = page.locator('.close-btn');
    await closeBtn.click();

    // Modal should disappear
    await expect(modal).not.toBeVisible();
  });

  test('modal close via clicking outside (overlay)', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Open modal
    await page.locator('.add-course-btn.floating').click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Click the overlay (outside the modal content).
    // The overlay has @click.self="hideModal", so clicking the overlay itself closes.
    // We click at coordinates outside the modal-content box.
    const overlay = page.locator('.modal-overlay');
    const overlayBox = await overlay.boundingBox();
    if (overlayBox) {
      // Click near the top-left corner of the overlay (outside modal-content)
      await page.mouse.click(overlayBox.x + 10, overlayBox.y + 10);
    }

    // Modal should disappear
    await expect(modal).not.toBeVisible();
  });

  test('lookup button is disabled when input is empty', async ({ page }) => {
    await navigateAs(page, 'student', '/home');

    await waitForContent(page, 'Introduction to Programming');

    // Open modal
    await page.locator('.add-course-btn.floating').click();

    // The lookup button should be disabled when the input is empty
    const lookupBtn = page.getByRole('button', { name: 'Lookup Course' });
    await expect(lookupBtn).toBeDisabled();

    // Type something — button should become enabled
    const courseInput = page.locator('#course-id');
    await courseInput.fill('anything');
    await expect(lookupBtn).toBeEnabled();

    // Clear — button should be disabled again
    await courseInput.fill('');
    await expect(lookupBtn).toBeDisabled();
  });
});
