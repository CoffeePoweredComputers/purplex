import { beforeEach, describe, expect, it } from 'vitest'
import { useProbeConfig, type ProbeConfig, type ProbeMode } from '../useProbeConfig'

describe('useProbeConfig', () => {
  let probe: ReturnType<typeof useProbeConfig>

  beforeEach(() => {
    probe = useProbeConfig()
  })

  describe('initial state', () => {
    it('should initialize with default values', () => {
      expect(probe.showFunctionSignature.value).toBe(true)
      expect(probe.probeMode.value).toBe('block')
      expect(probe.maxProbes.value).toBe(10)
      expect(probe.cooldownAttempts.value).toBe(3)
      expect(probe.cooldownRefill.value).toBe(5)
    })

    it('should show max probes field for block mode', () => {
      expect(probe.showMaxProbesField.value).toBe(true)
    })

    it('should not show cooldown fields for block mode', () => {
      expect(probe.showCooldownFields.value).toBe(false)
    })
  })

  describe('probe mode field visibility', () => {
    it('should show/hide fields based on probe mode - block', () => {
      probe.setProbeMode('block')

      expect(probe.showMaxProbesField.value).toBe(true)
      expect(probe.showCooldownFields.value).toBe(false)
    })

    it('should show/hide fields based on probe mode - cooldown', () => {
      probe.setProbeMode('cooldown')

      expect(probe.showMaxProbesField.value).toBe(true)
      expect(probe.showCooldownFields.value).toBe(true)
    })

    it('should show/hide fields based on probe mode - explore', () => {
      probe.setProbeMode('explore')

      expect(probe.showMaxProbesField.value).toBe(false)
      expect(probe.showCooldownFields.value).toBe(false)
    })
  })

  describe('validate', () => {
    it('should validate based on probe mode - block with invalid max probes', () => {
      probe.setProbeMode('block')
      probe.loadConfig({ ...probe.config, max_probes: 0 })

      const result = probe.validate()

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('Max probes must be at least 1')
    })

    it('should validate cooldown mode - require valid cooldown values', () => {
      probe.setProbeMode('cooldown')
      probe.loadConfig({
        ...probe.config,
        probe_mode: 'cooldown',
        cooldown_attempts: 0,
        cooldown_refill: 0,
      })

      const result = probe.validate()

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('Cooldown attempts must be at least 1')
      expect(result.errors).toContain('Cooldown refill must be at least 1')
    })

    it('should not require maxProbes in explore mode', () => {
      probe.setProbeMode('explore')
      probe.loadConfig({
        ...probe.config,
        probe_mode: 'explore',
        max_probes: 0, // Would be invalid in other modes
      })

      const result = probe.validate()

      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })

    it('should pass validation with valid block mode config', () => {
      probe.setProbeMode('block')
      probe.setMaxProbes(5)

      const result = probe.validate()

      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })

    it('should pass validation with valid cooldown mode config', () => {
      probe.setProbeMode('cooldown')
      probe.setMaxProbes(10)
      probe.setCooldownAttempts(3)
      probe.setCooldownRefill(5)

      const result = probe.validate()

      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })
  })

  describe('loadConfig', () => {
    it('should load all config values', () => {
      const config: ProbeConfig = {
        show_function_signature: false,
        probe_mode: 'cooldown',
        max_probes: 15,
        cooldown_attempts: 5,
        cooldown_refill: 8,
      }

      probe.loadConfig(config)

      expect(probe.showFunctionSignature.value).toBe(false)
      expect(probe.probeMode.value).toBe('cooldown')
      expect(probe.maxProbes.value).toBe(15)
      expect(probe.cooldownAttempts.value).toBe(5)
      expect(probe.cooldownRefill.value).toBe(8)
    })

    it('should handle null config gracefully', () => {
      probe.setProbeMode('cooldown')
      probe.setMaxProbes(20)

      probe.loadConfig(null)

      // Should reset to defaults
      expect(probe.probeMode.value).toBe('block')
      expect(probe.maxProbes.value).toBe(10)
    })

    it('should use defaults for missing fields', () => {
      const partialConfig = {
        probe_mode: 'explore' as ProbeMode,
      } as Partial<ProbeConfig>

      probe.loadConfig(partialConfig)

      expect(probe.probeMode.value).toBe('explore')
      expect(probe.maxProbes.value).toBe(10) // Default
      expect(probe.cooldownAttempts.value).toBe(3) // Default
    })
  })

  describe('setters', () => {
    it('should set show function signature', () => {
      probe.setShowFunctionSignature(false)
      expect(probe.showFunctionSignature.value).toBe(false)

      probe.setShowFunctionSignature(true)
      expect(probe.showFunctionSignature.value).toBe(true)
    })

    it('should set probe mode', () => {
      probe.setProbeMode('explore')
      expect(probe.probeMode.value).toBe('explore')

      probe.setProbeMode('cooldown')
      expect(probe.probeMode.value).toBe('cooldown')
    })

    it('should set max probes with minimum of 1', () => {
      probe.setMaxProbes(5)
      expect(probe.maxProbes.value).toBe(5)

      probe.setMaxProbes(0)
      expect(probe.maxProbes.value).toBe(1)

      probe.setMaxProbes(-5)
      expect(probe.maxProbes.value).toBe(1)
    })

    it('should set cooldown attempts with minimum of 1', () => {
      probe.setCooldownAttempts(5)
      expect(probe.cooldownAttempts.value).toBe(5)

      probe.setCooldownAttempts(0)
      expect(probe.cooldownAttempts.value).toBe(1)
    })

    it('should set cooldown refill with minimum of 1', () => {
      probe.setCooldownRefill(10)
      expect(probe.cooldownRefill.value).toBe(10)

      probe.setCooldownRefill(0)
      expect(probe.cooldownRefill.value).toBe(1)
    })

    it('should floor decimal values', () => {
      probe.setMaxProbes(5.7)
      expect(probe.maxProbes.value).toBe(5)

      probe.setCooldownAttempts(3.9)
      expect(probe.cooldownAttempts.value).toBe(3)
    })
  })

  describe('getConfigForApi', () => {
    it('should return current config state', () => {
      probe.setShowFunctionSignature(false)
      probe.setProbeMode('cooldown')
      probe.setMaxProbes(20)
      probe.setCooldownAttempts(4)
      probe.setCooldownRefill(6)

      const config = probe.getConfigForApi()

      expect(config).toEqual({
        show_function_signature: false,
        probe_mode: 'cooldown',
        max_probes: 20,
        cooldown_attempts: 4,
        cooldown_refill: 6,
      })
    })
  })

  describe('validationError computed', () => {
    it('should return error message for invalid max probes in block mode', () => {
      probe.setProbeMode('block')
      probe.loadConfig({ ...probe.config, max_probes: 0 })

      expect(probe.validationError.value).toBe('Max probes must be at least 1')
    })

    it('should return error for invalid cooldown attempts', () => {
      probe.setProbeMode('cooldown')
      probe.loadConfig({
        ...probe.config,
        probe_mode: 'cooldown',
        cooldown_attempts: 0,
      })

      expect(probe.validationError.value).toBe('Cooldown attempts must be at least 1')
    })

    it('should return null when config is valid', () => {
      probe.setProbeMode('block')
      probe.setMaxProbes(5)

      expect(probe.validationError.value).toBe(null)
    })
  })

  describe('reset', () => {
    it('should reset to defaults', () => {
      probe.setShowFunctionSignature(false)
      probe.setProbeMode('explore')
      probe.setMaxProbes(50)
      probe.setCooldownAttempts(10)
      probe.setCooldownRefill(15)

      probe.reset()

      expect(probe.showFunctionSignature.value).toBe(true)
      expect(probe.probeMode.value).toBe('block')
      expect(probe.maxProbes.value).toBe(10)
      expect(probe.cooldownAttempts.value).toBe(3)
      expect(probe.cooldownRefill.value).toBe(5)
    })
  })
})
