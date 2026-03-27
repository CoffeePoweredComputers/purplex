/**
 * useProbeableCodeConfig - Manages Probeable Code problem configuration.
 *
 * This composable wraps the base useProbeConfig with Probeable Code-specific
 * descriptions and type names. It provides the same API but with descriptions
 * tailored for code implementation problems.
 *
 * Note: reference_solution and function_signature are handled by the main form
 * composable since they are inherited from SpecProblem (shared with eipl, refute, etc.)
 */

import { type ProbeMode, useProbeConfig, type UseProbeConfigReturn } from './useProbeConfig';

// ===== TYPES =====

// Re-export ProbeMode from base composable
export type { ProbeMode };

// Type alias for Probeable Code config (same as base ProbeConfig)
export interface ProbeableCodeConfig {
  show_function_signature: boolean;
  probe_mode: ProbeMode;
  max_probes: number;
  cooldown_attempts: number;
  cooldown_refill: number;
}

// Type alias for return type
export type UseProbeableCodeConfigReturn = UseProbeConfigReturn;

// ===== CONSTANTS =====

// Probeable Code-specific descriptions
export const PROBE_MODES: { value: ProbeMode; labelKey: string; descriptionKey: string }[] = [
  {
    value: 'block',
    labelKey: 'admin.editors.probeSettings.modes.block.label',
    descriptionKey: 'admin.editors.probeSettings.modes.block.codeDescription',
  },
  {
    value: 'cooldown',
    labelKey: 'admin.editors.probeSettings.modes.cooldown.label',
    descriptionKey: 'admin.editors.probeSettings.modes.cooldown.codeDescription',
  },
  {
    value: 'explore',
    labelKey: 'admin.editors.probeSettings.modes.explore.label',
    descriptionKey: 'admin.editors.probeSettings.modes.explore.codeDescription',
  },
];

// ===== COMPOSABLE =====

export const useProbeableCodeConfig = (): UseProbeableCodeConfigReturn => {
  // Simply delegate to the base composable
  return useProbeConfig();
};
