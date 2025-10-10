// tests/load/k6/scenarios/02-read-heavy-load.js
// Read-heavy API load test - tests authenticated GET endpoints
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { getAuthHeaders } from '../helpers/auth.js';

// Custom metrics
const readSuccessRate = new Rate('read_success_rate');
const readDuration = new Trend('read_duration');
const cacheHitRate = new Rate('cache_hit_rate');
const rateLimitHits = new Counter('rate_limit_hits');

export const options = {
  scenarios: {
    constant_read_load: {
      executor: 'constant-arrival-rate',
      rate: 20,  // 20 requests per second
      timeUnit: '1s',
      duration: '60s',
      preAllocatedVUs: 10,
      maxVUs: 30,
    },
  },
  thresholds: {
    'http_req_failed': ['rate<0.01'],  // Less than 1% errors
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'read_success_rate': ['rate>0.99'],  // 99% success
    'read_duration': ['p(99)<800'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost';

// Simulated problem slugs (should exist in database)
const PROBLEM_SLUGS = ['two-sum', 'reverse-string', 'fizzbuzz', 'factorial', 'palindrome'];

// Different API endpoints to test
const READ_ENDPOINTS = [
  { url: '/api/problems/', weight: 30 },           // Problem list
  { url: '/api/user/me/', weight: 20 },            // User profile
  { url: '/api/progress/', weight: 25 },           // User progress
  { url: '/api/categories/', weight: 15 },         // Categories
  { url: '/api/problem-sets/', weight: 10 },       // Problem sets
];

// Calculate cumulative weights for weighted selection
let cumulativeWeights = [];
let totalWeight = 0;
for (const endpoint of READ_ENDPOINTS) {
  totalWeight += endpoint.weight;
  cumulativeWeights.push(totalWeight);
}

function selectRandomEndpoint() {
  const random = Math.random() * totalWeight;
  for (let i = 0; i < cumulativeWeights.length; i++) {
    if (random < cumulativeWeights[i]) {
      return READ_ENDPOINTS[i].url;
    }
  }
  return READ_ENDPOINTS[0].url;
}

export default function () {
  const headers = getAuthHeaders('student@test.local');
  const startTime = Date.now();

  // Randomly select endpoint based on weights
  let endpoint;
  const random = Math.random();
  if (random < 0.7) {
    // 70% of the time, use weighted selection
    endpoint = selectRandomEndpoint();
  } else {
    // 30% of the time, fetch a specific problem
    const problemSlug = PROBLEM_SLUGS[Math.floor(Math.random() * PROBLEM_SLUGS.length)];
    endpoint = `/api/problems/${problemSlug}/`;
  }

  const response = http.get(
    `${BASE_URL}${endpoint}`,
    {
      headers: headers,
      tags: { endpoint: endpoint.split('/')[2] || 'unknown' }, // Extract endpoint category
    }
  );

  const duration = Date.now() - startTime;
  readDuration.add(duration);

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'has response body': (r) => r.body && r.body.length > 0,
    'valid JSON': (r) => {
      try {
        r.json();
        return true;
      } catch (e) {
        return false;
      }
    },
  });

  readSuccessRate.add(success);

  // Track cache hits (if server sends Cache-Control or X-Cache headers)
  const cacheControl = response.headers['Cache-Control'];
  const xCache = response.headers['X-Cache'];
  if (cacheControl && cacheControl.includes('max-age') || xCache === 'HIT') {
    cacheHitRate.add(true);
  } else {
    cacheHitRate.add(false);
  }

  // Track rate limiting
  if (response.status === 429) {
    rateLimitHits.add(1);
    console.warn('Rate limit hit!');
  }

  if (!success) {
    console.error(`Request failed: ${endpoint} - Status: ${response.status}`);
  }

  // Minimal sleep for high throughput test
  sleep(0.1);
}

export function setup() {
  console.log('Starting read-heavy load test');
  console.log(`Target: 20 req/s for 60s = 1200 total requests`);
  console.log(`Testing endpoints: ${READ_ENDPOINTS.map(e => e.url).join(', ')}`);

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
  console.log('  - read_success_rate: Percentage of successful reads');
  console.log('  - read_duration: Response times for read operations');
  console.log('  - cache_hit_rate: Percentage of cached responses');
  console.log('  - rate_limit_hits: Number of rate limit errors (should be 0)');
}