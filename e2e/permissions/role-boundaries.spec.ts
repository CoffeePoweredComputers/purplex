/**
 * E2E Tests -- Permission Boundaries (CRITICAL)
 *
 * Verifies backend API permission enforcement directly via apiAs().
 * Frontend route guards are BYPASSED in dev mode, so these tests
 * hit the Django backend to confirm 403/401 responses.
 *
 * This is the most important permission test file. Every boundary
 * tested here prevents a real privilege escalation.
 *
 * Prerequisites:
 *   1. Django dev server on :8000 with USE_MOCK_FIREBASE=true
 *   2. Vite dev server on :5173
 *   3. Seeded users and course data
 *
 * Run: npx playwright test e2e/permissions/role-boundaries.spec.ts
 */

import { test, expect } from '@playwright/test';
import { navigateAs } from '../helpers/navigation';
import { apiAs } from '../helpers/api';

test.describe('Permission Boundaries', () => {
  // We need a page context for apiAs to run fetch in. Navigate once.
  test.beforeEach(async ({ page }) => {
    // Establish browser origin so page.evaluate can run fetch()
    await page.goto('/', { waitUntil: 'commit' });
  });

  // -----------------------------------------------------------------------
  // Student cannot access admin endpoints
  // -----------------------------------------------------------------------
  test.describe('Student cannot access admin endpoints', () => {
    test('student cannot GET /api/admin/users/', async ({ page }) => {
      const res = await apiAs(page, 'student', 'GET', '/api/admin/users/');
      expect(res.status).toBe(403);
    });

    test('student cannot GET /api/admin/problems/', async ({ page }) => {
      const res = await apiAs(page, 'student', 'GET', '/api/admin/problems/');
      expect(res.status).toBe(403);
    });

    test('student cannot POST /api/admin/problems/', async ({ page }) => {
      const res = await apiAs(page, 'student', 'POST', '/api/admin/problems/', {
        title: 'Injected Problem',
        slug: 'injected-problem',
      });
      expect(res.status).toBe(403);
    });

    test('student cannot DELETE /api/admin/courses/CS101-2024/', async ({ page }) => {
      const res = await apiAs(page, 'student', 'DELETE', '/api/admin/courses/CS101-2024/');
      expect(res.status).toBe(403);
    });
  });

  // -----------------------------------------------------------------------
  // Student cannot access instructor endpoints
  // -----------------------------------------------------------------------
  test.describe('Student cannot access instructor endpoints', () => {
    test('student cannot GET /api/instructor/courses/', async ({ page }) => {
      const res = await apiAs(page, 'student', 'GET', '/api/instructor/courses/');
      expect(res.status).toBe(403);
    });

    test('student cannot POST /api/instructor/problems/', async ({ page }) => {
      const res = await apiAs(page, 'student', 'POST', '/api/instructor/problems/', {
        title: 'Student Injected Problem',
        slug: 'student-injected',
      });
      expect(res.status).toBe(403);
    });

    test('student cannot GET /api/instructor/courses/CS101-2024/students/', async ({ page }) => {
      const res = await apiAs(page, 'student', 'GET', '/api/instructor/courses/CS101-2024/students/');
      expect(res.status).toBe(403);
    });
  });

  // -----------------------------------------------------------------------
  // Instructor cannot access admin endpoints
  // -----------------------------------------------------------------------
  test.describe('Instructor cannot access admin endpoints', () => {
    test('instructor cannot GET /api/admin/users/', async ({ page }) => {
      const res = await apiAs(page, 'instructor', 'GET', '/api/admin/users/');
      expect(res.status).toBe(403);
    });

    test('instructor cannot POST /api/admin/courses/', async ({ page }) => {
      const res = await apiAs(page, 'instructor', 'POST', '/api/admin/courses/', {
        name: 'Rogue Course',
        course_id: 'ROGUE-101',
      });
      expect(res.status).toBe(403);
    });
  });

  // -----------------------------------------------------------------------
  // Cross-course isolation
  // -----------------------------------------------------------------------
  test.describe('Cross-course isolation', () => {
    test('instructor cannot access a non-existent course', async ({ page }) => {
      const res = await apiAs(page, 'instructor', 'GET', '/api/instructor/courses/FAKE-COURSE-999/');
      // Should be 404 (not found) since the course does not exist
      expect(res.status).toBe(404);
    });

    test('student cannot access another course students list via instructor API', async ({ page }) => {
      const res = await apiAs(page, 'student', 'GET', '/api/instructor/courses/CS101-2024/students/');
      expect(res.status).toBe(403);
    });
  });

  // -----------------------------------------------------------------------
  // Unauthenticated access
  // -----------------------------------------------------------------------
  test.describe('Unauthenticated access', () => {
    test('no auth header on protected endpoint returns 401', async ({ page }) => {
      // Use page.evaluate with a raw fetch (no Authorization header)
      const result = await page.evaluate(async () => {
        const res = await fetch('http://localhost:8000/api/user/me/', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });
        let data;
        try {
          data = await res.json();
        } catch {
          data = null;
        }
        return { status: res.status, data };
      });

      expect(result.status).toBe(401);
    });

    test('no auth header on admin endpoint returns 401', async ({ page }) => {
      const result = await page.evaluate(async () => {
        const res = await fetch('http://localhost:8000/api/admin/users/', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });
        let data;
        try {
          data = await res.json();
        } catch {
          data = null;
        }
        return { status: res.status, data };
      });

      expect(result.status).toBe(401);
    });
  });

  // -----------------------------------------------------------------------
  // Positive checks: authorized roles succeed
  // -----------------------------------------------------------------------
  test.describe('Authorized access succeeds', () => {
    test('admin can GET /api/admin/users/', async ({ page }) => {
      const res = await apiAs(page, 'admin', 'GET', '/api/admin/users/');
      expect(res.status).toBe(200);
    });

    test('instructor can GET /api/instructor/courses/', async ({ page }) => {
      const res = await apiAs(page, 'instructor', 'GET', '/api/instructor/courses/');
      expect(res.status).toBe(200);
    });

    test('student can GET /api/user/me/', async ({ page }) => {
      const res = await apiAs(page, 'student', 'GET', '/api/user/me/');
      expect(res.status).toBe(200);
    });
  });
});
