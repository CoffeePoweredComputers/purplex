import { Page } from '@playwright/test';

/**
 * Fresh, per-test student users.
 *
 * Probe budgets and probe history live in Redis per (problem, user) with a
 * 7-day TTL and no reset, and submissions accumulate per user. Any test that
 * touches a budget, history or submissions must therefore run as a user no
 * other test (or earlier run) has used.
 *
 * Mock Firebase accepts any email: the backend (users_app/mock_firebase.py)
 * creates a student for an unknown email using the uid from the token, and
 * the frontend MockFirebase restores its session from localStorage.
 */
export interface FreshUser {
  uid: string;
  email: string;
  displayName: string;
}

/** Create a unique user identity. Nothing is sent to the server. */
export function freshStudent(label: string): FreshUser {
  const safeLabel = label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  const id = `e2e-${safeLabel}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return {
    uid: `mock-uid-${id}`,
    email: `${id}@test.local`,
    displayName: `E2E ${label}`,
  };
}

/**
 * Inject this user into localStorage so the Vue app boots as them.
 * Mirrors injectAuth in auth.ts: Vuex `user`, `mockFirebaseAuth`, and the
 * cookie consent flag. Must be called before navigating to the target route.
 */
export async function injectUser(page: Page, user: FreshUser): Promise<void> {
  await page.goto('/', { waitUntil: 'commit' });

  await page.evaluate(
    ({ userJson, mockFirebaseAuthJson, consent }) => {
      localStorage.setItem('user', userJson);
      localStorage.setItem('mockFirebaseAuth', mockFirebaseAuthJson);
      localStorage.setItem('purplex_cookie_consent', consent);
    },
    {
      userJson: JSON.stringify({
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        role: 'user',
        isAdmin: false,
      }),
      mockFirebaseAuthJson: JSON.stringify({
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
      }),
      consent: 'accepted',
    },
  );
}

/**
 * Mint a mock token for this user. Same payload as the frontend's
 * MockFirebase.createMockToken, which the backend decodes as
 * MOCK.<base64 json>.development.
 */
function mockTokenFor(user: FreshUser): string {
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    uid: user.uid,
    email: user.email,
    name: user.displayName,
    email_verified: true,
    iat: now,
    exp: now + 3600,
  };
  return `MOCK.${btoa(JSON.stringify(payload))}.development`;
}

/**
 * Call the API as this user from inside the page (same origin, through the
 * Vite proxy). The page must already be on the app origin.
 */
export async function apiAsUser(
  page: Page,
  user: FreshUser,
  method: string,
  path: string,
  body?: object,
): Promise<{ status: number; data: any }> {
  const token = mockTokenFor(user);
  return page.evaluate(
    async ({ token, method, path, body }) => {
      const res = await fetch(path, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      const text = await res.text();
      let data: unknown = null;
      if (text) {
        try {
          data = JSON.parse(text);
        } catch {
          data = text;
        }
      }
      return { status: res.status, data };
    },
    { token, method, path, body },
  );
}

/** Enroll this user in a course. Throws unless the API answers 200 or 201. */
export async function enrollUser(
  page: Page,
  user: FreshUser,
  courseId = 'CS101-2024',
): Promise<void> {
  const { status, data } = await apiAsUser(page, user, 'POST', '/api/courses/enroll/', {
    course_id: courseId,
  });
  if (status !== 200 && status !== 201) {
    throw new Error(
      `enrollUser: ${user.email} -> ${courseId} returned ${status}: ${JSON.stringify(data)}`,
    );
  }
}

/** Create a fresh student, log in, enroll in CS101-2024, and open `path`. */
export async function navigateAsFreshStudent(
  page: Page,
  label: string,
  path: string,
): Promise<FreshUser> {
  const user = freshStudent(label);
  await injectUser(page, user);
  await enrollUser(page, user);
  await page.goto(path, { waitUntil: 'networkidle' });
  return user;
}

/**
 * Grant this user AI-processing consent. Fresh users have none, and spec-type
 * submissions (LLM code generation) are blocked without it.
 */
export async function grantAiConsent(page: Page, user: FreshUser): Promise<void> {
  const { status, data } = await apiAsUser(page, user, 'POST', '/api/users/me/consents/', {
    consent_type: 'ai_processing',
  });
  if (status !== 200 && status !== 201) {
    throw new Error(`grantAiConsent: ${user.email} returned ${status}: ${JSON.stringify(data)}`);
  }
}
