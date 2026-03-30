import { Page } from '@playwright/test';
import { generateMockToken } from './api';

/**
 * Shape matches the User interface in auth.module.ts (line 83).
 * The auth module reads localStorage.getItem('user') on load (line 147)
 * and hydrates the Vuex store with { loggedIn: true, user }.
 *
 * In dev mode, DEBUG=true (line 77) bypasses route guards entirely,
 * but injecting a proper user ensures components that read the user
 * object render role-appropriate UI (admin panels, instructor tools, etc.).
 *
 * CRITICAL: We also intercept all API requests via page.route() to inject
 * the Authorization header with a valid mock Firebase token. Without this,
 * the axios interceptor (main.ts:59) can't get a token from
 * firebase.auth().currentUser.getIdToken() — so all API calls go out
 * unauthenticated and return 401.
 */
interface MockUser {
  uid: string;
  email: string;
  displayName: string;
  role: 'admin' | 'user' | 'instructor';
  isAdmin: boolean;
}

const USERS: Record<string, MockUser> = {
  student: {
    uid: 'mock-uid-student',
    email: 'student@test.local',
    displayName: 'Test Student',
    role: 'user',
    isAdmin: false,
  },
  student2: {
    uid: 'mock-uid-student2',
    email: 'student2@test.local',
    displayName: 'Test Student 2',
    role: 'user',
    isAdmin: false,
  },
  instructor: {
    uid: 'mock-uid-instructor',
    email: 'instructor@test.local',
    displayName: 'Test Instructor',
    role: 'instructor',
    isAdmin: false,
  },
  admin: {
    uid: 'mock-uid-admin',
    email: 'admin@test.local',
    displayName: 'Test Admin',
    role: 'admin',
    isAdmin: true,
  },
};

/**
 * Inject a mock user into localStorage so the Vue app boots as authenticated.
 *
 * Must be called before navigating to the target route — the auth module
 * reads localStorage synchronously during Vuex store initialization.
 *
 * Navigates to the baseURL first to establish the origin (localStorage is
 * origin-scoped), then sets the values via page.evaluate().
 */
export async function injectAuth(
  page: Page,
  role: 'student' | 'student2' | 'instructor' | 'admin',
): Promise<void> {
  const user = USERS[role];

  // Must be on the same origin before we can write to localStorage.
  // Use a bare GET to the root — the page will redirect, but that's fine;
  // we only need the origin established.
  await page.goto('/', { waitUntil: 'commit' });

  await page.evaluate(
    ({ userJson, consent }) => {
      localStorage.setItem('user', userJson);
      localStorage.setItem('purplex_cookie_consent', consent);
    },
    { userJson: JSON.stringify(user), consent: 'accepted' },
  );

  // Intercept all API requests and inject the Authorization header.
  // The app's axios interceptor (main.ts:59) calls
  // firebase.auth().currentUser.getIdToken() which is never initialized
  // in E2E tests. This route handler ensures every API call carries a
  // valid mock Firebase token so the Django backend authenticates the request.
  //
  // Only inject if no Authorization header is already present — this avoids
  // overwriting tokens set by apiAs() helper in page.evaluate(fetch(...)).
  const token = generateMockToken(role);
  await page.route('**/api/**', async (route) => {
    const existingAuth = route.request().headers()['authorization'];
    if (existingAuth) {
      // Request already has auth (e.g. from apiAs helper) — don't overwrite
      await route.continue();
    } else {
      const headers = {
        ...route.request().headers(),
        'authorization': `Bearer ${token}`,
      };
      await route.continue({ headers });
    }
  });
}
