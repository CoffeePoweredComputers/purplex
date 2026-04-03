/**
 * E2E Tests: Instructor MCQ Problem Authoring
 *
 * Tests the full CRUD lifecycle for Multiple Choice Question problems:
 * create via UI → verify via API → edit → verify → delete → verify.
 *
 * MCQ is the simplest problem type (no test cases, no code editor),
 * making it a good starting point for authoring tests.
 */

import { test, expect } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';
import {
  goToNewProblem,
  goToEditProblem,
  fillBasicInfo,
  saveProblem,
  deleteProblem,
  verifyProblemExists,
  verifyProblemDeleted,
  cleanupProblem,
  getSlugFromUrl,
  uniqueTitle,
} from '../helpers/instructor';

test.describe('MCQ Problem Authoring', () => {
  // Track created slugs for cleanup
  const createdSlugs: string[] = [];

  test.afterEach(async ({ page }) => {
    // Clean up any problems created during the test
    for (const slug of createdSlugs) {
      await cleanupProblem(page, slug).catch(() => {});
    }
    createdSlugs.length = 0;
  });

  test('create MCQ with 4 options and 1 correct answer', async ({ page }) => {
    const title = uniqueTitle('E2E MCQ Create');

    await goToNewProblem(page, 'mcq');

    // Fill basic info
    await fillBasicInfo(page, { title, description: 'Test MCQ problem' });

    // Fill question text
    await page.getByPlaceholder('Enter the question').fill('What is 2 + 2?');

    // The editor starts with 1 option — add 3 more for 4 total
    const addBtn = page.getByRole('button', { name: '+ Add Option' });
    await addBtn.click();
    await expect(page.getByPlaceholder('Enter option text')).toHaveCount(2, { timeout: 3000 });
    await addBtn.click();
    await expect(page.getByPlaceholder('Enter option text')).toHaveCount(3, { timeout: 3000 });
    await addBtn.click();
    await expect(page.getByPlaceholder('Enter option text')).toHaveCount(4, { timeout: 3000 });

    const optionInputs = page.getByPlaceholder('Enter option text');

    // Fill option texts
    await optionInputs.nth(0).fill('3');
    await optionInputs.nth(1).fill('4');
    await optionInputs.nth(2).fill('5');
    await optionInputs.nth(3).fill('22');

    // Mark option B (index 1) as correct
    await page.getByRole('radio', { name: 'Correct Answer' }).nth(1).click();

    // Capture the API response to get the created slug
    const responsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/instructor/problems') && resp.request().method() === 'POST',
      { timeout: 10000 },
    );

    // Save
    await saveProblem(page);

    // Get slug from API response
    const response = await responsePromise;
    expect(response.status()).toBe(201);
    const responseBody = await response.json();
    const slug = responseBody.slug;
    expect(slug).toBeTruthy();
    createdSlugs.push(slug);

    // Verify via API
    const data = await verifyProblemExists(page, slug);
    expect(data.title).toBe(title);
    expect(data.problem_type).toBe('mcq');
    expect(data.question_text).toBe('What is 2 + 2?');
    expect(data.options).toHaveLength(4);

    // Verify correct answer
    const correctOption = data.options.find((o: any) => o.is_correct);
    expect(correctOption).toBeTruthy();
    expect(correctOption.text).toBe('4');
  });

  test('create multi-select MCQ with 2 correct answers', async ({ page }) => {
    const title = uniqueTitle('E2E MCQ MultiSelect');

    await goToNewProblem(page, 'mcq');
    await fillBasicInfo(page, { title });
    await page.getByPlaceholder('Enter the question').fill('Select all prime numbers');

    // Add options to get 4 total (starts with 1)
    const addBtn = page.getByRole('button', { name: '+ Add Option' });
    await addBtn.click();
    await addBtn.click();
    await addBtn.click();
    await expect(page.getByPlaceholder('Enter option text')).toHaveCount(4, { timeout: 3000 });

    const optionInputs = page.getByPlaceholder('Enter option text');
    await optionInputs.nth(0).fill('2');
    await optionInputs.nth(1).fill('4');
    await optionInputs.nth(2).fill('7');
    await optionInputs.nth(3).fill('9');

    // Enable multi-select if there's a toggle
    const multiSelectToggle = page.locator('input[type="checkbox"]').filter({ hasText: /multiple/i });
    if (await multiSelectToggle.isVisible().catch(() => false)) {
      await multiSelectToggle.check();
    }

    // Mark options A and C as correct (indices 0 and 2)
    await page.getByRole('radio', { name: 'Correct Answer' }).nth(0).click();
    await page.getByRole('radio', { name: 'Correct Answer' }).nth(2).click();

    const responsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/instructor/problems') && resp.request().method() === 'POST',
      { timeout: 10000 },
    );
    await saveProblem(page);
    const response = await responsePromise;
    expect(response.status()).toBe(201);
    const slug = (await response.json()).slug;
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.options).toHaveLength(4);
  });

  test('save is blocked without question text', async ({ page }) => {
    await goToNewProblem(page, 'mcq');
    await fillBasicInfo(page, { title: uniqueTitle('E2E MCQ NoQuestion') });

    // Fill option text and mark correct, but DON'T fill question
    await page.getByPlaceholder('Enter option text').nth(0).fill('Option A');
    await page.getByRole('button', { name: '+ Add Option' }).click();
    await page.getByPlaceholder('Enter option text').nth(1).fill('Option B');
    await page.getByRole('radio', { name: 'Correct Answer' }).nth(0).click();

    // Save button should be disabled (no question text)
    const saveBtn = page.getByRole('button', { name: /save/i });
    await expect(saveBtn).toBeDisabled({ timeout: 3000 });
  });

  test('remove button is disabled when only 1 option exists', async ({ page }) => {
    await goToNewProblem(page, 'mcq');

    // Editor starts with 1 option — remove button should be disabled
    const removeBtn = page.getByRole('button', { name: '×' }).first();
    await expect(removeBtn).toBeDisabled();
  });

  test('validation warning shown when no correct answer is marked', async ({ page }) => {
    await goToNewProblem(page, 'mcq');

    // The validation warning should be visible by default (no correct answer marked)
    const warning = page.locator('text=Please mark one option as the correct answer');
    await expect(warning).toBeVisible({ timeout: 5000 });
  });

  test('edit MCQ: change correct answer and verify persistence', async ({ page }) => {
    const title = uniqueTitle('E2E MCQ Edit');

    // Navigate first so apiAs can use same-origin fetch
    await navigateAs(page, 'instructor', '/instructor/problems');
    await page.waitForTimeout(500);

    // Create via API for speed
    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problems/', {
      title,
      description: 'Test edit',
      problem_type: 'mcq',
      question_text: 'Capital of France?',
      options: [
        { id: 'a', text: 'London', is_correct: false },
        { id: 'b', text: 'Paris', is_correct: true },
        { id: 'c', text: 'Berlin', is_correct: false },
      ],
    });
    expect(createResult.status).toBe(201);
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    // Navigate to edit
    await goToEditProblem(page, slug);

    // Type selector should be disabled
    await expect(page.locator('#problem_type')).toBeDisabled();

    // Change correct answer from B to C (index 2)
    await page.getByRole('radio', { name: 'Correct Answer' }).nth(2).click();

    // Save
    await saveProblem(page);

    // Verify via API
    const data = await verifyProblemExists(page, slug);
    const correctOption = data.options.find((o: any) => o.is_correct);
    expect(correctOption.text).toBe('Berlin');
  });

  test('edit MCQ: change question and option text', async ({ page }) => {
    const title = uniqueTitle('E2E MCQ EditText');

    await navigateAs(page, 'instructor', '/instructor/problems');
    await page.waitForTimeout(500);

    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problems/', {
      title,
      problem_type: 'mcq',
      question_text: 'Original question',
      options: [
        { id: 'a', text: 'Original A', is_correct: true },
        { id: 'b', text: 'Original B', is_correct: false },
      ],
    });
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);

    // Change question text
    await page.getByPlaceholder('Enter the question').fill('Updated question');
    // Change option text
    await page.getByPlaceholder('Enter option text').nth(0).fill('Updated A');

    await saveProblem(page);

    const data = await verifyProblemExists(page, slug);
    expect(data.question_text).toBe('Updated question');
    expect(data.options[0].text).toBe('Updated A');
  });

  test('edit MCQ: add option to existing problem', async ({ page }) => {
    const title = uniqueTitle('E2E MCQ AddOpt');

    await navigateAs(page, 'instructor', '/instructor/problems');
    await page.waitForTimeout(500);

    const createResult = await apiAs(page, 'instructor', 'POST', '/api/instructor/problems/', {
      title,
      problem_type: 'mcq',
      question_text: 'Test question',
      options: [
        { id: 'a', text: 'A', is_correct: true },
        { id: 'b', text: 'B', is_correct: false },
      ],
    });
    const slug = createResult.data.slug;
    createdSlugs.push(slug);

    await goToEditProblem(page, slug);

    // Should start with 2 options
    await expect(page.getByPlaceholder('Enter option text')).toHaveCount(2);

    // Add a third
    await page.getByRole('button', { name: '+ Add Option' }).click();
    await expect(page.getByPlaceholder('Enter option text')).toHaveCount(3);
    await page.getByPlaceholder('Enter option text').nth(2).fill('New C');

    await saveProblem(page);

    const data = await verifyProblemExists(page, slug);
    expect(data.options).toHaveLength(3);
    expect(data.options[2].text).toBe('New C');
  });

  test('max 6 options disables Add Option button', async ({ page }) => {
    await goToNewProblem(page, 'mcq');

    const addBtn = page.getByRole('button', { name: '+ Add Option' });

    // Start with 1, add 5 more to reach 6
    for (let i = 0; i < 5; i++) {
      await addBtn.click();
      await page.waitForTimeout(200);
    }

    await expect(page.getByPlaceholder('Enter option text')).toHaveCount(6);
    await expect(addBtn).toBeDisabled();
  });

  test('tags persist after save', async ({ page }) => {
    const title = uniqueTitle('E2E MCQ Tags');

    await goToNewProblem(page, 'mcq');
    await fillBasicInfo(page, { title, description: 'Tag test', tags: ['loops', 'basics'] });
    await page.getByPlaceholder('Enter the question').fill('Tag test question');

    await page.getByRole('button', { name: '+ Add Option' }).click();
    await page.getByPlaceholder('Enter option text').nth(0).fill('A');
    await page.getByPlaceholder('Enter option text').nth(1).fill('B');
    await page.getByRole('radio', { name: 'Correct Answer' }).nth(0).click();

    const responsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/instructor/problems') && resp.request().method() === 'POST',
      { timeout: 10000 },
    );
    await saveProblem(page);
    const response = await responsePromise;
    const slug = (await response.json()).slug;
    createdSlugs.push(slug);

    const data = await verifyProblemExists(page, slug);
    expect(data.tags).toContain('loops');
    expect(data.tags).toContain('basics');
  });

  test('delete MCQ and verify removal', async ({ page }) => {
    const title = uniqueTitle('E2E MCQ Delete');

    // Create via UI
    await goToNewProblem(page, 'mcq');
    await fillBasicInfo(page, { title, description: 'To be deleted' });
    await page.getByPlaceholder('Enter the question').fill('Throwaway?');

    await page.getByRole('button', { name: '+ Add Option' }).click();
    await page.getByPlaceholder('Enter option text').nth(0).fill('Yes');
    await page.getByPlaceholder('Enter option text').nth(1).fill('No');
    await page.getByRole('radio', { name: 'Correct Answer' }).nth(0).click();

    // Save and capture slug
    const responsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/instructor/problems') && resp.request().method() === 'POST',
      { timeout: 10000 },
    );
    await saveProblem(page);
    const response = await responsePromise;
    const slug = (await response.json()).slug;

    // Navigate to edit (reuses existing session — no re-auth)
    await goToEditProblem(page, slug);

    // Delete
    await deleteProblem(page);

    // Verify via API — should be 404
    await verifyProblemDeleted(page, slug);
  });
});
