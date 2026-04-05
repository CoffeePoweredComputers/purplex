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
      // Try instructor first, fall back to admin for admin-created tests
      await apiAs(page, 'instructor', 'DELETE', `/api/instructor/courses/${id}/`)
        .catch(() => apiAs(page, 'admin', 'DELETE', `/api/admin/courses/${id}/`))
        .catch(() => {});
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

    // Change name and description
    const nameInput = page.getByPlaceholder(/Introduction to/i);
    await nameInput.fill('Updated Course Name');
    const descInput = page.getByPlaceholder(/description/i);
    await descInput.fill('Updated description text');
    await page.waitForTimeout(500);

    const savePromise = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'PATCH',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /update course/i }).click();
    const saveResp = await savePromise;
    expect(saveResp.status()).toBeLessThan(300);

    // Verify both fields persisted via API
    const fetchResult = await apiAs(page, 'instructor', 'GET', `/api/instructor/courses/${courseId}/`);
    expect(fetchResult.data.name).toBe('Updated Course Name');
    expect(fetchResult.data.description).toBe('Updated description text');
  });

  test('admin can update course via PATCH', async ({ page }) => {
    // Navigate to establish page context for apiAs fetch calls
    await navigateAs(page, 'admin', '/admin');
    await page.waitForTimeout(1000);

    // Create course as instructor first
    const courseId = `E2E-ADM-EDIT-${Date.now()}`;
    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/courses/create/', {
      course_id: courseId,
      name: 'Admin Edit Original',
      description: 'Original admin description',
      is_active: true,
      enrollment_open: true,
    });
    expect(createResult.status).toBe(201);
    createdIds.push(courseId);

    // Admin updates course via PATCH
    const patchResult = await apiAs(page, 'admin', 'PATCH', `/api/admin/courses/${courseId}/`, {
      name: 'Admin Updated Name',
      description: 'Admin updated description',
    });
    expect(patchResult.status).toBeLessThan(300);
    expect(patchResult.data.name).toBe('Admin Updated Name');

    // Verify persisted via separate GET
    const fetchResult = await apiAs(page, 'admin', 'GET', `/api/admin/courses/${courseId}/`);
    expect(fetchResult.data.name).toBe('Admin Updated Name');
    expect(fetchResult.data.description).toBe('Admin updated description');
  });

  test('admin can change primary instructor via PATCH', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin');
    await page.waitForTimeout(1000);

    // Get the list of available instructors
    const instructorsResult = await apiAs(page, 'admin', 'GET', '/api/admin/instructors/');
    expect(instructorsResult.status).toBe(200);
    const instructors = instructorsResult.data;

    // Find two different users to switch between
    const instructorUser = instructors.find((u: { username: string }) => u.username === 'instructor');
    const adminUser = instructors.find((u: { username: string }) => u.username === 'admin');
    expect(instructorUser).toBeTruthy();
    expect(adminUser).toBeTruthy();

    // Create course with instructor as primary
    const courseId = `E2E-SWITCH-${Date.now()}`;
    const createResult = await apiAs(page, 'admin', 'POST', '/api/admin/courses/', {
      course_id: courseId,
      name: 'Instructor Switch Test',
      instructor_id: instructorUser.id,
      is_active: true,
      enrollment_open: true,
    });
    expect(createResult.status).toBe(201);
    createdIds.push(courseId);

    // Verify original instructor is primary
    const beforeResult = await apiAs(page, 'admin', 'GET', `/api/admin/courses/${courseId}/`);
    const beforeInstructors = beforeResult.data.instructors;
    expect(beforeInstructors.some((i: { username: string; role: string }) =>
      i.username === 'instructor' && i.role === 'primary'
    )).toBe(true);

    // Switch primary instructor to admin user
    const patchResult = await apiAs(page, 'admin', 'PATCH', `/api/admin/courses/${courseId}/`, {
      instructor_id: adminUser.id,
    });
    expect(patchResult.status).toBeLessThan(300);

    // Verify admin user is now a primary instructor
    const afterResult = await apiAs(page, 'admin', 'GET', `/api/admin/courses/${courseId}/`);
    const afterInstructors = afterResult.data.instructors;
    expect(afterInstructors.some((i: { username: string; role: string }) =>
      i.username === 'admin' && i.role === 'primary'
    )).toBe(true);
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

  test('toggle Is Active checkbox', async ({ page }) => {
    const courseId = `E2E-ACTIVE-${Date.now()}`;

    await navigateAs(page, 'instructor', '/instructor/courses/new');
    await page.waitForTimeout(2000);
    await page.getByPlaceholder('e.g., CS101-FALL2024').fill(courseId);
    await page.getByPlaceholder(/Introduction to/i).fill('Active Toggle Test');
    await page.getByPlaceholder(/description/i).fill('Testing is_active toggle');
    await page.getByRole('button', { name: /create course/i }).click();
    await page.waitForTimeout(2000);
    createdIds.push(courseId);

    await page.goto(`/instructor/courses/${courseId}/edit`);
    await page.waitForTimeout(2000);

    // Uncheck "Course is active" (first checkbox)
    const activeCheckbox = page.getByRole('checkbox').first();
    await activeCheckbox.uncheck();
    await page.waitForTimeout(300);

    const savePromise = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'PATCH',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /update course/i }).click();
    const saveResp = await savePromise;
    expect(saveResp.status()).toBeLessThan(300);
  });

  test('delete course and verify removal', async ({ page }) => {
    const courseId = `E2E-DEL-${Date.now()}`;

    await navigateAs(page, 'instructor', '/instructor/courses/new');
    await page.waitForTimeout(2000);
    await page.getByPlaceholder('e.g., CS101-FALL2024').fill(courseId);
    await page.getByPlaceholder(/Introduction to/i).fill('Delete Test Course');
    await page.getByPlaceholder(/description/i).fill('Course to be deleted');

    const createPromise = page.waitForResponse(
      r => r.url().includes('/api/') && r.request().method() === 'POST',
      { timeout: 10000 },
    );
    await page.getByRole('button', { name: /create course/i }).click();
    await createPromise;
    createdIds.push(courseId);

    // Navigate to edit (same session, no re-auth)
    await page.goto(`/instructor/courses/${courseId}/edit`);
    await page.waitForTimeout(3000);

    // Click Delete in header
    await page.getByRole('button', { name: 'Delete' }).first().click();

    // Wait for dialog
    await page.locator('.dialog-overlay').waitFor({ state: 'visible', timeout: 5000 });

    // Click Delete in dialog (last Delete button on page)
    const allDeleteBtns = page.getByRole('button', { name: 'Delete' });
    await allDeleteBtns.last().click();

    // Wait for navigation
    await page.waitForTimeout(3000);
    expect(page.url()).not.toContain('/edit');
  });
});
