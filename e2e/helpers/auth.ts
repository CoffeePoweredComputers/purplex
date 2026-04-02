import { Page } from '@playwright/test';

/**
 * Shape matches the User interface in auth.module.ts (line 83).
 * The auth module reads localStorage.getItem('user') on load (line 147)
 * and hydrates the Vuex store with { loggedIn: true, user }.
 *
 * In dev mode, DEBUG=true (line 77) bypasses route guards entirely,
 * but injecting a proper user ensures components that read the user
 * object render role-appropriate UI (admin panels, instructor tools, etc.).
 *
 * Auth tokens are handled by MockFirebase's built-in session restoration:
 * setting localStorage['mockFirebaseAuth'] causes the MockFirebase
 * constructor to restore currentUser with a working getIdToken() method.
 * The axios interceptor (main.ts:59) then automatically picks up tokens.
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
 * Sets three localStorage keys:
 * 1. 'user' — Vuex store hydration (role, email, UI rendering)
 * 2. 'mockFirebaseAuth' — MockFirebase session restoration (the axios
 *    interceptor needs currentUser.getIdToken() to work)
 * 3. 'purplex_cookie_consent' — dismiss cookie banner
 *
 * Must be called before navigating to the target route.
 */
export async function injectAuth(
  page: Page,
  role: 'student' | 'student2' | 'instructor' | 'admin',
): Promise<void> {
  const user = USERS[role];

  // Must be on the same origin before we can write to localStorage.
  await page.goto('/', { waitUntil: 'commit' });

  await page.evaluate(
    ({ userJson, mockFirebaseAuthJson, consent }) => {
      // Vuex store hydration (role-appropriate UI rendering)
      localStorage.setItem('user', userJson);
      // MockFirebase session restoration — on init, MockFirebase reads this
      // and reconstructs currentUser with a working getIdToken() that
      // generates valid MOCK.base64.development tokens automatically.
      localStorage.setItem('mockFirebaseAuth', mockFirebaseAuthJson);
      // Dismiss cookie consent banner
      localStorage.setItem('purplex_cookie_consent', consent);
    },
    {
      userJson: JSON.stringify(user),
      mockFirebaseAuthJson: JSON.stringify({
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
      }),
      consent: 'accepted',
    },
  );
}
