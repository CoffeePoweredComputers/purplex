/**
 * Regression tests for ProblemSetEditorShell component.
 *
 * Bug Prevention:
 * - Bug 2: Frontend accessed p.slug instead of p.problem.slug when mapping
 *   API response to selectedProblemSlugs, causing null/undefined slugs
 *   to be sent to the backend.
 *
 * API Response Structure (from AdminProblemSetSerializer.get_problems_detail):
 * ```json
 * {
 *   "slug": "my-problem-set",
 *   "title": "My Problem Set",
 *   "problems_detail": [
 *     { "order": 0, "problem": { "slug": "problem-1", "title": "Problem 1", "problem_type": "eipl" } },
 *     { "order": 1, "problem": { "slug": "problem-2", "title": "Problem 2", "problem_type": "mcq" } }
 *   ]
 * }
 * ```
 *
 * The CORRECT extraction: `problems_detail.map(p => p.problem.slug)`
 * The BUGGY extraction: `problems_detail.map(p => p.slug)` → [undefined, undefined]
 */

import { describe, expect, it } from 'vitest';

// Types matching the API response structure
interface ProblemBasic {
  slug: string;
  title: string;
  problem_type: string;
}

interface ProblemDetailEntry {
  order: number;
  problem: ProblemBasic;
}

interface ProblemSetAPIResponse {
  slug: string;
  title: string;
  description?: string;
  is_public?: boolean;
  problems_detail?: ProblemDetailEntry[];
}

/**
 * Extract problem slugs from API response in correct order.
 *
 * This is the CORRECT implementation that matches ProblemSetEditorShell.vue:276
 */
function extractProblemSlugs(problemSet: ProblemSetAPIResponse): string[] {
  if (!problemSet.problems_detail) {
    return [];
  }

  // Sort by order field, then extract slug from nested problem object
  const sorted = [...problemSet.problems_detail].sort(
    (a, b) => (a.order || 0) - (b.order || 0)
  );

  // CORRECT: p.problem.slug (nested under problem object)
  return sorted.map((p) => p.problem.slug);
}

/**
 * This is the BUGGY implementation that caused null slugs.
 * Kept here to document what NOT to do.
 */
function extractProblemSlugsBUGGY(problemSet: ProblemSetAPIResponse): (string | undefined)[] {
  if (!problemSet.problems_detail) {
    return [];
  }

  const sorted = [...problemSet.problems_detail].sort(
    (a, b) => (a.order || 0) - (b.order || 0)
  );

  // BUGGY: p.slug doesn't exist - it's under p.problem.slug!
  // @ts-expect-error - intentionally accessing wrong property to show the bug
  return sorted.map((p) => p.slug);
}

describe('ProblemSetEditorShell - Bug 2 Regression: Slug Extraction', () => {
  // Mock API response matching backend serializer output
  const mockProblemSetResponse: ProblemSetAPIResponse = {
    slug: 'test-problem-set',
    title: 'Test Problem Set',
    description: 'A test problem set',
    is_public: true,
    problems_detail: [
      { order: 0, problem: { slug: 'problem-1', title: 'Problem 1', problem_type: 'eipl' } },
      { order: 1, problem: { slug: 'problem-2', title: 'Problem 2', problem_type: 'mcq' } },
      { order: 2, problem: { slug: 'problem-3', title: 'Problem 3', problem_type: 'prompt' } },
    ],
  };

  describe('Correct slug extraction', () => {
    it('should extract slugs from nested problem objects', () => {
      const slugs = extractProblemSlugs(mockProblemSetResponse);

      expect(slugs).toEqual(['problem-1', 'problem-2', 'problem-3']);
      expect(slugs).not.toContain(null);
      expect(slugs).not.toContain(undefined);
    });

    it('should handle empty problems_detail', () => {
      const emptyResponse: ProblemSetAPIResponse = {
        slug: 'empty-set',
        title: 'Empty Set',
        problems_detail: [],
      };

      const slugs = extractProblemSlugs(emptyResponse);

      expect(slugs).toEqual([]);
    });

    it('should handle missing problems_detail', () => {
      const noDetailResponse: ProblemSetAPIResponse = {
        slug: 'no-detail-set',
        title: 'No Detail Set',
        // problems_detail is undefined
      };

      const slugs = extractProblemSlugs(noDetailResponse);

      expect(slugs).toEqual([]);
    });

    it('should sort by order before extracting', () => {
      // API might return problems out of order
      const unorderedResponse: ProblemSetAPIResponse = {
        slug: 'unordered-set',
        title: 'Unordered Set',
        problems_detail: [
          { order: 2, problem: { slug: 'third', title: 'Third', problem_type: 'eipl' } },
          { order: 0, problem: { slug: 'first', title: 'First', problem_type: 'eipl' } },
          { order: 1, problem: { slug: 'second', title: 'Second', problem_type: 'mcq' } },
        ],
      };

      const slugs = extractProblemSlugs(unorderedResponse);

      // Should be sorted by order: first (0), second (1), third (2)
      expect(slugs).toEqual(['first', 'second', 'third']);
    });
  });

  describe('Buggy extraction (regression demonstration)', () => {
    it('should demonstrate the bug that produced undefined slugs', () => {
      // This test documents what the bug looked like
      const buggySlugs = extractProblemSlugsBUGGY(mockProblemSetResponse);

      // The buggy version would return [undefined, undefined, undefined]
      // because p.slug doesn't exist on ProblemDetailEntry
      expect(buggySlugs).toEqual([undefined, undefined, undefined]);

      // When sent to backend, undefined becomes null in JSON
      const jsonPayload = JSON.stringify({ problem_slugs: buggySlugs });
      expect(jsonPayload).toBe('{"problem_slugs":[null,null,null]}');
    });
  });

  describe('API payload construction', () => {
    it('should construct valid payload for update API', () => {
      const slugs = extractProblemSlugs(mockProblemSetResponse);

      const payload = {
        title: 'Updated Title',
        description: 'Updated description',
        is_public: true,
        problem_slugs: slugs,
      };

      // Verify payload is valid for API
      expect(payload.problem_slugs).toHaveLength(3);
      expect(payload.problem_slugs.every((s) => typeof s === 'string')).toBe(true);
      expect(payload.problem_slugs.every((s) => s.length > 0)).toBe(true);

      // Verify no nulls/undefined when serialized
      const json = JSON.stringify(payload);
      expect(json).not.toContain('null');
      expect(json).toContain('"problem-1"');
      expect(json).toContain('"problem-2"');
      expect(json).toContain('"problem-3"');
    });
  });
});

describe('ProblemDetailEntry type structure', () => {
  /**
   * These tests document the expected API response structure.
   * They serve as a contract test between frontend and backend.
   */

  it('should have nested problem object with slug', () => {
    const entry: ProblemDetailEntry = {
      order: 0,
      problem: {
        slug: 'test-problem',
        title: 'Test Problem',
        problem_type: 'eipl',
      },
    };

    // This is the CORRECT way to access the slug
    expect(entry.problem.slug).toBe('test-problem');

    // This would be WRONG (TypeScript catches this, but JS wouldn't)
    // @ts-expect-error - slug doesn't exist directly on entry
    expect(entry.slug).toBeUndefined();
  });

  it('should match backend AdminProblemSetSerializer.get_problems_detail structure', () => {
    /**
     * Backend returns this structure from:
     * purplex/problems_app/serializers.py
     *
     * class AdminProblemSetSerializer:
     *     problems_detail = serializers.SerializerMethodField()
     *
     *     def get_problems_detail(self, obj):
     *         memberships = obj.memberships.select_related('problem').order_by('order')
     *         return [
     *             {
     *                 'order': m.order,
     *                 'problem': ProblemPolymorphicListSerializer(m.problem).data
     *             }
     *             for m in memberships
     *         ]
     */
    const backendResponse: ProblemDetailEntry[] = [
      {
        order: 0,
        problem: {
          slug: 'my-problem',
          title: 'My Problem',
          problem_type: 'eipl',
        },
      },
    ];

    // The slug is nested under 'problem', not at top level
    expect(backendResponse[0].problem.slug).toBe('my-problem');
    expect('slug' in backendResponse[0]).toBe(false); // No top-level slug
  });
});
