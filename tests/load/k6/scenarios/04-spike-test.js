// tests/load/k6/scenarios/04-spike-test.js
// Spike/stress test - finds breaking points and validates graceful degradation
import http from 'k6/http';
import { check, sleep } from 'k6';
import { getAuthHeaders } from '../helpers/auth.js';

export const options = {
  scenarios: {
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 10 },   // Warm up
        { duration: '30s', target: 10 },   // Stable load
        { duration: '10s', target: 30 },   // SPIKE to 30 users
        { duration: '30s', target: 30 },   // Hold spike
        { duration: '10s', target: 50 },   // BIGGER SPIKE to 50 users
        { duration: '30s', target: 50 },   // Hold big spike (or until failure)
        { duration: '10s', target: 0 },    // Ramp down
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    'http_req_failed': ['rate<0.10'],  // Allow up to 10% errors (we expect some under spike)
    'http_req_duration': ['p(95)<10000'],  // P95 < 10s (degraded but not dead)
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost';

// Various endpoints to stress test
const ENDPOINTS = [
  '/api/problems/',
  '/api/user/me/',
  '/api/progress/',
  '/api/categories/',
  '/api/problem-sets/',
];

const PROBLEM_SLUGS = ['two-sum', 'reverse-string', 'fizzbuzz'];

export default function () {
  // Get auth headers
  const headers = getAuthHeaders('student@test.local');

  // Random endpoint selection
  const action = Math.random();

  if (action < 0.70) {
    // 70% - List endpoints (heavy read)
    const endpoint = ENDPOINTS[Math.floor(Math.random() * ENDPOINTS.length)];
    const response = http.get(`${BASE_URL}${endpoint}`, {
      headers: headers,
      tags: { type: 'read', endpoint: endpoint.split('/')[2] },
    });

    check(response, {
      'request completed': (r) => r.status < 500,  // Any non-5xx is acceptable
      'response received': (r) => r.body !== null,
    });
  } else if (action < 0.90) {
    // 20% - Detail endpoints
    const problemSlug = PROBLEM_SLUGS[Math.floor(Math.random() * PROBLEM_SLUGS.length)];
    const response = http.get(`${BASE_URL}/api/problems/${problemSlug}/`, {
      headers: headers,
      tags: { type: 'read', endpoint: 'problem_detail' },
    });

    check(response, {
      'problem loaded': (r) => r.status === 200 || r.status === 404,
    });
  } else {
    // 10% - Write operations (code submission under stress)
    const problemSlug = PROBLEM_SLUGS[Math.floor(Math.random() * PROBLEM_SLUGS.length)];
    const response = http.post(
      `${BASE_URL}/api/test-solution/`,
      JSON.stringify({
        problem_slug: problemSlug,
        code: 'def solution(): pass'
      }),
      {
        headers: headers,
        tags: { type: 'write', endpoint: 'submit' },
      }
    );

    check(response, {
      'submission attempted': (r) => r.status < 500,  // Don't fail on rate limits
    });
  }

  sleep(0.5);  // High throughput - minimal think time
}

export function setup() {
  console.log('Starting spike/stress test');
  console.log('Goal: Find breaking point and validate graceful degradation');
  console.log('\nLoad profile:');
  console.log('  - Ramp: 0 → 10 → 30 → 50 users');
  console.log('  - Spikes at 30s and 60s marks');
  console.log('  - Total duration: ~2.5 minutes');

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
    console.warn(`⚠ Authentication test failed: ${authTest.status}. Continuing anyway...`);
  } else {
    console.log('✓ Authentication verified');
  }

  return { startTime: Date.now() };
}

export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`\nSpike test completed in ${duration.toFixed(1)}s`);
  console.log('\nAnalyze results to determine:');
  console.log('  - At what load level did errors start occurring?');
  console.log('  - Did the system recover gracefully after the spike?');
  console.log('  - What was the maximum sustainable load?');
  console.log('  - Were there any 5xx errors (server failures)?');
}