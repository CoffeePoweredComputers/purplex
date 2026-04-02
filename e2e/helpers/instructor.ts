/**
 * Instructor authoring E2E test helpers.
 *
 * Common functions for creating, verifying, and cleaning up problems,
 * problem sets, and courses in instructor authoring tests.
 */

import { Page, expect } from '@playwright/test';
import { navigateAs } from './navigation';
import { apiAs } from './api';

// ---------------------------------------------------------------------------
// Navigation helpers
// ---------------------------------------------------------------------------

/** Navigate to the new problem editor, select a type, and wait for the form. */
export async function goToNewProblem(page: Page, problemType: string) {
  await navigateAs(page, 'instructor', '/instructor/problems/new');

  // Wait for the type selector to be populated (options loaded from API)
  const typeSelect = page.locator('#problem_type');
  await typeSelect.waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForTimeout(1000); // Wait for async type loading

  // Select the problem type by label (more reliable than value with async loading)
  const typeLabels: Record<string, string> = {
    mcq: 'Multiple Choice Question',
    eipl: 'Explain in Plain Language',
    prompt: 'Prompt Problem',
    debug_fix: 'Debug and Fix Code',
    probeable_code: 'Probeable Problem (Code)',
    probeable_spec: 'Probeable Problem (Explanation)',
    refute: 'Refute: Find Counterexample',
  };
  await typeSelect.selectOption({ label: typeLabels[problemType] || problemType });

  // Wait for the dynamic editor to load via Suspense
  await page.waitForTimeout(2000);
}

/** Navigate to edit an existing problem (assumes already authenticated). */
export async function goToEditProblem(page: Page, slug: string) {
  await page.goto(`/instructor/problems/${slug}/edit`);
  await page.locator('.problem-form').waitFor({ state: 'visible', timeout: 15000 });
  // Wait for editor to load
  await page.waitForTimeout(1500);
}

// ---------------------------------------------------------------------------
// Form interaction helpers
// ---------------------------------------------------------------------------

/** Fill the BasicInfoSection fields. */
export async function fillBasicInfo(
  page: Page,
  opts: { title: string; description?: string; tags?: string[] },
) {
  await page.locator('#title').fill(opts.title);

  if (opts.description) {
    await page.locator('#description').fill(opts.description);
  }

  if (opts.tags) {
    for (const tag of opts.tags) {
      await page.locator('.tag-input').fill(tag);
      await page.locator('.tag-input').press('Enter');
    }
  }
}

/** Click the save button and wait for navigation or success indicator. */
export async function saveProblem(page: Page) {
  const saveBtn = page.getByRole('button', { name: /save/i });
  await expect(saveBtn).toBeEnabled({ timeout: 5000 });
  await saveBtn.click();

  // Wait for URL to change to edit mode (slug appears in URL)
  // or for a success notification
  await page.waitForURL('**/edit', { timeout: 10000 }).catch(() => {
    // May already be in edit mode (update, not create)
  });
  await page.waitForTimeout(500);
}

/** Click the delete button, confirm the dialog, and wait for navigation. */
export async function deleteProblem(page: Page) {
  // Click the delete button in the header
  await page.getByRole('button', { name: 'Delete' }).first().click();

  // Wait for the Cancel button to appear (signals dialog is rendered)
  await page.getByRole('button', { name: 'Cancel' }).waitFor({ state: 'visible', timeout: 5000 });

  // Click the Delete button that's next to Cancel (dialog confirm, not header)
  const allDeleteBtns = page.getByRole('button', { name: 'Delete' });
  const count = await allDeleteBtns.count();
  await allDeleteBtns.nth(count - 1).click();

  // Wait for navigation away from edit page
  await page.waitForURL(/\/instructor\/problems(?!.*\/edit)/, { timeout: 10000 });
}

// ---------------------------------------------------------------------------
// API verification helpers
// ---------------------------------------------------------------------------

/** Verify a problem exists via the instructor API and return its data. */
export async function verifyProblemExists(page: Page, slug: string) {
  const result = await apiAs(page, 'instructor', 'GET', `/api/instructor/problems/${slug}/`);
  expect(result.status).toBe(200);
  expect(result.data).toBeTruthy();
  expect(result.data.slug).toBe(slug);
  return result.data;
}

/** Verify a problem was deleted (API returns 404). */
export async function verifyProblemDeleted(page: Page, slug: string) {
  const result = await apiAs(page, 'instructor', 'GET', `/api/instructor/problems/${slug}/`);
  expect(result.status).toBe(404);
}

/** Delete a problem via API (for cleanup in afterEach). */
export async function cleanupProblem(page: Page, slug: string) {
  await apiAs(page, 'instructor', 'DELETE', `/api/instructor/problems/${slug}/`);
}

/** Delete a problem set via API (for cleanup). */
export async function cleanupProblemSet(page: Page, slug: string) {
  await apiAs(page, 'instructor', 'DELETE', `/api/instructor/problem-sets/${slug}/`);
}

/** Delete a course via API (for cleanup). */
export async function cleanupCourse(page: Page, courseId: string) {
  await apiAs(page, 'instructor', 'DELETE', `/api/instructor/courses/${courseId}/`);
}

// ---------------------------------------------------------------------------
// Test case helpers
// ---------------------------------------------------------------------------

/** Add a test case row and fill its parameters. */
export async function addTestCase(
  page: Page,
  inputs: string[],
  expectedOutput: string,
) {
  // Click "Add Test Case"
  await page.locator('.test-actions .btn-secondary').click();
  await page.waitForTimeout(300);

  // Get the last test case row
  const testCases = page.locator('.test-case');
  const lastCase = testCases.last();

  // Fill parameter inputs (inputs are in order)
  const paramInputs = lastCase.locator('.smart-parameters .param-input');
  for (let i = 0; i < inputs.length; i++) {
    await paramInputs.nth(i).fill(inputs[i]);
  }

  // Fill expected output (last param-input in the output section)
  const outputInput = lastCase.locator('.output-field-container .param-input');
  await outputInput.fill(expectedOutput);
}

/** Extract slug from the current URL after saving a problem. */
export async function getSlugFromUrl(page: Page): Promise<string> {
  const url = page.url();
  const match = url.match(/\/problems\/([^/]+)\/edit/);
  return match ? match[1] : '';
}

/** Generate a unique title for test isolation. */
export function uniqueTitle(prefix: string): string {
  return `${prefix} ${Date.now()}`;
}
