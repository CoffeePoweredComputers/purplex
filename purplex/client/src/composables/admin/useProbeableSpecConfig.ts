/**
 * useProbeableSpecConfig - Manages Probeable Spec problem configuration.
 *
 * Probeable Spec combines:
 * - Probe configuration (like Probeable Code) - student probes an oracle function
 * - Segmentation analysis (like EiPL) - student writes NL explanation
 *
 * This composable wraps the base useProbeConfig with Probeable Spec-specific
 * descriptions tailored for explanation-based problems.
 *
 * Note: Segmentation config is handled separately by useSegmentation composable.
 * This composable focuses on probe-specific settings for the Probeable Spec type.
 *
 * reference_solution and function_signature are handled by the main form
 * composable since they are inherited from SpecProblem.
 */

import { useProbeConfig, PROBE_MODES as BASE_PROBE_MODES, type ProbeMode } from './useProbeConfig';
import type { UseProbeConfigReturn } from './useProbeConfig';

// ===== TYPES =====

// Re-export ProbeMode from base composable
export type { ProbeMode };

// Type alias for Probeable Spec config (same as base ProbeConfig)
export interface ProbeableSpecConfig {
  show_function_signature: boolean;
  probe_mode: ProbeMode;
  max_probes: number;
  cooldown_attempts: number;
  cooldown_refill: number;
}

// Type alias for return type
export type UseProbeableSpecConfigReturn = UseProbeConfigReturn;

// ===== CONSTANTS =====

// Probeable Spec-specific descriptions (tailored for explanation tasks)
export const PROBE_MODES: { value: ProbeMode; labelKey: string; descriptionKey: string }[] = [
  {
    value: 'block',
    labelKey: 'admin.editors.probeSettings.modes.block.label',
    descriptionKey: 'admin.editors.probeSettings.modes.block.specDescription',
  },
  {
    value: 'cooldown',
    labelKey: 'admin.editors.probeSettings.modes.cooldown.label',
    descriptionKey: 'admin.editors.probeSettings.modes.cooldown.specDescription',
  },
  {
    value: 'explore',
    labelKey: 'admin.editors.probeSettings.modes.explore.label',
    descriptionKey: 'admin.editors.probeSettings.modes.explore.specDescription',
  },
];

// ===== COMPOSABLE =====

export const useProbeableSpecConfig = (): UseProbeableSpecConfigReturn => {
  // Simply delegate to the base composable
  return useProbeConfig();
};
