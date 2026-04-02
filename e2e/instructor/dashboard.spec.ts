/**
 * E2E Tests -- Instructor Dashboard
 *
 * Tests the instructor dashboard: course listing, card metadata, navigation,
 * course creation form (happy path, validation, cancel).
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *   4. E2E data seeded: python manage.py seed_e2e_data
 *
 * Run: npx playwright test e2e/instructor/dashboard.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, waitForContent, expectNoErrors } from '../helpers/navigation';

test.describe('Instructor Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await navigateAs(page, 'instructor', '/instructor');
  });

  test('instructor sees CS101-2024 course on dashboard', async ({ page }) => {
    // Wait for the course list to render (spinner should disappear)
    await page.locator('.courses-list').waitFor({ state: 'visible', timeout: 15000 });

    // The seeded course card should be present
    const courseCard = page.locator('.course-card').filter({ hasText: 'CS101-2024' });
    await expect(courseCard).toBeVisible();

    await expectNoErrors(page);
  });

  test('course card shows name, code, student count, and role badge', async ({ page }) => {
    await page.locator('.courses-list').waitFor({ state: 'visible', timeout: 15000 });

    const courseCard = page.locator('.course-card').filter({ hasText: 'CS101-2024' });

    // Course title: "Introduction to Programming"
    const title = courseCard.locator('.course-title');
    await expect(title).toContainText('Introduction to Programming');

    // Course code badge
    const code = courseCard.locator('.course-code');
    await expect(code).toContainText('CS101-2024');

    // Student count (at least the 2 seeded students)
    const studentCount = courseCard.locator('.student-count');
    await expect(studentCount).toBeVisible();

    // Role badge should display "Primary" for the instructor
    const roleBadge = courseCard.locator('.role-badge');
    await expect(roleBadge).toContainText(/primary/i);
  });

  test('click course card navigates to course overview', async ({ page }) => {
    await page.locator('.courses-list').waitFor({ state: 'visible', timeout: 15000 });

    const courseCard = page.locator('.course-card').filter({ hasText: 'CS101-2024' });
    await courseCard.click();

    await page.waitForURL('**/instructor/courses/CS101-2024', { timeout: 10000 });
    expect(page.url()).toContain('/instructor/courses/CS101-2024');
  });

  test('create course: fill form and submit creates new course', async ({ page }) => {
    await page.locator('.courses-list').waitFor({ state: 'visible', timeout: 15000 });

    // Click the add-course trigger button
    const addButton = page.locator('.add-card-trigger');
    await expect(addButton).toBeVisible();
    await addButton.click();

    // Form should expand
    const form = page.locator('.inline-course-form');
    await expect(form).toBeVisible();

    // Fill in course name
    const uniqueSuffix = Date.now();
    const courseName = `E2E Test Course ${uniqueSuffix}`;
    const courseId = `E2E-${uniqueSuffix}`;
    await page.locator('#new-course-name').fill(courseName);
    await page.locator('#new-course-id').fill(courseId);

    // Submit the form via the create button
    const createBtn = page.locator('.btn-create');
    await expect(createBtn).toBeEnabled();
    await createBtn.click();

    // Wait for the form to collapse (indicates success)
    await expect(form).not.toBeVisible({ timeout: 10000 });

    // The new course should appear in the list
    const newCard = page.locator('.course-card').filter({ hasText: courseId.toUpperCase() });
    await expect(newCard).toBeVisible();
  });

  test('create course with empty name keeps submit disabled', async ({ page }) => {
    await page.locator('.courses-list').waitFor({ state: 'visible', timeout: 15000 });

    // Open the creation form
    await page.locator('.add-card-trigger').click();
    const form = page.locator('.inline-course-form');
    await expect(form).toBeVisible();

    // Fill only the course ID, leave name empty
    await page.locator('#new-course-id').fill('EMPTY-NAME-TEST');

    // The create button should be disabled (isFormValid requires both fields)
    const createBtn = page.locator('.btn-create');
    await expect(createBtn).toBeDisabled();
  });

  test('cancel create collapses form without creating course', async ({ page }) => {
    await page.locator('.courses-list').waitFor({ state: 'visible', timeout: 15000 });

    // Count existing course cards (excluding the add-course-card)
    const courseCountBefore = await page.locator('.course-card:not(.add-course-card)').count();

    // Open the form
    await page.locator('.add-card-trigger').click();
    const form = page.locator('.inline-course-form');
    await expect(form).toBeVisible();

    // Fill in some data
    await page.locator('#new-course-name').fill('Should Not Exist');
    await page.locator('#new-course-id').fill('CANCEL-TEST');

    // Click Cancel
    const cancelBtn = page.locator('.btn-cancel');
    await cancelBtn.click();

    // Form should collapse
    await expect(form).not.toBeVisible();

    // No new course card should have appeared
    const courseCountAfter = await page.locator('.course-card:not(.add-course-card)').count();
    expect(courseCountAfter).toBe(courseCountBefore);
  });
});
