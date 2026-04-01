/**
 * E2E Tests -- Admin User Management
 *
 * Tests the /admin/users page: DataTable rendering, search, role filter,
 * role change via API, and nav visibility.
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server on :5173
 *   3. Seeded users: admin, instructor, student, student2
 *
 * Run: npx playwright test e2e/admin/users.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs, waitForContent, expectNoErrors } from '../helpers/navigation';
import { apiAs, waitForAPI } from '../helpers/api';

test.describe('Admin User Management', () => {
  test('page loads with DataTable and no errors', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/users');
    await expectNoErrors(page);

    // DataTable container should be visible
    const table = page.locator('.data-table-container');
    await expect(table).toBeVisible({ timeout: 15000 });
  });

  test('table displays seeded users', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/users');

    // Wait for the table rows to populate
    const tableBody = page.locator('.data-table tbody');
    await expect(tableBody).toBeVisible({ timeout: 15000 });

    // Admin user should be on the first page (alphabetical sort)
    const body = await page.locator('body').textContent();
    expect(body).toContain('admin');

    // Student may be on a later page — use the search box to find them
    const searchBox = page.locator('input[placeholder*="Search"]');
    await searchBox.fill('student');
    await page.waitForTimeout(500);  // debounce

    const filteredBody = await page.locator('body').textContent();
    expect(filteredBody).toContain('student');
  });

  test('search filters users by keyword', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/users');

    // Wait for table to load
    await page.locator('.data-table tbody tr').first().waitFor({ timeout: 15000 });

    // Type "student" into the search input
    const searchInput = page.locator('.search-input');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('student');

    // Wait for debounced search to fire and API to respond
    await page.waitForTimeout(1000);

    // After filtering, rows should contain "student" but not "admin" (as a username)
    const rows = page.locator('.data-table tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    // Each visible row should relate to "student"
    for (let i = 0; i < rowCount; i++) {
      const text = await rows.nth(i).textContent();
      expect(text?.toLowerCase()).toContain('student');
    }
  });

  test('role filter dropdown filters by role', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/users');

    // Wait for table to load
    await page.locator('.data-table tbody tr').first().waitFor({ timeout: 15000 });

    // Select "admin" from the role filter
    const roleSelect = page.locator('.filter-select');
    await expect(roleSelect).toBeVisible();
    await roleSelect.selectOption('admin');

    // Wait for API response
    await page.waitForTimeout(1000);

    // Should show at least the admin user
    const rows = page.locator('.data-table tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThanOrEqual(1);
  });

  test('clear filters button resets all filters', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/users');

    // Wait for table
    await page.locator('.data-table tbody tr').first().waitFor({ timeout: 15000 });

    // Apply a search filter
    const searchInput = page.locator('.search-input');
    await searchInput.fill('student');
    await page.waitForTimeout(1000);

    // Clear filters button should appear
    const clearBtn = page.locator('.clear-filters-btn');
    await expect(clearBtn).toBeVisible();
    await clearBtn.click();

    // Wait for data reload
    await page.waitForTimeout(1000);

    // Search input should be empty
    await expect(searchInput).toHaveValue('');
  });

  test('role change via API succeeds for admin', async ({ page }) => {
    // First, get the list of users to find a student user ID
    await navigateAs(page, 'admin', '/home');

    const listResponse = await apiAs(page, 'admin', 'GET', '/api/admin/users/');
    expect(listResponse.status).toBe(200);

    // Find student user
    const users = listResponse.data.results || listResponse.data;
    const studentUser = (Array.isArray(users) ? users : []).find(
      (u: any) => u.email === 'student2@test.local',
    );

    if (studentUser) {
      // Change student2's role to instructor, then back to user
      const postResponse = await apiAs(page, 'admin', 'POST', `/api/admin/user/${studentUser.id}/`, {
        role: 'instructor',
      });
      expect(postResponse.status).toBe(200);

      // Revert it back
      const revertResponse = await apiAs(page, 'admin', 'POST', `/api/admin/user/${studentUser.id}/`, {
        role: 'user',
      });
      expect(revertResponse.status).toBe(200);
    }
  });

  test('admin link is visible in navbar for admin user', async ({ page }) => {
    await navigateAs(page, 'admin', '/home');
    await expect(page.getByText('Admin')).toBeVisible();
  });

  test('admin link is NOT visible for student user', async ({ page }) => {
    await navigateAs(page, 'student', '/home');
    await expect(page.getByText('Admin')).not.toBeVisible();
  });

  test('page title renders correctly', async ({ page }) => {
    await navigateAs(page, 'admin', '/admin/users');

    // The page should have a title element with the user console heading
    const title = page.locator('.page-title');
    await expect(title).toBeVisible({ timeout: 15000 });
  });
});
