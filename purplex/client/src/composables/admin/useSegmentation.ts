/**
 * useSegmentation - Manages segmentation configuration for EiPL problems.
 *
 * This composable handles the segmentation analysis configuration including:
 * - Enable/disable segmentation
 * - Threshold setting (number of segments for "good" vs "needs work")
 * - Example segments for relational and multi-structural responses
 */

import { reactive, readonly, computed, type DeepReadonly, type ComputedRef } from 'vue';

// ===== TYPES =====

/**
 * Segmentation example using parallel arrays format (matches backend)
 * - segments: array of text descriptions
 * - code_lines: array of line number arrays (parallel to segments)
 */
export interface SegmentationExample {
  prompt: string;
  segments: string[];
  code_lines: number[][];
}

export interface SegmentationConfig {
  enabled: boolean;
  threshold: number;
  examples: {
    relational: SegmentationExample;
    multi_structural: SegmentationExample;
  };
}

export interface UseSegmentationReturn {
  /** Readonly segmentation config */
  config: DeepReadonly<SegmentationConfig>;
  /** Whether segmentation is enabled */
  isEnabled: ComputedRef<boolean>;
  /** Current threshold */
  threshold: ComputedRef<number>;
  /** Relational example segments (text array) */
  relationalSegments: ComputedRef<string[]>;
  /** Relational example code lines (parallel array) */
  relationalCodeLines: ComputedRef<number[][]>;
  /** Multi-structural example segments (text array) */
  multiStructuralSegments: ComputedRef<string[]>;
  /** Multi-structural example code lines (parallel array) */
  multiStructuralCodeLines: ComputedRef<number[][]>;

  /** Set enabled state */
  setEnabled: (enabled: boolean) => void;
  /** Set threshold */
  setThreshold: (threshold: number) => void;
  /** Set relational prompt */
  setRelationalPrompt: (prompt: string) => void;
  /** Set multi-structural prompt */
  setMultiStructuralPrompt: (prompt: string) => void;

  /** Add a relational segment */
  addRelationalSegment: () => void;
  /** Remove a relational segment */
  removeRelationalSegment: (index: number) => void;
  /** Update relational segment text */
  updateRelationalSegmentText: (index: number, text: string) => void;
  /** Update relational segment code lines */
  updateRelationalSegmentCodeLines: (index: number, codeLines: number[]) => void;

  /** Add a multi-structural segment */
  addMultiStructuralSegment: () => void;
  /** Remove a multi-structural segment */
  removeMultiStructuralSegment: (index: number) => void;
  /** Update multi-structural segment text */
  updateMultiStructuralSegmentText: (index: number, text: string) => void;
  /** Update multi-structural segment code lines */
  updateMultiStructuralSegmentCodeLines: (index: number, codeLines: number[]) => void;

  /** Validate line range string */
  validateLineRange: (input: string) => boolean;
  /** Parse line range string to array */
  parseLineRange: (input: string) => number[];
  /** Format array to line range string */
  formatLineRange: (lines: number[]) => string;

  /** Load config from problem data */
  loadConfig: (config: SegmentationConfig | null | undefined) => void;
  /** Format config for API */
  formatForApi: () => SegmentationConfig | null;
  /** Reset to initial state */
  reset: () => void;
}

// ===== INITIAL STATE =====

const createInitialState = (): SegmentationConfig => ({
  enabled: false,
  threshold: 3,
  examples: {
    relational: {
      prompt: '',
      segments: [],
      code_lines: [],
    },
    multi_structural: {
      prompt: '',
      segments: [],
      code_lines: [],
    },
  },
});

// ===== COMPOSABLE =====

export const useSegmentation = (): UseSegmentationReturn => {
  const state = reactive<SegmentationConfig>(createInitialState());

  // ===== Computed =====

  const isEnabled = computed(() => state.enabled);
  const threshold = computed(() => state.threshold);
  const relationalSegments = computed(() => state.examples.relational.segments);
  const relationalCodeLines = computed(() => state.examples.relational.code_lines);
  const multiStructuralSegments = computed(() => state.examples.multi_structural.segments);
  const multiStructuralCodeLines = computed(() => state.examples.multi_structural.code_lines);

  // ===== Basic Setters =====

  const setEnabled = (enabled: boolean): void => {
    state.enabled = enabled;
  };

  const setThreshold = (threshold: number): void => {
    state.threshold = Math.max(1, Math.min(10, threshold));
  };

  const setRelationalPrompt = (prompt: string): void => {
    state.examples.relational.prompt = prompt;
  };

  const setMultiStructuralPrompt = (prompt: string): void => {
    state.examples.multi_structural.prompt = prompt;
  };

  // ===== Relational Segments =====

  const addRelationalSegment = (): void => {
    state.examples.relational.segments.push('');
    state.examples.relational.code_lines.push([]);
  };

  const removeRelationalSegment = (index: number): void => {
    state.examples.relational.segments.splice(index, 1);
    state.examples.relational.code_lines.splice(index, 1);
  };

  const updateRelationalSegmentText = (index: number, text: string): void => {
    if (index >= 0 && index < state.examples.relational.segments.length) {
      state.examples.relational.segments[index] = text;
    }
  };

  const updateRelationalSegmentCodeLines = (index: number, codeLines: number[]): void => {
    if (index >= 0 && index < state.examples.relational.code_lines.length) {
      state.examples.relational.code_lines[index] = codeLines;
    }
  };

  // ===== Multi-Structural Segments =====

  const addMultiStructuralSegment = (): void => {
    state.examples.multi_structural.segments.push('');
    state.examples.multi_structural.code_lines.push([]);
  };

  const removeMultiStructuralSegment = (index: number): void => {
    state.examples.multi_structural.segments.splice(index, 1);
    state.examples.multi_structural.code_lines.splice(index, 1);
  };

  const updateMultiStructuralSegmentText = (index: number, text: string): void => {
    if (index >= 0 && index < state.examples.multi_structural.segments.length) {
      state.examples.multi_structural.segments[index] = text;
    }
  };

  const updateMultiStructuralSegmentCodeLines = (index: number, codeLines: number[]): void => {
    if (index >= 0 && index < state.examples.multi_structural.code_lines.length) {
      state.examples.multi_structural.code_lines[index] = codeLines;
    }
  };

  // ===== Line Range Utilities =====

  /**
   * Validate line range string (e.g., "1-3" or "1,2,3" or "1")
   */
  const validateLineRange = (input: string): boolean => {
    if (!input.trim()) return true; // Empty is valid
    return /^(\d+(-\d+)?)(,\s*\d+(-\d+)?)*$/.test(input.trim());
  };

  /**
   * Parse line range string to array of line numbers
   */
  const parseLineRange = (input: string): number[] => {
    if (!input.trim()) return [];

    const lines: number[] = [];
    const parts = input.split(',').map(p => p.trim());

    for (const part of parts) {
      if (part.includes('-')) {
        const [start, end] = part.split('-').map(n => parseInt(n, 10));
        for (let i = start; i <= end; i++) {
          if (!lines.includes(i)) lines.push(i);
        }
      } else {
        const num = parseInt(part, 10);
        if (!isNaN(num) && !lines.includes(num)) {
          lines.push(num);
        }
      }
    }

    return lines.sort((a, b) => a - b);
  };

  /**
   * Format array of line numbers to compact string
   */
  const formatLineRange = (lines: number[]): string => {
    if (!lines || !lines.length) return '';

    const sorted = [...lines].sort((a, b) => a - b);
    const ranges: string[] = [];
    let start = sorted[0];
    let end = sorted[0];

    for (let i = 1; i <= sorted.length; i++) {
      if (sorted[i] === end + 1) {
        end = sorted[i];
      } else {
        ranges.push(start === end ? String(start) : `${start}-${end}`);
        start = sorted[i];
        end = sorted[i];
      }
    }

    return ranges.join(', ');
  };

  // ===== Persistence =====

  const loadConfig = (config: SegmentationConfig | null | undefined): void => {
    if (!config) {
      reset();
      return;
    }

    state.enabled = config.enabled ?? false;
    state.threshold = config.threshold ?? 3;

    // Load examples directly - format now matches backend (parallel arrays)
    if (config.examples) {
      const rel = config.examples.relational;
      state.examples.relational = {
        prompt: rel?.prompt ?? '',
        segments: Array.isArray(rel?.segments) ? [...rel.segments] : [],
        code_lines: Array.isArray(rel?.code_lines) ? rel.code_lines.map(lines => [...lines]) : [],
      };

      const multi = config.examples.multi_structural;
      state.examples.multi_structural = {
        prompt: multi?.prompt ?? '',
        segments: Array.isArray(multi?.segments) ? [...multi.segments] : [],
        code_lines: Array.isArray(multi?.code_lines) ? multi.code_lines.map(lines => [...lines]) : [],
      };
    }
  };

  /**
   * Format config for API.
   * Always returns a valid config object (never null) to avoid backend validation errors.
   * When disabled, returns a minimal config with enabled: false.
   */
  const formatForApi = (): SegmentationConfig => {
    // Filter out empty segments and their corresponding code_lines
    const filterExample = (example: SegmentationExample): SegmentationExample => {
      const filteredSegments: string[] = [];
      const filteredCodeLines: number[][] = [];

      example.segments.forEach((text, idx) => {
        if (text.trim()) {
          filteredSegments.push(text);
          filteredCodeLines.push(example.code_lines[idx] || []);
        }
      });

      return {
        prompt: example.prompt,
        segments: filteredSegments,
        code_lines: filteredCodeLines,
      };
    };

    // Always return a valid config object
    return {
      enabled: state.enabled,
      threshold: state.threshold,
      examples: state.enabled ? {
        relational: filterExample(state.examples.relational),
        multi_structural: filterExample(state.examples.multi_structural),
      } : {
        // Return empty but valid structure when disabled
        relational: { prompt: '', segments: [], code_lines: [] },
        multi_structural: { prompt: '', segments: [], code_lines: [] },
      },
    };
  };

  const reset = (): void => {
    const initial = createInitialState();
    Object.assign(state, initial);
  };

  return {
    config: readonly(state),
    isEnabled,
    threshold,
    relationalSegments,
    relationalCodeLines,
    multiStructuralSegments,
    multiStructuralCodeLines,
    setEnabled,
    setThreshold,
    setRelationalPrompt,
    setMultiStructuralPrompt,
    addRelationalSegment,
    removeRelationalSegment,
    updateRelationalSegmentText,
    updateRelationalSegmentCodeLines,
    addMultiStructuralSegment,
    removeMultiStructuralSegment,
    updateMultiStructuralSegmentText,
    updateMultiStructuralSegmentCodeLines,
    validateLineRange,
    parseLineRange,
    formatLineRange,
    loadConfig,
    formatForApi,
    reset,
  };
};
