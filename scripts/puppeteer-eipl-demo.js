/**
 * Puppeteer Demo Script for EiPL (Explain in Plain Language) Questions
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
 *   node scripts/puppeteer-eipl-demo.js [response-type]
 *
 *   response-type: "high-level" | "line-by-line" | "correct" (default: "correct")
 *
 * Prerequisites:
 *   npm install puppeteer
 */

const puppeteer = require('puppeteer');

// Firefox support requires puppeteer with Firefox installed
// Run: npx puppeteer browsers install firefox

// =============================================================================
// Configuration
// =============================================================================

const CONFIG = {
  baseUrl: 'http://localhost:5173',
  problemSetSlug: 'introduction-to-programming', // Contains valid-parentheses
  problemSlug: 'valid-parentheses',

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
    feedbackPoll: 2000,
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
  'high-level': `This function checks if a string of parentheses is valid.

It uses a stack data structure to keep track of opening brackets.

When it sees a closing bracket, it checks if it matches the most recent opening bracket.

The function returns True if all brackets are properly matched and False otherwise.`,

  /**
   * LINE-BY-LINE RESPONSE
   *
   * Problem: Mechanical code translation, doesn't show algorithmic understanding
   * Expected Score: ~50-70% (shows some understanding but misses the "why")
   */
  'line-by-line': `Line 1: Define a function called is_valid that takes a parameter s.

Line 2: Create an empty list called stack.

Line 3: Create a dictionary called mapping that maps closing brackets to their corresponding opening brackets.

Line 5: Start a for loop that iterates through each character in the string s.

Line 6: Check if the current character is a key in the mapping dictionary (meaning it's a closing bracket).

Line 7-8: If the stack is empty or the popped element doesn't match the expected opening bracket, return False.

Line 9-10: Otherwise (if it's an opening bracket), append it to the stack.

Line 12: After processing all characters, return True if the stack is empty, False otherwise.`,

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
 * Simulate human-like typing with variable delays
 */
async function typeWithDelay(page, selector, text) {
  await page.focus(selector);

  for (const char of text) {
    // Calculate delay based on character type
    let delay = Math.random() * (CONFIG.typing.maxDelay - CONFIG.typing.minDelay) + CONFIG.typing.minDelay;

    if (['.', ',', '!', '?', ':'].includes(char)) {
      delay += CONFIG.typing.pauseAfterPunctuation;
    } else if (char === '\n') {
      delay += CONFIG.typing.pauseAfterNewline;
    }

    await page.keyboard.type(char);
    await sleep(delay);
  }
}

/**
 * Type into Ace Editor (requires special handling)
 */
async function typeIntoAceEditor(page, containerSelector, text) {
  // Click to focus the Ace editor
  await page.click(containerSelector);
  await sleep(100);

  // Find the textarea that Ace uses for input
  const textareaSelector = `${containerSelector} textarea.ace_text-input`;

  // Type character by character with realistic delays
  for (const char of text) {
    let delay = Math.random() * (CONFIG.typing.maxDelay - CONFIG.typing.minDelay) + CONFIG.typing.minDelay;

    if (['.', ',', '!', '?', ':'].includes(char)) {
      delay += CONFIG.typing.pauseAfterPunctuation;
    } else if (char === '\n') {
      delay += CONFIG.typing.pauseAfterNewline;
    }

    await page.type(textareaSelector, char);
    await sleep(delay);
  }
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
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
  console.log('🚀 Starting EiPL Demo Script');
  console.log(`📝 Response Type: ${responseType}`);
  console.log('─'.repeat(50));

  const response = RESPONSES[responseType];
  if (!response) {
    console.error(`❌ Invalid response type: ${responseType}`);
    console.log('Valid options: high-level, line-by-line, correct');
    process.exit(1);
  }

  const browser = await puppeteer.launch({
    browser: 'firefox',  // Use Firefox instead of Chromium
    headless: false,     // Set to true for automated runs
    defaultViewport: { width: 1440, height: 900 },
  });

  const page = await browser.newPage();

  try {
    // =========================================================================
    // Step 1: Navigate to Login Page
    // =========================================================================
    console.log('\n📍 Step 1: Navigating to login page...');
    await page.goto(CONFIG.baseUrl, {
      waitUntil: 'networkidle2',
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
    await page.waitForNavigation({
      waitUntil: 'networkidle2',
      timeout: CONFIG.timeouts.navigation
    });

    console.log('✅ Logged in successfully');
    await takeScreenshot(page, '03-home-page');

    // =========================================================================
    // Step 3: Navigate to Problem Set
    // =========================================================================
    console.log(`📍 Step 3: Navigating to problem set: ${CONFIG.problemSetSlug}...`);

    await page.goto(`${CONFIG.baseUrl}/problem-set/${CONFIG.problemSetSlug}`, {
      waitUntil: 'networkidle2',
      timeout: CONFIG.timeouts.navigation
    });

    // Wait for problems to load
    await page.waitForSelector('.problem-set-container', {
      timeout: CONFIG.timeouts.navigation
    });

    console.log('✅ Problem set loaded');
    await takeScreenshot(page, '04-problem-set');

    // =========================================================================
    // Step 4: Navigate to Valid Parentheses Problem (if not first)
    // =========================================================================
    console.log('📍 Step 4: Finding Valid Parentheses problem...');

    // Check if we need to navigate to the correct problem
    // The problem set URL can include a ?problem= query param
    await page.goto(
      `${CONFIG.baseUrl}/problem-set/${CONFIG.problemSetSlug}?problem=${CONFIG.problemSlug}`,
      { waitUntil: 'networkidle2', timeout: CONFIG.timeouts.navigation }
    );

    await sleep(1000); // Wait for problem to render
    await takeScreenshot(page, '05-valid-parentheses-problem');

    // =========================================================================
    // Step 5: View the Code
    // =========================================================================
    console.log('📍 Step 5: Viewing the reference code...');

    // The code editor should be visible with the reference solution
    await page.waitForSelector('#code-editor .ace_editor', {
      timeout: CONFIG.timeouts.navigation
    });

    await sleep(500);
    await takeScreenshot(page, '06-code-visible');

    // =========================================================================
    // Step 6: Type the EiPL Response
    // =========================================================================
    console.log('📍 Step 6: Typing EiPL response...');
    console.log(`   Response length: ${response.length} characters`);
    console.log(`   Estimated time: ~${Math.round(response.length * 50 / 1000)}s`);

    // Find the prompt editor (EiPL input area)
    await page.waitForSelector('#promptEditor', {
      timeout: CONFIG.timeouts.navigation
    });

    // Type into the Ace editor
    await typeIntoAceEditor(page, '#promptEditor', response);

    console.log('✅ Response typed');
    await takeScreenshot(page, '07-response-typed');

    // =========================================================================
    // Step 7: Submit
    // =========================================================================
    console.log('📍 Step 7: Submitting response...');

    // Click submit button
    await page.waitForSelector('#submitButton:not(:disabled)');
    await page.click('#submitButton');

    await takeScreenshot(page, '08-submitting');

    // =========================================================================
    // Step 8: Wait for Feedback
    // =========================================================================
    console.log('📍 Step 8: Waiting for AI feedback...');

    await waitForFeedback(page);

    console.log('✅ Feedback received');
    await takeScreenshot(page, '09-feedback-received');

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

// Validate response type
if (!RESPONSES[responseType]) {
  console.log('EiPL Demo Script - Valid Parentheses Problem');
  console.log('─'.repeat(50));
  console.log('\nUsage: node puppeteer-eipl-demo.js [response-type]\n');
  console.log('Response types:');
  console.log('  high-level   - Vague, high-level description (~30-50% score)');
  console.log('  line-by-line - Mechanical code translation (~50-70% score)');
  console.log('  correct      - Full algorithmic understanding (~90-100% score)');
  console.log('\nExamples:');
  console.log('  node puppeteer-eipl-demo.js correct');
  console.log('  node puppeteer-eipl-demo.js high-level');
  process.exit(0);
}

runDemo(responseType).catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
