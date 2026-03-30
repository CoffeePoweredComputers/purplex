import { Page } from '@playwright/test';

/**
 * Shape matches the User interface in auth.module.ts (line 83).
 * The auth module reads localStorage.getItem('user') on load (line 147)
 * and hydrates the Vuex store with { loggedIn: true, user }.
 *
 * In dev mode, DEBUG=true (line 77) bypasses route guards entirely,
 * but injecting a proper user ensures components that read the user
 * object render role-appropriate UI (admin panels, instructor tools, etc.).
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
    uid: 'e2e-student-001',
    email: 'student@test.local',
    displayName: 'Test Student',
    role: 'user',
    isAdmin: false,
  },
  instructor: {
    uid: 'e2e-instructor-001',
    email: 'instructor@test.local',
    displayName: 'Test Instructor',
    role: 'instructor',
    isAdmin: false,
  },
  admin: {
    uid: 'e2e-admin-001',
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
  role: 'student' | 'instructor' | 'admin',
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
}
