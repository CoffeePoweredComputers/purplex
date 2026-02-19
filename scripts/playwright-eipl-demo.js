/**
 * Playwright Demo Script for EiPL (Explain in Plain Language) Questions
 *
 * This script demonstrates three different quality levels of EiPL responses
 * using the "Valid Parentheses" problem:
 *
 * 1. HIGH-LEVEL (too vague) - Gets low score
 * 2. LINE-BY-LINE (too mechanical) - Gets medium score
 * 3. FULLY CORRECT (proper understanding) - Gets high score
 *
 * Reference Solution being explained:
 * ```python
 * def is_valid(s):
 *     stack = []
 *     mapping = {')': '(', '}': '{', ']': '['}
 *
 *     for char in s:
 *         if char in mapping:
 *             if not stack or stack.pop() != mapping[char]:
 *                 return False
 *         else:
 *             stack.append(char)
 *
 *     return len(stack) == 0
 * ```
 *
 * Usage:
 *   node scripts/playwright-eipl-demo.js [response-type]
 *
 *   response-type: "high-level" | "line-by-line" | "correct" (default: "correct")
 *
 * Prerequisites:
 *   npm install playwright
 */

const { firefox } = require('playwright');

// =============================================================================
// Configuration
// =============================================================================

const CONFIG = {
  baseUrl: 'http://localhost:5173',
  courseId: 'ENGGEN131',
  problemSetSlug: 'demo-problem-set',
  problemIndex: 3,  // ?p=3

  // Test credentials (mock auth in dev)
  credentials: {
    email: 'test@example.com',
    password: 'test123'
  },

  // Typing simulation settings
  typing: {
    minDelay: 30,  // ms between keystrokes (min)
    maxDelay: 80,  // ms between keystrokes (max)
    pauseAfterPunctuation: 200, // ms pause after . , ! ?
    pauseAfterNewline: 300,     // ms pause after newline
  },

  // Screenshot settings
  screenshots: {
    enabled: true,
    outputDir: './demo-screenshots',
  },

  // Timeouts
  timeouts: {
    navigation: 30000,
    submission: 60000,
  }
};

// =============================================================================
// Response Templates
// =============================================================================

const RESPONSES = {
  /**
   * HIGH-LEVEL RESPONSE
   *
   * Problem: Too vague, doesn't explain the actual mechanism
   * Expected Score: ~30-50% (fails to show understanding of implementation)
   */
  'high-level': `Validates whether a string of parentheses, brackets, and curly braces are properly matched and nested.`,

  /**
   * LINE-BY-LINE RESPONSE
   *
   * Problem: Mechanical code translation, doesn't show algorithmic understanding
   * Expected Score: Passes correctness, fails segmentation (no high-level understanding)
   */
  'line-by-line': `Create an empty list called x. Create a dictionary called m that maps closing brackets to opening brackets. Loop through each character c in the string s. Check if c is a key in m. If x is empty or the popped element doesn't equal m[c], return False. Otherwise append c to x. Return True if the length of x is 0, otherwise return False.`,

  /**
   * FULLY CORRECT RESPONSE
   *
   * Shows: Algorithmic understanding, explains WHY not just WHAT
   * Expected Score: ~90-100%
   */
  'correct': `This function validates whether a string contains properly matched and nested parentheses, brackets, and braces.

The algorithm uses a stack-based approach: opening brackets are pushed onto a stack, and when a closing bracket is encountered, we verify it matches the most recently opened bracket by popping from the stack.

A mapping dictionary provides O(1) lookup to find which opening bracket corresponds to each closing bracket. This handles the three bracket types: (), [], and {}.

For each character in the input string:
- If it's a closing bracket, we check two things: the stack must not be empty (there must be an unmatched opening bracket), and the top of the stack must be the matching opening bracket. If either condition fails, the parentheses are invalid.
- If it's an opening bracket, we push it onto the stack to remember it needs to be closed later.

Finally, we verify the stack is empty - any remaining items would indicate unclosed opening brackets.

This approach correctly handles nested brackets like "({[]})" because the stack's LIFO property ensures the most recent opening bracket is matched first.`
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Sleep for specified milliseconds
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Calculate typing delay for a character
 */
function getTypingDelay(char) {
  let delay = Math.random() * (CONFIG.typing.maxDelay - CONFIG.typing.minDelay) + CONFIG.typing.minDelay;

  if (['.', ',', '!', '?', ':'].includes(char)) {
    delay += CONFIG.typing.pauseAfterPunctuation;
  } else if (char === '\n') {
    delay += CONFIG.typing.pauseAfterNewline;
  }

  return delay;
}

/**
 * Type text with human-like delays
 */
async function typeWithDelay(page, selector, text) {
  await page.click(selector);

  for (const char of text) {
    await page.keyboard.type(char);
    await sleep(getTypingDelay(char));
  }
}

/**
 * Type into Ace Editor (requires special handling)
 */
async function typeIntoAceEditor(page, containerSelector, text) {
  // Click to focus the Ace editor
  await page.click(containerSelector);
  await sleep(100);

  // Type character by character with realistic delays
  for (const char of text) {
    await page.keyboard.type(char);
    await sleep(getTypingDelay(char));
  }
}

/**
 * Take a screenshot with timestamp
 */
async function takeScreenshot(page, name) {
  if (!CONFIG.screenshots.enabled) return;

  const fs = require('fs');
  const path = require('path');

  // Ensure output directory exists
  if (!fs.existsSync(CONFIG.screenshots.outputDir)) {
    fs.mkdirSync(CONFIG.screenshots.outputDir, { recursive: true });
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `${timestamp}-${name}.png`;
  const filepath = path.join(CONFIG.screenshots.outputDir, filename);

  await page.screenshot({ path: filepath, fullPage: true });
  console.log(`📸 Screenshot saved: ${filename}`);
}

/**
 * Wait for feedback to appear after submission
 */
async function waitForFeedback(page) {
  console.log('⏳ Waiting for feedback...');

  // Wait for the loading state to disappear and results to appear
  await page.waitForFunction(() => {
    const loadingPanel = document.querySelector('.generating-feedback-panel');
    const hasResults = document.querySelector('.feedback-container .variant-card') ||
                       document.querySelector('.feedback-container .comprehension-panel');
    return !loadingPanel && hasResults;
  }, { timeout: CONFIG.timeouts.submission });

  // Additional wait for animations to settle
  await sleep(1000);
}

// =============================================================================
// Main Demo Flow
// =============================================================================

async function runDemo(responseType = 'correct') {
  console.log('🚀 Starting EiPL Demo Script (Playwright + Firefox)');
  console.log(`📝 Response Type: ${responseType}`);
  console.log('─'.repeat(50));

  const response = RESPONSES[responseType];
  if (!response) {
    console.error(`❌ Invalid response type: ${responseType}`);
    console.log('Valid options: high-level, line-by-line, correct');
    process.exit(1);
  }

  // Launch your system Firefox
  const browser = await firefox.launch({
    channel: 'firefox',  // Uses your installed Firefox
    headless: false,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });

  const page = await context.newPage();

  try {
    // =========================================================================
    // Step 1: Navigate to Login Page
    // =========================================================================
    console.log('\n📍 Step 1: Navigating to login page...');
    await page.goto(CONFIG.baseUrl, {
      waitUntil: 'networkidle',
      timeout: CONFIG.timeouts.navigation
    });
    await takeScreenshot(page, '01-login-page');

    // =========================================================================
    // Step 2: Login
    // =========================================================================
    console.log('📍 Step 2: Logging in...');

    // Fill in credentials
    await page.waitForSelector('#email');
    await typeWithDelay(page, '#email', CONFIG.credentials.email);
    await typeWithDelay(page, '#psw', CONFIG.credentials.password);

    await takeScreenshot(page, '02-credentials-entered');

    // Click login button
    await page.click('.login-btns button:first-of-type');

    // Wait for navigation to home
    await page.waitForURL('**/home', { timeout: CONFIG.timeouts.navigation });

    console.log('✅ Logged in successfully');
    await takeScreenshot(page, '03-home-page');

    // =========================================================================
    // Step 3: Navigate directly to the EiPL problem
    // =========================================================================
    const problemUrl = `${CONFIG.baseUrl}/courses/${CONFIG.courseId}/problem-set/${CONFIG.problemSetSlug}?p=${CONFIG.problemIndex}`;
    console.log(`📍 Step 3: Navigating to problem: ${problemUrl}`);

    await page.goto(problemUrl, {
      waitUntil: 'networkidle',
      timeout: CONFIG.timeouts.navigation
    });

    // Wait for problems to load
    await page.waitForSelector('.problem-set-container', {
      timeout: CONFIG.timeouts.navigation
    });

    await sleep(1000); // Wait for problem to render
    console.log('✅ Problem loaded');
    await takeScreenshot(page, '04-problem-loaded');

    // =========================================================================
    // Step 4: View the Code
    // =========================================================================
    console.log('📍 Step 4: Viewing the reference code...');

    // The code editor should be visible with the reference solution
    await page.waitForSelector('#code-editor .ace_editor', {
      timeout: CONFIG.timeouts.navigation
    });

    await sleep(500);
    await takeScreenshot(page, '05-code-visible');

    // =========================================================================
    // Step 5: Type the EiPL Response
    // =========================================================================
    console.log('📍 Step 5: Typing EiPL response...');
    console.log(`   Response length: ${response.length} characters`);
    console.log(`   Estimated time: ~${Math.round(response.length * 50 / 1000)}s`);

    // Find the prompt editor (EiPL input area)
    await page.waitForSelector('#promptEditor', {
      timeout: CONFIG.timeouts.navigation
    });

    // Clear existing content first
    await page.click('#promptEditor');
    await sleep(100);
    await page.keyboard.press('Control+A');
    await page.keyboard.press('Backspace');
    await sleep(100);

    // Type into the Ace editor
    await typeIntoAceEditor(page, '#promptEditor', response);

    console.log('✅ Response typed');
    await takeScreenshot(page, '06-response-typed');

    // =========================================================================
    // Step 6: Submit
    // =========================================================================
    console.log('📍 Step 6: Submitting response...');

    // Wait for submit button to be enabled
    await page.waitForSelector('#submitButton:not(:disabled)');
    await page.click('#submitButton');

    await takeScreenshot(page, '07-submitting');

    // =========================================================================
    // Step 7: Wait for Feedback
    // =========================================================================
    console.log('📍 Step 7: Waiting for AI feedback...');

    await waitForFeedback(page);

    console.log('✅ Feedback received');
    await takeScreenshot(page, '08-feedback-received');

    // =========================================================================
    // Step 9: Display Results Summary
    // =========================================================================
    console.log('\n' + '═'.repeat(50));
    console.log('📊 DEMO COMPLETE');
    console.log('═'.repeat(50));
    console.log(`Response Type: ${responseType}`);
    console.log(`Screenshots saved to: ${CONFIG.screenshots.outputDir}`);
    console.log('═'.repeat(50));

    // Keep browser open for manual inspection
    console.log('\n⏸️  Browser kept open for inspection.');
    console.log('   Press Ctrl+C to close.');

    // Wait indefinitely (until user closes)
    await new Promise(() => {});

  } catch (error) {
    console.error('❌ Demo failed:', error.message);
    await takeScreenshot(page, 'error-state');
    throw error;
  }
}

// =============================================================================
// CLI Entry Point
// =============================================================================

const args = process.argv.slice(2);
const responseType = args[0] || 'correct';

// Show help if invalid response type
if (args[0] === '--help' || args[0] === '-h') {
  console.log('EiPL Demo Script - Valid Parentheses Problem');
  console.log('─'.repeat(50));
  console.log('\nUsage: node playwright-eipl-demo.js [response-type]\n');
  console.log('Response types:');
  console.log('  high-level   - Vague, high-level description (~30-50% score)');
  console.log('  line-by-line - Mechanical code translation (~50-70% score)');
  console.log('  correct      - Full algorithmic understanding (~90-100% score)');
  console.log('\nExamples:');
  console.log('  node playwright-eipl-demo.js correct');
  console.log('  node playwright-eipl-demo.js high-level');
  process.exit(0);
}

if (!RESPONSES[responseType]) {
  console.error(`❌ Invalid response type: ${responseType}`);
  console.log('Valid options: high-level, line-by-line, correct');
  console.log('Run with --help for more info');
  process.exit(1);
}

runDemo(responseType).catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
