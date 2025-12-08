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

import { useProbeConfig, PROBE_MODES as BASE_PROBE_MODES, type ProbeMode } from './useProbeConfig';
import type { UseProbeConfigReturn } from './useProbeConfig';

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
export const PROBE_MODES: { value: ProbeMode; label: string; description: string }[] = [
  {
    value: 'block',
    label: 'Block Mode',
    description: 'Student gets a fixed number of probes. Once exhausted, they must submit code without further testing.',
  },
  {
    value: 'cooldown',
    label: 'Cooldown Mode',
    description: 'After initial probes are used, student can earn more probes by making submission attempts.',
  },
  {
    value: 'explore',
    label: 'Explore Mode',
    description: 'Unlimited probes. Student can test as many inputs as they want before submitting.',
  },
];

// ===== COMPOSABLE =====

export const useProbeableCodeConfig = (): UseProbeableCodeConfigReturn => {
  // Simply delegate to the base composable
  return useProbeConfig();
};
