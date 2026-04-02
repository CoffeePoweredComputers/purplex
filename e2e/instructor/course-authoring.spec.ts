/**
 * E2E Tests: Instructor Course Authoring
 *
 * Verified via Playwright scripts:
 * - Form: course ID ("e.g., CS101-FALL2024"), name, description
 * - Two checkboxes (Is Active, Enrollment Open) — both default checked
 * - Save button text: "Create Course"
 * - API returns 201 with course_id field
 */

import { test, expect } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';
import { uniqueTitle } from '../helpers/instructor';

test.describe('Course Authoring', () => {
  const createdIds: string[] = [];

  test.afterEach(async ({ page }) => {
    for (const id of createdIds) {
      await apiAs(page, 'instructor', 'DELETE', `/api/instructor/courses/${id}/`).catch(() => {});
    }
    createdIds.length = 0;
  });

  test('create course with ID and name', async ({ page }) => {
    const courseId = `E2E-COURSE-${Date.now()}`;

    await navigateAs(page, 'instructor', '/instructor/courses/new');
    await page.waitForTimeout(2000);

    await page.getByPlaceholder('e.g., CS101-FALL2024').fill(courseId);
    await page.getByPlaceholder(/Introduction to/i).fill('E2E Test Course');
    await page.getByPlaceholder(/description/i).fill('Course created by E2E test');
    await page.waitForTimeout(500);

    const responsePromise = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'POST',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /create course/i }).click();
    const response = await responsePromise;
    const body = await response.json();

    expect(response.status()).toBe(201);
    expect(body.course_id).toBe(courseId);
    createdIds.push(courseId);
  });

  test('edit course name and description', async ({ page }) => {
    const courseId = `E2E-EDIT-${Date.now()}`;

    await navigateAs(page, 'instructor', '/instructor/courses/new');
    await page.waitForTimeout(2000);

    await page.getByPlaceholder('e.g., CS101-FALL2024').fill(courseId);
    await page.getByPlaceholder(/Introduction to/i).fill('Original Name');
    await page.getByPlaceholder(/description/i).fill('Original description text');
    await page.waitForTimeout(500);

    const createPromise = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'POST',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /create course/i }).click();
    await createPromise;
    createdIds.push(courseId);

    // Navigate to edit
    await page.goto(`/instructor/courses/${courseId}/edit`);
    await page.waitForTimeout(2000);

    // Change name
    const nameInput = page.getByPlaceholder(/Introduction to/i);
    await nameInput.fill('Updated Course Name');
    await page.waitForTimeout(500);

    const savePromise = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'PATCH',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /update course/i }).click();
    const saveResp = await savePromise;
    expect(saveResp.status()).toBeLessThan(300);

    // Verify via API
    const fetchResult = await apiAs(page, 'instructor', 'GET', `/api/instructor/courses/${courseId}/`);
    expect(fetchResult.data.name).toBe('Updated Course Name');
  });

  test('course ID is locked in edit mode', async ({ page }) => {
    const courseId = `E2E-LOCK-${Date.now()}`;

    await navigateAs(page, 'instructor', '/instructor/courses/new');
    await page.waitForTimeout(2000);

    await page.getByPlaceholder('e.g., CS101-FALL2024').fill(courseId);
    await page.getByPlaceholder(/Introduction to/i).fill('Lock Test Course');
    await page.getByPlaceholder(/description/i).fill('Testing course ID lock behavior');

    const createPromise = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'POST',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /create course/i }).click();
    await createPromise;
    createdIds.push(courseId);

    // Navigate to edit
    await page.goto(`/instructor/courses/${courseId}/edit`);
    await page.waitForTimeout(2000);

    // Course ID should be disabled
    const courseIdInput = page.getByPlaceholder('e.g., CS101-FALL2024');
    await expect(courseIdInput).toBeDisabled();
  });
});
