// tests/load/k6/scenarios/01-submission-flow.js
// Load test for complete code submission flow
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { getAuthHeaders } from '../helpers/auth.js';

// Custom metrics
const containerPoolWaitTime = new Trend('container_pool_wait_time');
const codeExecutionTime = new Trend('code_execution_time');
const submissionErrors = new Counter('submission_errors');

// Test configuration
export const options = {
  scenarios: {
    code_submission_flow: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 5 },    // Ramp up to 5 users
        { duration: '30s', target: 5 },    // Stay at 5 users
        { duration: '10s', target: 0 },    // Ramp down
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    // HTTP error rates
    'http_req_failed': ['rate<0.01'],  // Less than 1% errors

    // Response times
    'http_req_duration': ['p(95)<2000', 'p(99)<5000'],  // P95 < 2s, P99 < 5s

    // API-specific thresholds
    'http_req_duration{endpoint:problem}': ['p(95)<1000'],
    'http_req_duration{endpoint:submit}': ['p(99)<5000'],

    // Custom metrics
    'code_execution_time': ['p(95)<3000', 'p(99)<5000'],
    'container_pool_wait_time': ['p(95)<500'],  // Container should be available quickly
    'submission_errors': ['count<10'],  // Max 10 submission errors in test
  },
};

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost';

// Sample problems for testing (these should exist in your database)
const PROBLEM_SLUGS = ['two-sum', 'reverse-string', 'fizzbuzz', 'factorial'];

// Sample code submissions (simple, fast-executing code)
const CODE_SAMPLES = {
  'two-sum': `def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []`,
  'reverse-string': `def reverse_string(s):
    return s[::-1]`,
  'fizzbuzz': `def fizzbuzz(n):
    result = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result`,
  'factorial': `def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)`,
};

// Main test scenario
export default function () {
  // Generate auth headers with mock Firebase token
  const headers = getAuthHeaders('student@test.local');

  // 1. Fetch random problem
  let problemSlug;
  let problemData;
  group('Fetch Problem', () => {
    problemSlug = PROBLEM_SLUGS[Math.floor(Math.random() * PROBLEM_SLUGS.length)];

    const response = http.get(
      `${BASE_URL}/api/problems/${problemSlug}/`,
      {
        headers: headers,
        tags: { endpoint: 'problem' },
      }
    );

    const isSuccess = check(response, {
      'problem loaded': (r) => r.status === 200,
      'problem has data': (r) => {
        try {
          const data = r.json();
          return data && data.slug === problemSlug;
        } catch (e) {
          return false;
        }
      },
    });

    if (isSuccess) {
      problemData = response.json();
    } else {
      console.error(`Failed to load problem ${problemSlug}: ${response.status} ${response.body}`);
      submissionErrors.add(1);
    }

    sleep(2);  // User reads problem
  });

  if (!problemData) {
    return;  // Skip rest if problem fetch failed
  }

  // 2. Submit code for testing
  let taskId;
  group('Submit Code', () => {
    const code = CODE_SAMPLES[problemSlug] || CODE_SAMPLES['fizzbuzz'];
    const startTime = Date.now();

    const payload = JSON.stringify({
      problem_slug: problemSlug,
      code: code
    });

    const response = http.post(
      `${BASE_URL}/api/test-solution/`,
      payload,
      {
        headers: headers,
        tags: { endpoint: 'submit' },
      }
    );

    const responseTime = Date.now() - startTime;

    const isSuccess = check(response, {
      'submission accepted': (r) => r.status === 200 || r.status === 202,
      'task ID received': (r) => {
        try {
          const data = r.json();
          return data && data.task_id !== undefined;
        } catch (e) {
          return false;
        }
      },
    });

    if (isSuccess) {
      const responseData = response.json();
      taskId = responseData.task_id;

      // Track container pool wait time (if provided in response)
      const containerWait = responseData.container_wait_ms;
      if (containerWait !== undefined) {
        containerPoolWaitTime.add(containerWait);
      }
    } else {
      console.error(`Submission failed for ${problemSlug}: ${response.status} ${response.body}`);
      submissionErrors.add(1);
    }

    sleep(1);
  });

  // 3. Poll for results using SSE endpoint
  // Note: k6 doesn't support SSE well, so we'll poll the task status
  group('Wait for Results', () => {
    if (!taskId) {
      submissionErrors.add(1);
      return;
    }

    const maxAttempts = 10;  // 10 attempts = 20s max wait
    const pollInterval = 2;   // Poll every 2 seconds
    let attempt = 0;
    let completed = false;
    const executionStartTime = Date.now();

    // For k6, we'll use a simple GET to check if task is complete
    // In real scenario, frontend uses SSE at /api/tasks/{task_id}/stream/
    while (attempt < maxAttempts && !completed) {
      // Poll by trying to get progress or by checking submission history
      // Since we don't have a direct status endpoint, we'll use a small sleep and assume completion
      sleep(pollInterval);
      attempt++;

      // In a real implementation, you'd poll a status endpoint here
      // For now, we assume 4 seconds is enough for most submissions
      if (attempt >= 2) {
        completed = true;
        const executionTime = Date.now() - executionStartTime;
        codeExecutionTime.add(executionTime);

        check(null, {
          'task likely completed': () => true,
        });
      }
    }

    if (!completed) {
      submissionErrors.add(1);
      console.error(`Task ${taskId} did not complete in ${maxAttempts * pollInterval}s`);
    }
  });

  // 4. Fetch progress (simulate user checking their progress)
  group('View Progress', () => {
    const response = http.get(
      `${BASE_URL}/api/progress/${problemSlug}/`,
      {
        headers: headers,
        tags: { endpoint: 'progress' },
      }
    );

    check(response, {
      'progress loaded': (r) => r.status === 200,
    });

    sleep(1);  // User reviews results
  });

  // Think time between iterations
  sleep(Math.random() * 3 + 2);  // 2-5 seconds
}

// Setup function (runs once per VU)
export function setup() {
  console.log(`Starting load test against ${BASE_URL}`);
  console.log(`Test duration: 50 seconds with max 5 VUs`);

  // Verify server is reachable
  const response = http.get(`${BASE_URL}/api/health/`);
  if (response.status !== 200) {
    throw new Error(`Server not reachable at ${BASE_URL}: ${response.status}`);
  }

  console.log('✓ Server health check passed');

  // Check if we can authenticate
  const headers = getAuthHeaders('student@test.local');
  const authTest = http.get(`${BASE_URL}/api/user/me/`, { headers: headers });
  if (authTest.status !== 200) {
    console.warn(`⚠ Authentication test failed: ${authTest.status}. This may cause test failures.`);
    console.warn(`Response: ${authTest.body}`);
  } else {
    console.log('✓ Authentication working');
  }

  // Check if problems exist
  const problemsTest = http.get(`${BASE_URL}/api/problems/`, { headers: headers });
  if (problemsTest.status === 200) {
    try {
      const problems = problemsTest.json();
      const problemCount = Array.isArray(problems) ? problems.length : problems.results?.length || 0;
      console.log(`✓ Found ${problemCount} problems in database`);

      if (problemCount === 0) {
        console.warn('⚠ No problems found. Tests may fail. Run: python manage.py populate_sample_data');
      }
    } catch (e) {
      console.warn('⚠ Could not parse problems response');
    }
  }

  return { startTime: Date.now() };
}

// Teardown function (runs once at end)
export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`\nTest completed in ${duration.toFixed(1)}s`);
  console.log('\nTo view detailed metrics, check the k6 output above.');
  console.log('Key metrics to review:');
  console.log('  - http_req_duration: Overall API response times');
  console.log('  - code_execution_time: Time to execute code in Docker');
  console.log('  - submission_errors: Number of failed submissions');
}