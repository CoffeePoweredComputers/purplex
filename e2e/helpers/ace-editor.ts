/**
 * Ace Editor E2E Test Helpers
 *
 * Reliable methods for interacting with Ace editors in Playwright tests.
 *
 * ## The Problem
 *
 * The app uses vue3-ace-editor, wrapping Ace with Vue 3 v-model:
 *   ProblemSet ↔ InputSelector ↔ DebugFixInput ↔ Editor.vue ↔ VAceEditor ↔ Ace
 *
 * keyboard.type() works for single-line text but garbles multi-line code
 * (Ace's auto-indent mangles indentation). aceEditor.setValue() updates Ace
 * but doesn't reliably propagate through the Vue v-model chain.
 *
 * ## The Solution
 *
 * Find the Vue component instance that owns the editor and set its
 * `inputValue` computed (which calls emit('update:modelValue')). This
 * uses the same mechanism as the app's own reset button — Vue propagates
 * the value DOWN through props to Ace, which is the reliable direction.
 *
 * The Editor.vue _contentBackup fix ensures Ace and vue3-ace-editor stay
 * in sync regardless of which direction the value flows.
 *
 * @example
 * import { setAceEditorValue, getAceEditorValue } from '../helpers/ace-editor';
 *
 * // Set multi-line code in the debug fix editor
 * await setAceEditorValue(page, '#codeEditor', 'def foo():\n    return 42');
 *
 * // Read current editor content
 * const code = await getAceEditorValue(page, '#codeEditor');
 */

import { Page } from '@playwright/test';

/**
 * Set the value of an Ace editor via Vue's v-model chain.
 *
 * Walks up the DOM from the container to find the Vue component with
 * `inputValue` (computed setter) and `modelValue` (prop). Setting
 * `inputValue` triggers emit('update:modelValue') which Vue's
 * reactivity system properly tracks through the entire chain.
 *
 * @param page - Playwright page
 * @param containerSelector - CSS selector for the wrapper containing .ace_editor
 *   (e.g., '#codeEditor', '#promptEditor')
 * @param value - The text to set in the editor
 */
export async function setAceEditorValue(
  page: Page,
  containerSelector: string,
  value: string,
): Promise<void> {
  await page.waitForSelector(`${containerSelector} .ace_editor`, { timeout: 5000 });

  const success = await page.evaluate(
    ({ selector, newValue }) => {
      const container = document.querySelector(selector);
      if (!container) return false;

      // Walk up from the container to find the activity input component
      // (DebugFixInput, ProbeableInput, etc.) which has inputValue computed + modelValue prop
      let el: any = container;
      while (el) {
        const vcomp = el.__vueParentComponent;
        if (vcomp?.setupState && 'inputValue' in vcomp.setupState &&
            vcomp?.props && 'modelValue' in vcomp.props) {
          vcomp.setupState.inputValue = newValue;
          return true;
        }
        el = el.parentElement;
      }
      return false;
    },
    { selector: containerSelector, newValue: value },
  );

  if (!success) {
    throw new Error(`setAceEditorValue: no Vue component found above "${containerSelector}"`);
  }

  // Wait for Vue reactivity to propagate through the v-model chain
  await page.waitForTimeout(500);
}

/**
 * Get the current value of an Ace editor.
 *
 * @param page - Playwright page
 * @param containerSelector - CSS selector for the wrapper containing .ace_editor
 * @returns The editor's current text content
 */
export async function getAceEditorValue(
  page: Page,
  containerSelector: string,
): Promise<string> {
  return page.evaluate((selector) => {
    const container = document.querySelector(selector);
    const aceEl = container?.querySelector('.ace_editor') as any;
    return aceEl?.env?.editor?.getValue() ?? '';
  }, containerSelector);
}
