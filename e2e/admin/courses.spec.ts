/**
 * E2E Tests -- Admin Course Management
 *
 * Tests the /admin/courses page and admin course API endpoints:
 * listing courses, viewing details, managing team, enrolled students,
 * and problem sets.
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server on :5173
 *   3. Seeded course: CS101-2024 (instructor=primary, student+student2=enrolled)
 *
 * Run: npx playwright test e2e/admin/courses.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';
import { apiAs } from '../helpers/api';

const COURSE_ID = 'CS101-2024';

test.describe('Admin Course Management', () => {
  test('admin courses page loads without errors', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/courses');
    await expectNoErrors(page);
  });

  test('admin can list courses via API and see CS101-2024', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    const response = await apiAs(page, 'admin', 'GET', '/api/admin/courses/');
    expect(response.status).toBe(200);

    const courses = response.data.results || response.data;
    expect(Array.isArray(courses)).toBeTruthy();

    // Seeded course should be present
    const courseIds = courses.map((c: any) => c.course_id || c.id);
    expect(courseIds).toContain(COURSE_ID);
  });

  test('admin can view course details via API', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    const response = await apiAs(page, 'admin', 'GET', `/api/admin/courses/${COURSE_ID}/`);
    expect(response.status).toBe(200);

    // Should contain course data
    const course = response.data;
    expect(course).toBeDefined();
    expect(course.course_id || course.id).toBe(COURSE_ID);
  });

  test('admin can view course team via API', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    const response = await apiAs(page, 'admin', 'GET', `/api/admin/courses/${COURSE_ID}/team/`);
    expect(response.status).toBe(200);

    // Team should include at least the primary instructor
    const team = response.data.results || response.data;
    expect(Array.isArray(team)).toBeTruthy();
    expect(team.length).toBeGreaterThanOrEqual(1);

    // At least one member should have the primary role
    const hasPrimary = team.some((m: any) => m.role === 'primary');
    expect(hasPrimary).toBeTruthy();
  });

  test('admin can view enrolled students via API', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    const response = await apiAs(page, 'admin', 'GET', `/api/admin/courses/${COURSE_ID}/students/`);
    expect(response.status).toBe(200);

    // Should have at least the two seeded enrolled students
    const students = response.data.results || response.data;
    expect(Array.isArray(students)).toBeTruthy();
    expect(students.length).toBeGreaterThanOrEqual(2);
  });

  test('admin can view course problem sets via API', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');

    const response = await apiAs(page, 'admin', 'GET', `/api/admin/courses/${COURSE_ID}/problem-sets/`);
    expect(response.status).toBe(200);

    // Should have at least the seeded problem sets
    const problemSets = response.data.results || response.data;
    expect(Array.isArray(problemSets)).toBeTruthy();
    expect(problemSets.length).toBeGreaterThanOrEqual(1);
  });

  test('admin course management page shows CS101-2024', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/courses');

    // Wait for courses to load
    await page.waitForTimeout(3000);

    // The page should display the seeded course
    const body = await page.locator('body').textContent();
    expect(body).toContain('CS101');
  });
});
