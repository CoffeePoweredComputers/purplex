/**
 * E2E Tests -- Instructor Course Overview
 *
 * Tests the course overview page: header details, navigation tabs (via
 * InstructorNavBar), students view, problem sets timeline, team section,
 * and submissions link.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *   4. E2E data seeded: python manage.py seed_e2e_data
 *
 * Run: npx playwright test e2e/instructor/course-overview.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, expectNoErrors } from '../helpers/navigation';

const COURSE_URL = '/instructor/courses/CS101-2024';

test.describe('Instructor Course Overview', () => {
  test('navigates to course overview and shows course details', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    // Wait for loading to finish -- the course-card container appears
    await page.locator('.course-card').first().waitFor({ state: 'visible', timeout: 15000 });

    await expectNoErrors(page);
  });

  test('course header shows title, code, and student count', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);
    await page.locator('.course-header').waitFor({ state: 'visible', timeout: 15000 });

    // Course name
    const heading = page.locator('.course-header h1');
    await expect(heading).toContainText('Introduction to Programming');

    // Course code
    const courseCode = page.locator('.course-code');
    await expect(courseCode).toContainText('CS101-2024');

    // Student count stat
    const studentStat = page.locator('.header-stat .stat-label').filter({ hasText: /students/i });
    await expect(studentStat).toBeVisible();
  });

  test('navbar shows course-scoped navigation links', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);
    await page.locator('.instructor-nav').waitFor({ state: 'visible', timeout: 10000 });

    // InstructorNavBar in course context shows: My Courses, Overview, Students, Submissions, Problem Sets
    const nav = page.locator('.instructor-nav');

    // "My Courses" link always present
    await expect(nav.getByText(/my courses/i)).toBeVisible();

    // Course-scoped links
    await expect(nav.getByText(/overview/i)).toBeVisible();
    await expect(nav.getByText(/students/i)).toBeVisible();
    await expect(nav.getByText(/submissions/i)).toBeVisible();
    await expect(nav.getByText(/problem sets/i)).toBeVisible();
  });

  test('students page shows enrolled students', async ({ page }) => {
    await navigateAs(page, 'instructor', `${COURSE_URL}/students`);

    // Wait for the student table to load
    await page.locator('.students-table, .loading-container').first().waitFor({ state: 'visible', timeout: 15000 });

    // If loading, wait for it to resolve
    await page.locator('.students-table').waitFor({ state: 'visible', timeout: 15000 });

    // Should contain the two seeded students
    const tableBody = page.locator('.students-table tbody');
    await expect(tableBody.getByText('student@test.local')).toBeVisible();
    await expect(tableBody.getByText('student2@test.local')).toBeVisible();
  });

  test('problem set timeline shows seeded problem sets', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    // Wait for the journey timeline to load
    await page.locator('.journey-timeline, .empty-journey').first().waitFor({ state: 'visible', timeout: 15000 });

    // The three seeded problem sets should appear in the timeline
    const timeline = page.locator('.journey-timeline');
    await expect(timeline.getByText('E2E Basics')).toBeVisible();
    await expect(timeline.getByText('E2E Code Challenges')).toBeVisible();
    await expect(timeline.getByText('E2E Mixed Set')).toBeVisible();
  });

  test('team section shows instructor as Primary', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    // The CourseTeamManager is rendered inside .course-card-team
    const teamSection = page.locator('.course-card-team');
    await teamSection.waitFor({ state: 'visible', timeout: 15000 });

    // Wait for team table to load (spinner disappears, table appears)
    await teamSection.locator('.team-table').waitFor({ state: 'visible', timeout: 15000 });

    // Instructor should appear in the team table
    await expect(teamSection.getByText('instructor@test.local')).toBeVisible();

    // Should have a "Primary" role badge
    const roleBadge = teamSection.locator('.role-badge.role-primary');
    await expect(roleBadge.first()).toBeVisible();
  });

  test('submissions link navigates to course submissions page', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);
    await page.locator('.instructor-nav').waitFor({ state: 'visible', timeout: 10000 });

    // Click the Submissions nav link
    const submissionsLink = page.locator('.instructor-nav').getByText(/submissions/i);
    await submissionsLink.click();

    await page.waitForURL(`**/instructor/courses/CS101-2024/submissions`, { timeout: 10000 });
    expect(page.url()).toContain('/instructor/courses/CS101-2024/submissions');
  });

  test('students page search filters results', async ({ page }) => {
    await navigateAs(page, 'instructor', `${COURSE_URL}/students`);
    await page.locator('.students-table').waitFor({ state: 'visible', timeout: 15000 });

    // Both students should be visible initially
    const tableBody = page.locator('.students-table tbody');
    const initialRows = await tableBody.locator('tr').count();
    expect(initialRows).toBeGreaterThanOrEqual(2);

    // Type a search query to filter
    const searchInput = page.locator('#student-search');
    await searchInput.fill('student2');

    // After filtering, only student2 should appear
    // (client-side filter, so we wait a moment for the reactive update)
    await page.waitForTimeout(500);

    const filteredRows = tableBody.locator('tr');
    await expect(filteredRows).toHaveCount(1);
    await expect(filteredRows.first()).toContainText('student2@test.local');
  });
});
