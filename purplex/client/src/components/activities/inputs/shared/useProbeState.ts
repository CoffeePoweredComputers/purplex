/**
 * useProbeState - Shared composable for probe functionality.
 *
 * Manages probe state, API calls, and utility functions for probeable activities.
 * Used by both ProbeableCodeInput and ProbeableSpecInput.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import type { ActivityProblem, ProbeHistoryEntry, ProbeParameter, ProbeStatus } from '../../types'

export function useProbeState(problem: ActivityProblem | (() => ActivityProblem)) {
  const { t } = useI18n()
  // Probe state
  const probing = ref(false)
  const probeError = ref<string | null>(null)
  const probeHistory = ref<ProbeHistoryEntry[]>([])
  const probeStatus = ref<ProbeStatus | null>(null)
  const probeInputs = reactive<Record<string, string>>({})

  // Support both direct problem object and computed problem
  const getProblem = () => typeof problem === 'function' ? problem() : problem

  // Get probe config from problem
  const probeConfig = computed(() => {
    const p = getProblem()
    // Check probe_config (primary), then input_config.probe (fallback)
    return p?.probe_config || p?.input_config?.probe || {}
  })

  const functionSignature = computed(() => probeConfig.value?.function_signature || null)

  // Function name is available from probe config or problem
  const functionName = computed(() => probeConfig.value?.function_name || getProblem()?.function_name || 'f')

  // Probe count display for UI
  const probeCountDisplay = computed(() => {
    if (!probeStatus.value) {
      return ''
    }
    if (probeStatus.value.mode === 'explore') {
      return '∞'
    }
    const remaining = probeStatus.value.probes_remaining ?? 0
    return `${remaining} left`
  })

  const parameters = computed((): ProbeParameter[] => {
    // Try to get from probe config first
    if (probeConfig.value?.parameters) {
      return probeConfig.value.parameters
    }
    // Fall back to parsing function signature
    const sig = functionSignature.value
    if (!sig) {
      return []
    }

    const match = sig.match(/\(([^)]*)\)/)
    if (!match) {
      return []
    }

    const paramsStr = match[1].trim()
    if (!paramsStr) {
      return []
    }

    return paramsStr.split(',').map((p: string) => {
      const parts = p.trim().split(':')
      return {
        name: parts[0].trim(),
        type: parts[1]?.trim() || 'Any'
      }
    })
  })

  const canProbe = computed(() => {
    // Assume can probe until status loaded
    if (!probeStatus.value) {
      return true
    }
    return probeStatus.value.can_probe
  })

  const probeStatusText = computed(() => {
    if (!probeStatus.value) {
      return t('feedback.codeSubmission.probeLoading')
    }
    return probeStatus.value.message
  })

  const probeStatusClass = computed(() => {
    if (!probeStatus.value) {
      return ''
    }
    if (probeStatus.value.mode === 'explore') {
      return 'status-explore'
    }
    if (probeStatus.value.can_probe) {
      return 'status-available'
    }
    return 'status-exhausted'
  })

  const hasValidInputs = computed(() => {
    // Check all parameters have values
    return parameters.value.every(p => {
      const value = probeInputs[p.name]
      return value !== undefined && value !== ''
    })
  })

  // Check if current inputs match any previous query (real-time duplicate detection)
  const duplicateEntry = computed(() => {
    if (!hasValidInputs.value) {return null}

    // Parse current inputs
    const parsedInputs: Record<string, unknown> = {}
    for (const param of parameters.value) {
      const rawValue = probeInputs[param.name]
      parsedInputs[param.name] = parseInputValue(rawValue, param.type)
    }

    const inputKey = JSON.stringify(parsedInputs)
    return probeHistory.value.find(
      entry => JSON.stringify(entry.input) === inputKey
    ) || null
  })

  const isDuplicate = computed(() => duplicateEntry.value !== null)

  const cachedResult = computed(() => duplicateEntry.value?.output ?? null)

  // Initialize probe inputs when parameters change
  watch(parameters, (params) => {
    params.forEach(p => {
      if (!(p.name in probeInputs)) {
        probeInputs[p.name] = ''
      }
    })
  }, { immediate: true })

  // Load probe status and history on mount
  onMounted(async () => {
    await loadProbeStatus()
    await loadProbeHistory()
  })

  // Watch for problem changes
  watch(() => getProblem()?.slug, async () => {
    await loadProbeStatus()
    await loadProbeHistory()
    // Reset inputs
    Object.keys(probeInputs).forEach(key => {
      probeInputs[key] = ''
    })
  })

  async function loadProbeStatus() {
    try {
      const p = getProblem()
      const response = await axios.get(`/api/problems/${p.slug}/probe/status/`)
      probeStatus.value = response.data
    } catch (_error) {
      // Failed to load probe status - will use defaults
    }
  }

  async function loadProbeHistory() {
    try {
      const p = getProblem()
      const response = await axios.get(`/api/problems/${p.slug}/probe/history/`)
      probeHistory.value = response.data.history || []
      if (response.data.probe_status) {
        probeStatus.value = response.data.probe_status
      }
    } catch (_error) {
      // Failed to load probe history - will start with empty history
    }
  }

  async function executeProbe() {
    if (!canProbe.value || probing.value) {
      return
    }

    probing.value = true
    probeError.value = null

    try {
      // Parse input values
      const parsedInputs: Record<string, unknown> = {}
      for (const param of parameters.value) {
        const rawValue = probeInputs[param.name]
        parsedInputs[param.name] = parseInputValue(rawValue, param.type)
      }

      const p = getProblem()
      const response = await axios.post(`/api/problems/${p.slug}/probe/`, {
        input: parsedInputs
      })

      if (response.data.success) {
        // Add to history (most recent first)
        probeHistory.value.unshift({
          input: parsedInputs,
          output: response.data.result,
          timestamp: new Date().toISOString()
        })
        // Limit history display
        if (probeHistory.value.length > 20) {
          probeHistory.value = probeHistory.value.slice(0, 20)
        }
      } else {
        probeError.value = response.data.error || 'Probe failed'
      }

      // Update probe status
      if (response.data.probe_status) {
        probeStatus.value = response.data.probe_status
      }
    } catch (error: unknown) {
      probeError.value = axios.isAxiosError(error) ? (error.response?.data?.error || 'Failed to probe oracle') : 'Failed to probe oracle'
    } finally {
      probing.value = false
    }
  }

  function parseInputValue(rawValue: string, type: string): unknown {
    const trimmed = rawValue.trim()

    // Try to parse as JSON first (handles arrays, objects, etc.)
    try {
      return JSON.parse(trimmed)
    } catch {
      // Fall back to type-specific parsing
    }

    const lowerType = type.toLowerCase()

    if (lowerType === 'int' || lowerType === 'integer') {
      const num = parseInt(trimmed, 10)
      return isNaN(num) ? trimmed : num
    }

    if (lowerType === 'float' || lowerType === 'number') {
      const num = parseFloat(trimmed)
      return isNaN(num) ? trimmed : num
    }

    if (lowerType === 'bool' || lowerType === 'boolean') {
      if (trimmed.toLowerCase() === 'true') {
        return true
      }
      if (trimmed.toLowerCase() === 'false') {
        return false
      }
      return trimmed
    }

    // Default: return as string
    return trimmed
  }

  function formatInput(input: Record<string, unknown>): string {
    const parts = Object.entries(input).map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    return parts.join(', ')
  }

  function formatOutput(output: unknown): string {
    if (output === null) {
      return 'None'
    }
    if (output === undefined) {
      return 'undefined'
    }
    return JSON.stringify(output)
  }

  function updateProbeInput(paramName: string, value: string) {
    probeInputs[paramName] = value
  }

  function formatFunctionCall(input: Record<string, unknown>): string {
    const args = Object.values(input).map(v => JSON.stringify(v)).join(', ')
    return `${functionName.value}(${args})`
  }

  return {
    // State
    probing,
    probeError,
    probeHistory,
    probeStatus,
    probeInputs,
    // Computed
    probeConfig,
    functionSignature,
    functionName,
    probeCountDisplay,
    parameters,
    canProbe,
    probeStatusText,
    probeStatusClass,
    hasValidInputs,
    isDuplicate,
    cachedResult,
    // Methods
    executeProbe,
    loadProbeStatus,
    loadProbeHistory,
    parseInputValue,
    formatInput,
    formatOutput,
    formatFunctionCall,
    updateProbeInput,
  }
}
