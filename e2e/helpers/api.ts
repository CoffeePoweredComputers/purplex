import { Page } from '@playwright/test';

type Role = 'student' | 'student2' | 'instructor' | 'admin';

const ROLE_EMAILS: Record<Role, string> = {
  student: 'student@test.local',
  student2: 'student2@test.local',
  instructor: 'instructor@test.local',
  admin: 'admin@test.local',
};

/**
 * Generate a mock Firebase token for the given role.
 * Format: MOCK.base64(payload).development
 * This matches what mock_firebase.py expects.
 */
function generateMockToken(role: Role): string {
  const email = ROLE_EMAILS[role];
  const payload = {
    email,
    uid: `mock-uid-${role === 'student2' ? 'student2' : role}`,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 3600,
  };
  // Base64 encode the payload - will be decoded in page.evaluate
  return `MOCK.${btoa(JSON.stringify(payload))}.development`;
}

/**
 * Make an authenticated API call as a specific role.
 * Uses page.evaluate to run fetch() in the browser context.
 * Returns { status, data }.
 */
export async function apiAs(
  page: Page,
  role: Role,
  method: string,
  path: string,
  body?: object,
): Promise<{ status: number; data: any }> {
  const token = generateMockToken(role);
  const baseURL = 'http://localhost:8000';

  return page.evaluate(
    async ({ token, method, url, body }) => {
      const res = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      let data;
      try {
        data = await res.json();
      } catch {
        data = null;
      }
      return { status: res.status, data };
    },
    { token, method, url: `${baseURL}${path}`, body },
  );
}

/**
 * Wait for a specific API response during page interaction.
 * Returns the response.
 */
export async function waitForAPI(
  page: Page,
  urlPattern: string | RegExp,
  timeout = 15000,
): Promise<{ status: number; body: any }> {
  const response = await page.waitForResponse(
    (resp) => {
      if (typeof urlPattern === 'string') {
        return resp.url().includes(urlPattern);
      }
      return urlPattern.test(resp.url());
    },
    { timeout },
  );
  let body;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return { status: response.status(), body };
}

/**
 * Intercept an API call and return a mock response.
 * Useful for testing error states.
 */
export async function interceptAPI(
  page: Page,
  urlPattern: string | RegExp,
  mockResponse: { status: number; body: object },
): Promise<void> {
  await page.route(
    (url) => {
      if (typeof urlPattern === 'string') {
        return url.toString().includes(urlPattern);
      }
      return urlPattern.test(url.toString());
    },
    (route) => {
      route.fulfill({
        status: mockResponse.status,
        contentType: 'application/json',
        body: JSON.stringify(mockResponse.body),
      });
    },
  );
}
