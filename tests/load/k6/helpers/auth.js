// tests/load/k6/helpers/auth.js
// Authentication helper for k6 load tests
// Generates Mock Firebase tokens for development environment
import encoding from 'k6/encoding';

/**
 * Generate a mock Firebase token for development.
 *
 * Format: MOCK.<base64_payload>.development
 *
 * This matches the format expected by Purplex's mock_firebase.py
 * in development mode. The token contains user email, UID, and expiration.
 *
 * @param {string} email - User email address (default: 'student@test.local')
 * @returns {string} Mock Firebase token
 */
export function generateMockToken(email = 'student@test.local') {
  const now = Math.floor(Date.now() / 1000);

  const payload = {
    email: email,
    uid: `mock-uid-${email.replace('@', '-').replace(/\./g, '-')}`,
    name: email.split('@')[0],
    iat: now,
    exp: now + 3600, // 1 hour expiry
    email_verified: true
  };

  // Base64 encode the payload
  const payloadJson = JSON.stringify(payload);
  const payloadB64 = encoding.b64encode(payloadJson, 'rawstd');

  return `MOCK.${payloadB64}.development`;
}

/**
 * Get headers for authenticated requests.
 *
 * Includes Content-Type and Authorization headers with mock Firebase token.
 *
 * @param {string} email - User email address (default: 'student@test.local')
 * @returns {Object} Headers object for HTTP requests
 */
export function getAuthHeaders(email = 'student@test.local') {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${generateMockToken(email)}`
  };
}

/**
 * Get different test users based on role.
 *
 * @param {string} role - User role: 'student', 'admin', or 'instructor'
 * @returns {string} Email address for the test user
 */
export function getTestUser(role = 'student') {
  const users = {
    'student': 'student@test.local',
    'student2': 'student2@test.local',
    'admin': 'admin@test.local',
    'instructor': 'instructor@test.local'
  };

  return users[role] || users['student'];
}

/**
 * Generate headers for a specific user role.
 *
 * @param {string} role - User role: 'student', 'admin', or 'instructor'
 * @returns {Object} Headers object for HTTP requests
 */
export function getAuthHeadersForRole(role = 'student') {
  const email = getTestUser(role);
  return getAuthHeaders(email);
}