/**
 * useSubmissionCache - TTL-based cache for submission data.
 *
 * Provides a simple in-memory cache with 5-minute TTL for submission data.
 * Helps reduce API calls when navigating between problems.
 *
 * Key format: `${problemSetSlug}_${problemSlug}_${courseId || 'standalone'}`
 */

import { shallowRef } from 'vue';

// ===== TYPES =====

/**
 * Cached submission data structure.
 */
export interface CachedSubmissionData {
  has_submission: boolean;
  variations: string[];
  results: unknown[];
  passing_variations: number;
  feedback: string;
  user_prompt: string;
  segmentation: unknown | null;
  segmentation_passed?: boolean;
  [key: string]: unknown;
}

interface CacheEntry {
  data: CachedSubmissionData;
  timestamp: number;
}

// ===== CONSTANTS =====

/** Cache TTL in milliseconds (5 minutes) */
const CACHE_TTL_MS = 5 * 60 * 1000;

// ===== COMPOSABLE =====

export interface UseSubmissionCacheReturn {
  /**
   * Get cached data for a key, or null if not found or expired.
   */
  get: (key: string) => CachedSubmissionData | null;

  /**
   * Set data in cache with current timestamp.
   */
  set: (key: string, data: CachedSubmissionData) => void;

  /**
   * Invalidate a specific cache entry.
   */
  invalidate: (key: string) => void;

  /**
   * Clear all cached entries.
   */
  invalidateAll: () => void;

  /**
   * Build a cache key from problem context.
   */
  buildKey: (problemSetSlug: string, problemSlug: string, courseId?: string | null) => string;

  /**
   * Check if a key exists and is not expired.
   */
  has: (key: string) => boolean;
}

/**
 * Creates a submission cache manager.
 *
 * @returns Cache management methods
 *
 * @example
 * ```typescript
 * const cache = useSubmissionCache();
 *
 * const key = cache.buildKey('arrays', 'two-sum', 'CS201');
 *
 * // Check cache first
 * const cached = cache.get(key);
 * if (cached) {
 *   return cached;
 * }
 *
 * // Fetch and cache
 * const data = await fetchSubmissionData();
 * cache.set(key, data);
 *
 * // Invalidate on new submission
 * cache.invalidate(key);
 * ```
 */
export const useSubmissionCache = (): UseSubmissionCacheReturn => {
  // Using shallowRef to avoid deep reactivity on the Map
  // The Map itself doesn't need to be deeply reactive
  const cache = shallowRef<Map<string, CacheEntry>>(new Map());

  /**
   * Build a cache key from problem context.
   */
  const buildKey = (
    problemSetSlug: string,
    problemSlug: string,
    courseId?: string | null
  ): string => {
    return `${problemSetSlug}_${problemSlug}_${courseId || 'standalone'}`;
  };

  /**
   * Check if entry exists and is not expired.
   */
  const isValid = (entry: CacheEntry | undefined): entry is CacheEntry => {
    if (!entry) {
      return false;
    }
    return Date.now() - entry.timestamp < CACHE_TTL_MS;
  };

  /**
   * Check if a key exists and is valid.
   */
  const has = (key: string): boolean => {
    return isValid(cache.value.get(key));
  };

  /**
   * Get cached data, or null if not found/expired.
   */
  const get = (key: string): CachedSubmissionData | null => {
    const entry = cache.value.get(key);
    if (isValid(entry)) {
      return entry.data;
    }
    // Clean up expired entry
    if (entry) {
      cache.value.delete(key);
    }
    return null;
  };

  /**
   * Set data in cache.
   */
  const set = (key: string, data: CachedSubmissionData): void => {
    cache.value.set(key, {
      data,
      timestamp: Date.now(),
    });
  };

  /**
   * Invalidate a specific cache entry.
   */
  const invalidate = (key: string): void => {
    cache.value.delete(key);
  };

  /**
   * Clear all cache entries.
   */
  const invalidateAll = (): void => {
    cache.value.clear();
  };

  return {
    get,
    set,
    invalidate,
    invalidateAll,
    buildKey,
    has,
  };
};
