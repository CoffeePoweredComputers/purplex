/**
 * E2E Tests -- Course Team Management
 *
 * Tests the CourseTeamManager component embedded in the course overview page:
 * team listing, role badges, role change protection, remove protection,
 * and the add-member form.
 *
 * Prerequisites:
 *   1. Django dev server running on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server running on :5173
 *   3. Test users created: python manage.py create_test_users
 *   4. E2E data seeded: python manage.py seed_e2e_data
 *
 * Run: npx playwright test e2e/instructor/course-team.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';

const COURSE_URL = '/instructor/courses/CS101-2024';

test.describe('Course Team Management', () => {
  test('team section shows instructor as Primary', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    // Wait for the team section to load
    const teamSection = page.locator('.team-manager');
    await teamSection.waitFor({ state: 'visible', timeout: 15000 });
    await teamSection.locator('.team-table').waitFor({ state: 'visible', timeout: 15000 });

    // Instructor should be listed
    await expect(teamSection.getByText('instructor@test.local')).toBeVisible();

    // Role badge should show "Primary"
    const primaryBadge = teamSection.locator('.role-badge.role-primary');
    await expect(primaryBadge.first()).toBeVisible();
    await expect(primaryBadge.first()).toContainText(/primary/i);
  });

  test('team table shows Name, Email, Role, and Added columns', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    const teamSection = page.locator('.team-manager');
    await teamSection.locator('.team-table').waitFor({ state: 'visible', timeout: 15000 });

    const headers = teamSection.locator('.team-table thead th');
    const headerTexts = await headers.allTextContents();
    const joined = headerTexts.join(' ').toLowerCase();

    expect(joined).toContain('name');
    expect(joined).toContain('email');
    expect(joined).toContain('role');
    expect(joined).toContain('added');
  });

  test('cannot demote last primary instructor', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    const teamSection = page.locator('.team-manager');
    await teamSection.locator('.team-table').waitFor({ state: 'visible', timeout: 15000 });

    // The instructor row should have a role select (since they are primary)
    const instructorRow = teamSection.locator('.team-table tbody tr').filter({
      hasText: 'instructor@test.local',
    });

    const roleSelect = instructorRow.locator('.role-select');

    // If there is a role select, try changing primary to TA
    const selectCount = await roleSelect.count();
    if (selectCount > 0) {
      await roleSelect.first().selectOption('ta');

      // Should show an error message (cannot demote last primary)
      const errorMessage = teamSection.locator('.action-error');
      await expect(errorMessage).toBeVisible({ timeout: 5000 });

      // The error should contain a meaningful message about last primary
      const errorText = await errorMessage.textContent();
      expect(errorText?.toLowerCase()).toMatch(/primary|last|cannot|only/);
    }
  });

  test('cannot remove last primary instructor', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    const teamSection = page.locator('.team-manager');
    await teamSection.locator('.team-table').waitFor({ state: 'visible', timeout: 15000 });

    // Find the instructor's row
    const instructorRow = teamSection.locator('.team-table tbody tr').filter({
      hasText: 'instructor@test.local',
    });

    const removeBtn = instructorRow.locator('.btn-remove');
    const removeBtnCount = await removeBtn.count();

    if (removeBtnCount > 0) {
      // Accept the native confirm dialog
      page.on('dialog', async (dialog) => {
        await dialog.accept();
      });

      await removeBtn.click();

      // Should show an error (cannot remove last primary)
      const errorMessage = teamSection.locator('.action-error');
      await expect(errorMessage).toBeVisible({ timeout: 5000 });

      const errorText = await errorMessage.textContent();
      expect(errorText?.toLowerCase()).toMatch(/primary|last|cannot|only|remove/);

      // Instructor should still be in the table
      await expect(instructorRow).toBeVisible();
    }
  });

  test('add team member form is visible for primary instructor', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    const teamSection = page.locator('.team-manager');
    await teamSection.locator('.team-table').waitFor({ state: 'visible', timeout: 15000 });

    // The "Add Team Member" section should be visible for the primary instructor
    const addMemberSection = teamSection.locator('.add-member');
    await expect(addMemberSection).toBeVisible();

    // It should have an email input and an Add button
    const emailInput = addMemberSection.locator('.input-email');
    await expect(emailInput).toBeVisible();

    const addBtn = addMemberSection.locator('.btn-add');
    await expect(addBtn).toBeVisible();

    // Add button should be disabled when email is empty
    await expect(addBtn).toBeDisabled();
  });

  test('role badges display correct styling for Primary', async ({ page }) => {
    await navigateAs(page, 'instructor', COURSE_URL);

    const teamSection = page.locator('.team-manager');
    await teamSection.locator('.team-table').waitFor({ state: 'visible', timeout: 15000 });

    // Check that the primary role badge has the correct CSS class
    const primaryBadge = teamSection.locator('.role-badge.role-primary').first();
    await expect(primaryBadge).toBeVisible();

    // The badge should have the role-primary class (which maps to specific styling)
    await expect(primaryBadge).toHaveClass(/role-primary/);
  });
});
