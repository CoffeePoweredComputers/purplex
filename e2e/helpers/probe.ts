import { expect, Page } from '@playwright/test';
import { probe } from './selectors';

/**
 * Probe panel call line (activities/inputs/shared/ProbePanel.vue).
 *
 * The student edits only the argument list between `name(` and `)`: one
 * contenteditable #probe-args holding Python-style arguments, positional or
 * keyword (`7`, `n=7`, `["a", "b"], prefix="x"`).
 */

/**
 * Replace the argument list with `text` and wait until the editable holds it.
 *
 * Locator.fill selects the current contents and inserts the text as one input
 * event, which a contenteditable accepts, brackets and quotes included.
 */
export async function fillProbeArgs(page: Page, text: string): Promise<void> {
  const line = page.locator(probe.argsLine);
  await line.fill(text);
  await expect(line).toHaveJSProperty('textContent', text);
}

/** Text of the result slot after the arrow ('?' until a result). */
export async function readProbeResult(page: Page): Promise<string> {
  return (await page.locator(probe.result).innerText()).trim();
}

/** Text of the remaining-probe badge, e.g. '· ∞' or '· 2 left'. */
export async function readBadge(page: Page): Promise<string> {
  return (await page.locator(probe.badge).innerText()).trim();
}

/**
 * Assert the error shown for one argument. `name` is a parameter name, or
 * 'line' for a line-level error (unknown, duplicate, extra or empty argument).
 */
export async function expectArgError(page: Page, name: string, text: string | RegExp): Promise<void> {
  await expect(page.locator(probe.fieldError(name))).toHaveText(text);
}

/**
 * Assert whether the argument list can be edited. Locked means
 * contenteditable="false" plus aria-disabled, as when probes are exhausted.
 */
export async function expectArgsEditable(page: Page, editable: boolean): Promise<void> {
  const line = page.locator(probe.argsLine);
  if (editable) {
    // The e2e project is Chromium-only, which supports plaintext-only; the 'true'
    // fallback for other browsers is covered in Vitest (probeArgsLine.test.ts)
    await expect(line).toHaveAttribute('contenteditable', 'plaintext-only');
    await expect(line).toBeEnabled();
  } else {
    await expect(line).toHaveAttribute('contenteditable', 'false');
    await expect(line).toHaveAttribute('aria-disabled', 'true');
    await expect(line).toBeDisabled();
  }
}

/** The placeholder actually painted in the empty call line (CSS :empty::before). */
export async function readArgsPlaceholder(page: Page): Promise<string> {
  return page.locator(probe.argsLine).evaluate((el) => {
    const content = getComputedStyle(el, '::before').content;
    // 'none' when the line is not empty; otherwise a quoted CSS string
    return content === 'none' ? '' : JSON.parse(content);
  });
}
