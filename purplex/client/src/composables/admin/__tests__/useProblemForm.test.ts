import { beforeEach, describe, expect, it } from 'vitest'
import { type ProblemFormState, useProblemForm } from '../useProblemForm'
import type { ProblemCategory, ProblemDetailed } from '@/types'

// ===== TEST FIXTURES =====

/**
 * Mock ProblemDetailed with non-default values for every field that
 * ProblemFormState consumes. Non-default values ensure the round-trip
 * test exercises actual mapping, not silent default pass-through.
 */
const createMockProblemDetailed = (
  overrides: Partial<ProblemDetailed> = {}
): ProblemDetailed => ({
  slug: 'round-trip-problem',
  title: 'Round Trip Title',
  description: 'Round trip description text',
  difficulty: 'advanced',
  problem_type: 'eipl',
  function_name: 'solve',
  function_signature: 'def solve(n: int) -> int:',
  reference_solution: 'def solve(n):\n    return n * 2',
  memory_limit: 256,
  tags: ['recursion', 'dp'],
  is_active: true,
  created_at: '2025-06-01T00:00:00Z',
  updated_at: '2025-06-01T00:00:00Z',
  version: 1,
  categories: [
    { id: 5, name: 'Algorithms', slug: 'algorithms', description: '' } as ProblemCategory,
    { id: 12, name: 'Data Structures', slug: 'data-structures', description: '' } as ProblemCategory,
  ],
  category_ids: [5, 12],
  test_cases: [],
  test_cases_count: 0,
  visible_test_cases_count: 0,
  ...overrides,
})

/**
 * Expected ProblemFormState after normalizeFromLoad on the mock above.
 *
 * IMPORTANT: This must contain EVERY key of ProblemFormState. TypeScript
 * enforces this at compile time — adding a field to ProblemFormState
 * without updating this fixture will cause a type error.
 */
const EXPECTED_ROUND_TRIP: ProblemFormState = {
  title: 'Round Trip Title',
  description: 'Round trip description text',
  difficulty: 'advanced',
  problem_type: 'eipl',
  category_ids: [5, 12],
  function_signature: 'def solve(n: int) -> int:',
  reference_solution: 'def solve(n):\n    return n * 2',
  tags: ['recursion', 'dp'],
}

// ===== TESTS =====

describe('useProblemForm', () => {
  let form: ReturnType<typeof useProblemForm>

  beforeEach(() => {
    form = useProblemForm()
  })

  // --- initial state ---

  describe('initial state', () => {
    it('should have empty/default values for all fields', () => {
      expect(form.form.title).toBe('')
      expect(form.form.description).toBe('')
      expect(form.form.difficulty).toBe('beginner')
      expect(form.form.problem_type).toBe('eipl')
      expect(form.form.category_ids).toEqual([])
      expect(form.form.function_signature).toBe('')
      expect(form.form.reference_solution).toBe('')
      expect(form.form.tags).toEqual([])
    })

    it('should not be dirty', () => {
      expect(form.isDirty.value).toBe(false)
    })

    it('should not be saveable', () => {
      expect(form.canSave.value).toBe(false)
    })

    it('should report validation errors for required fields', () => {
      expect(form.validationErrors.value).toContain('Title is required')
      expect(form.validationErrors.value).toContain('Function signature is required')
      expect(form.validationErrors.value).toContain('Reference solution is required')
    })
  })

  // --- round-trip: normalizeFromLoad -> setForm -> form ---
  // This is the critical regression test that would have caught the
  // missing description field. TypeScript enforces EXPECTED_ROUND_TRIP
  // has all keys; the test enforces the runtime mapping works.

  describe('round-trip: normalizeFromLoad -> setForm -> form', () => {
    it('should preserve ALL ProblemFormState fields through the pipeline', () => {
      const mock = createMockProblemDetailed()
      const normalized = form.normalizeFromLoad(mock)
      form.setForm(normalized)

      // Per-field assertions for clear failure messages
      for (const key of Object.keys(EXPECTED_ROUND_TRIP) as Array<keyof ProblemFormState>) {
        expect(form.form[key], `field "${key}" should survive round-trip`).toEqual(
          EXPECTED_ROUND_TRIP[key]
        )
      }
    })

    it('should produce an exact match (catches extra or missing keys)', () => {
      const mock = createMockProblemDetailed()
      const normalized = form.normalizeFromLoad(mock)
      form.setForm(normalized)

      expect({ ...form.form }).toEqual(EXPECTED_ROUND_TRIP)
    })

    it('normalizeFromLoad output should have exactly the keys of ProblemFormState', () => {
      const normalized = form.normalizeFromLoad(createMockProblemDetailed())
      expect(Object.keys(normalized).sort()).toEqual(Object.keys(EXPECTED_ROUND_TRIP).sort())
    })

    it('should not be dirty after setForm', () => {
      const normalized = form.normalizeFromLoad(createMockProblemDetailed())
      form.setForm(normalized)
      expect(form.isDirty.value).toBe(false)
    })
  })

  // --- setForm ---

  describe('setForm', () => {
    it('should set all provided fields', () => {
      form.setForm({
        title: 'New Title',
        description: 'A description',
        difficulty: 'intermediate',
        tags: ['test'],
      })

      expect(form.form.title).toBe('New Title')
      expect(form.form.description).toBe('A description')
      expect(form.form.difficulty).toBe('intermediate')
      expect(form.form.tags).toEqual(['test'])
    })

    it('should not clear fields absent from partial update', () => {
      form.setForm({ title: 'First', description: 'Desc' })
      form.setForm({ difficulty: 'advanced' })

      expect(form.form.title).toBe('First')
      expect(form.form.description).toBe('Desc')
      expect(form.form.difficulty).toBe('advanced')
    })

    it('should reset isDirty after setForm', () => {
      form.updateField('title', 'changed')
      expect(form.isDirty.value).toBe(true)

      form.setForm({ title: 'loaded' })
      expect(form.isDirty.value).toBe(false)
    })
  })

  // --- resetForm ---

  describe('resetForm', () => {
    it('should reset all fields to initial defaults', () => {
      form.setForm({
        title: 'Something',
        description: 'Desc',
        difficulty: 'advanced',
        problem_type: 'prompt',
        category_ids: [1, 2],
        function_signature: 'def f():',
        reference_solution: 'def f(): pass',
        tags: ['a', 'b'],
      })

      form.resetForm()

      expect(form.form.title).toBe('')
      expect(form.form.description).toBe('')
      expect(form.form.difficulty).toBe('beginner')
      expect(form.form.problem_type).toBe('eipl')
      expect(form.form.category_ids).toEqual([])
      expect(form.form.function_signature).toBe('')
      expect(form.form.reference_solution).toBe('')
      expect(form.form.tags).toEqual([])
    })

    it('should reset isDirty to false', () => {
      form.updateField('title', 'dirty')
      form.resetForm()
      expect(form.isDirty.value).toBe(false)
    })
  })

  // --- updateField ---

  describe('updateField', () => {
    it('should update a single field', () => {
      form.updateField('title', 'Updated')
      expect(form.form.title).toBe('Updated')
    })

    it('should mark form as dirty', () => {
      form.updateField('title', 'Changed')
      expect(form.isDirty.value).toBe(true)
    })

    it('should handle array fields', () => {
      form.updateField('category_ids', [1, 2, 3])
      expect(form.form.category_ids).toEqual([1, 2, 3])
    })
  })

  // --- updateTags ---

  describe('updateTags', () => {
    it('should parse comma-separated tags', () => {
      form.updateTags('loops, arrays, recursion')
      expect(form.form.tags).toEqual(['loops', 'arrays', 'recursion'])
    })

    it('should trim whitespace', () => {
      form.updateTags('  tag1  ,  tag2  ')
      expect(form.form.tags).toEqual(['tag1', 'tag2'])
    })

    it('should filter empty strings', () => {
      form.updateTags('a,,b, ,c')
      expect(form.form.tags).toEqual(['a', 'b', 'c'])
    })

    it('should handle empty input', () => {
      form.updateTags('')
      expect(form.form.tags).toEqual([])
    })
  })

  // --- updateReferenceSolution ---

  describe('updateReferenceSolution', () => {
    it('should accept string directly', () => {
      form.updateReferenceSolution('def solve(): pass')
      expect(form.form.reference_solution).toBe('def solve(): pass')
    })

    it('should coerce non-string to string', () => {
      form.updateReferenceSolution(42)
      expect(form.form.reference_solution).toBe('42')
    })

    it('should handle null/undefined', () => {
      form.updateReferenceSolution(null)
      expect(form.form.reference_solution).toBe('')

      form.updateReferenceSolution(undefined)
      expect(form.form.reference_solution).toBe('')
    })
  })

  // --- canSave ---

  describe('canSave', () => {
    it('should require title, function_signature, and reference_solution', () => {
      expect(form.canSave.value).toBe(false)

      form.updateField('title', 'Title')
      expect(form.canSave.value).toBe(false)

      form.updateField('function_signature', 'def f():')
      expect(form.canSave.value).toBe(false)

      form.updateField('reference_solution', 'def f(): pass')
      expect(form.canSave.value).toBe(true)
    })

    it('should reject whitespace-only required fields', () => {
      form.updateField('title', '   ')
      form.updateField('function_signature', 'def f():')
      form.updateField('reference_solution', 'code')
      expect(form.canSave.value).toBe(false)
    })
  })

  // --- validationErrors ---

  describe('validationErrors', () => {
    it('should return all 3 errors when form is empty', () => {
      expect(form.validationErrors.value).toHaveLength(3)
    })

    it('should return empty when all required fields are filled', () => {
      form.updateField('title', 'T')
      form.updateField('function_signature', 'def f():')
      form.updateField('reference_solution', 'code')
      expect(form.validationErrors.value).toHaveLength(0)
    })
  })

  // --- getApiSafeString ---

  describe('getApiSafeString', () => {
    it('should trim whitespace', () => {
      expect(form.getApiSafeString('  hello  ')).toBe('hello')
    })

    it('should return empty string for null/undefined', () => {
      expect(form.getApiSafeString(null)).toBe('')
      expect(form.getApiSafeString(undefined)).toBe('')
    })
  })

  // --- normalizeFromLoad edge cases ---

  describe('normalizeFromLoad', () => {
    it('should extract category_ids from categories array', () => {
      const mock = createMockProblemDetailed({
        categories: [{ id: 3, name: 'Cat', slug: 'cat', description: '' } as ProblemCategory],
      })
      const result = form.normalizeFromLoad(mock)
      expect(result.category_ids).toEqual([3])
    })

    it('should fall back to category_ids when categories is missing', () => {
      const mock = createMockProblemDetailed({
        categories: undefined as unknown as ProblemCategory[],
        category_ids: [7, 8],
      })
      const result = form.normalizeFromLoad(mock)
      expect(result.category_ids).toEqual([7, 8])
    })

    it('should default missing difficulty to beginner', () => {
      const mock = createMockProblemDetailed({
        difficulty: undefined as unknown as 'beginner',
      })
      expect(form.normalizeFromLoad(mock).difficulty).toBe('beginner')
    })

    it('should default empty problem_type to eipl', () => {
      const mock = createMockProblemDetailed({
        problem_type: '' as unknown as string,
      })
      expect(form.normalizeFromLoad(mock).problem_type).toBe('eipl')
    })

    it('should coerce non-string reference_solution to empty string', () => {
      const mock = createMockProblemDetailed({
        reference_solution: null as unknown as string,
      })
      expect(form.normalizeFromLoad(mock).reference_solution).toBe('')
    })

    it('should handle non-array tags', () => {
      const mock = createMockProblemDetailed({
        tags: null as unknown as string[],
      })
      expect(form.normalizeFromLoad(mock).tags).toEqual([])
    })
  })

  // --- isDirty edge cases ---

  describe('isDirty', () => {
    it('should detect changes after setForm baseline', () => {
      form.setForm({ title: 'loaded' })
      expect(form.isDirty.value).toBe(false)

      form.updateField('title', 'modified')
      expect(form.isDirty.value).toBe(true)
    })

    it('should return to not-dirty when value is reverted', () => {
      form.setForm({ title: 'original' })
      form.updateField('title', 'changed')
      expect(form.isDirty.value).toBe(true)

      form.updateField('title', 'original')
      expect(form.isDirty.value).toBe(false)
    })
  })
})
