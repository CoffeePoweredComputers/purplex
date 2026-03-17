/**
 * Problem Type Handlers Registry
 *
 * Maps problem types to their load/save handlers.
 * This eliminates manual if/else chains in useProblemEditor and ensures
 * all problem types are properly wired up.
 */

import type { ProblemDetailed } from '@/types';
import type { UseMcqOptionsReturn } from './useMcqOptions';
import type { UsePromptConfigReturn } from './usePromptConfig';
import type { UseDebugFixConfigReturn } from './useDebugFixConfig';
import type { UseProbeableCodeConfigReturn } from './useProbeableCodeConfig';
import type { UseProbeableSpecConfigReturn } from './useProbeableSpecConfig';
import type { UseRefuteConfigReturn } from './useRefuteConfig';
import type { UseSegmentationReturn } from './useSegmentation';

// ===== TYPES =====

/**
 * Bundle of composables passed to type handlers.
 * Only includes composables that handle type-specific data.
 */
export interface ComposableBundle {
  mcqOptions: UseMcqOptionsReturn;
  promptConfig: UsePromptConfigReturn;
  debugFixConfig: UseDebugFixConfigReturn;
  probeableCodeConfig: UseProbeableCodeConfigReturn;
  probeableSpecConfig: UseProbeableSpecConfigReturn;
  refuteConfig: UseRefuteConfigReturn;
  segmentation: UseSegmentationReturn;
}

/**
 * Handler for a specific problem type.
 * Each handler knows how to load and save its type-specific data.
 */
export interface ProblemTypeHandler {
  /** Load type-specific data from backend response into composables */
  load: (data: ProblemDetailed, composables: ComposableBundle) => void;
  /** Get type-specific data from composables for save payload */
  save: (composables: ComposableBundle) => Record<string, unknown>;
}

// ===== REGISTRY =====

/**
 * Registry mapping problem types to their handlers.
 * Add new problem types here to wire them into load/save.
 */
export const problemTypeHandlers: Record<string, ProblemTypeHandler> = {
  mcq: {
    load: (data, c) => {
      if (data.options) {
        c.mcqOptions.setOptions(data.options);
      }
      if (data.question_text !== undefined) {
        c.mcqOptions.setQuestionText(data.question_text);
      }
    },
    save: (c) => ({
      options: c.mcqOptions.getOptionsForApi(),
      question_text: c.mcqOptions.questionText.value,
    }),
  },

  eipl: {
    load: (data, c) => {
      if (data.segmentation_config) {
        c.segmentation.loadConfig(data.segmentation_config);
      }
    },
    save: (c) => ({
      segmentation_config: c.segmentation.formatForApi(),
      segmentation_threshold: c.segmentation.threshold.value,
      requires_highlevel_comprehension: c.segmentation.isEnabled.value,
    }),
  },

  prompt: {
    load: (data, c) => {
      // Load from either nested prompt_config or top-level fields
      if (data.prompt_config) {
        c.promptConfig.loadConfig(data.prompt_config);
      } else if (data.image_url) {
        c.promptConfig.loadConfig({
          image_url: data.image_url,
          image_alt_text: data.image_alt_text || '',
        });
      }
    },
    save: (c) => ({
      // Spread directly - backend expects image_url at top level
      ...c.promptConfig.getConfigForApi(),
    }),
  },

  debug_fix: {
    load: (data, c) => {
      c.debugFixConfig.loadConfig({
        buggy_code: data.buggy_code || '',
        bug_hints: data.bug_hints || [],
      });
    },
    save: (c) => ({ ...c.debugFixConfig.getConfigForApi() }),
  },

  probeable_code: {
    load: (data, c) => {
      if (data.probe_mode !== undefined) {
        c.probeableCodeConfig.loadConfig({
          show_function_signature: data.show_function_signature,
          probe_mode: data.probe_mode,
          max_probes: data.max_probes,
          cooldown_attempts: data.cooldown_attempts,
          cooldown_refill: data.cooldown_refill,
        });
      }
    },
    save: (c) => ({ ...c.probeableCodeConfig.getConfigForApi() }),
  },

  probeable_spec: {
    load: (data, c) => {
      // Probe config
      if (data.probe_mode !== undefined) {
        c.probeableSpecConfig.loadConfig({
          show_function_signature: data.show_function_signature,
          probe_mode: data.probe_mode,
          max_probes: data.max_probes,
          cooldown_attempts: data.cooldown_attempts,
          cooldown_refill: data.cooldown_refill,
        });
      }
      // Segmentation config (probeable_spec also supports segmentation)
      if (data.segmentation_config) {
        c.segmentation.loadConfig(data.segmentation_config);
      }
    },
    save: (c) => ({
      ...c.probeableSpecConfig.getConfigForApi(),
      segmentation_config: c.segmentation.formatForApi(),
      segmentation_threshold: c.segmentation.threshold.value,
      requires_highlevel_comprehension: c.segmentation.isEnabled.value,
    }),
  },

  refute: {
    load: (data, c) => {
      c.refuteConfig.loadConfig({
        claim_text: data.claim_text || '',
        claim_predicate: data.claim_predicate || '',
        expected_counterexample: data.expected_counterexample || '',
      });
    },
    save: (c) => ({ ...c.refuteConfig.getConfigForApi() }),
  },
};
