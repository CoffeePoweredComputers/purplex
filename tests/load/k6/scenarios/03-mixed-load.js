// tests/load/k6/scenarios/03-mixed-load.js
// Mixed workload test - realistic usage patterns with read/write operations
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { SharedArray } from 'k6/data';
import { getAuthHeaders } from '../helpers/auth.js';

// Shared test data (loaded once, shared across VUs)
const problemSlugs = new SharedArray('problems', function () {
  return ['two-sum', 'reverse-string', 'fizzbuzz', 'factorial', 'palindrome'];
});

const codeSamples = new SharedArray('code', function () {
  return [
    'def solution(n): return n * 2',
    'def solution(s): return s[::-1]',
    'def solution(x, y): return x + y',
    'def solution(arr): return sorted(arr)',
  ];
});

export const options = {
  scenarios: {
    mixed_load: {
      executor: 'constant-vus',
      vus: 15,
      duration: '120s',  // 2 minutes
    },
  },
  thresholds: {
    'http_req_failed': ['rate<0.01'],
    'http_req_duration{operation:read}': ['p(95)<1000'],
    'http_req_duration{operation:write}': ['p(95)<3000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost';

export default function () {
  // Get auth headers with mock Firebase token
  const headers = getAuthHeaders('student@test.local');

  // Weighted random actions (simulate realistic usage)
  const action = Math.random();

  if (action < 0.70) {
    // 70% - Read operations (browsing problems)
    group('Read Operations', () => {
      // List all problems
      const problemsResponse = http.get(`${BASE_URL}/api/problems/`, {
        headers: headers,
        tags: { operation: 'read', endpoint: 'problems' },
      });

      check(problemsResponse, {
        'problems list loaded': (r) => r.status === 200,
      });

      sleep(1);

      // View specific problem
      const problemSlug = problemSlugs[Math.floor(Math.random() * problemSlugs.length)];
      const problemResponse = http.get(`${BASE_URL}/api/problems/${problemSlug}/`, {
        headers: headers,
        tags: { operation: 'read', endpoint: 'problem_detail' },
      });

      check(problemResponse, {
        'problem detail loaded': (r) => r.status === 200,
      });

      sleep(2);

      // Check user progress
      const progressResponse = http.get(`${BASE_URL}/api/progress/`, {
        headers: headers,
        tags: { operation: 'read', endpoint: 'progress' },
      });

      check(progressResponse, {
        'progress loaded': (r) => r.status === 200,
      });

      sleep(1);
    });
  } else if (action < 0.90) {
    // 20% - Moderate operations (checking hints, progress)
    group('Moderate Operations', () => {
      // View user profile
      const userResponse = http.get(`${BASE_URL}/api/user/me/`, {
        headers: headers,
        tags: { operation: 'read', endpoint: 'user_profile' },
      });

      check(userResponse, {
        'user profile loaded': (r) => r.status === 200,
      });

      sleep(1);

      // Check hints availability
      const problemSlug = problemSlugs[Math.floor(Math.random() * problemSlugs.length)];
      const hintsResponse = http.get(`${BASE_URL}/api/problems/${problemSlug}/hints/`, {
        headers: headers,
        tags: { operation: 'read', endpoint: 'hints' },
      });

      check(hintsResponse, {
        'hints check successful': (r) => r.status === 200 || r.status === 404,
      });

      sleep(2);

      // View problem sets
      const problemSetsResponse = http.get(`${BASE_URL}/api/problem-sets/`, {
        headers: headers,
        tags: { operation: 'read', endpoint: 'problem_sets' },
      });

      check(problemSetsResponse, {
        'problem sets loaded': (r) => r.status === 200,
      });

      sleep(1);
    });
  } else {
    // 10% - Write operations (code submission)
    group('Write Operations', () => {
      const problemSlug = problemSlugs[Math.floor(Math.random() * problemSlugs.length)];
      const code = codeSamples[Math.floor(Math.random() * codeSamples.length)];

      const submitResponse = http.post(
        `${BASE_URL}/api/test-solution/`,
        JSON.stringify({
          problem_slug: problemSlug,
          code: code
        }),
        {
          headers: headers,
          tags: { operation: 'write', endpoint: 'submit' },
        }
      );

      const success = check(submitResponse, {
        'submission accepted': (r) => r.status === 200 || r.status === 202,
        'task ID received': (r) => {
          try {
            return r.json('task_id') !== undefined;
          } catch (e) {
            return false;
          }
        },
      });

      if (!success) {
        console.error(`Submission failed for ${problemSlug}: ${submitResponse.status}`);
      }

      sleep(3);  // Wait a bit for execution
    });
  }

  // Think time between actions
  sleep(Math.random() * 2 + 1);
}

export function setup() {
  console.log('Starting mixed workload test');
  console.log('Simulating realistic user behavior:');
  console.log('  - 70% read operations (browsing problems)');
  console.log('  - 20% moderate operations (checking progress/hints)');
  console.log('  - 10% write operations (code submissions)');
  console.log(`Target: 15 concurrent users for 2 minutes`);

  // Verify server is reachable
  const response = http.get(`${BASE_URL}/api/health/`);
  if (response.status !== 200) {
    throw new Error(`Server not reachable at ${BASE_URL}: ${response.status}`);
  }

  console.log('✓ Server health check passed');

  // Verify authentication works
  const headers = getAuthHeaders('student@test.local');
  const authTest = http.get(`${BASE_URL}/api/user/me/`, { headers: headers });
  if (authTest.status !== 200) {
    throw new Error(`Authentication failed: ${authTest.status} - ${authTest.body}`);
  }

  console.log('✓ Authentication verified');

  return { startTime: Date.now() };
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`\nTest completed in ${duration.toFixed(1)}s`);
  console.log('\nKey metrics to review:');
  console.log('  - http_req_duration{operation:read}: Read operation response times');
  console.log('  - http_req_duration{operation:write}: Write operation response times');
  console.log('  - http_req_failed: Overall error rate');
}