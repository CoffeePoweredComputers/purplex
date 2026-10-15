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

/** Canonical primitive parameter types that probe inputs are validated against. */
export type PrimitiveType = 'int' | 'float' | 'bool' | 'str'

/** Error code for a probe input that does not match its declared primitive type. */
export type ProbeInputError = 'int' | 'intRange' | 'float' | 'bool'

export interface ParsedProbeInput {
  value: unknown
  error: ProbeInputError | null
}

// Must stay identical to _PRIMITIVE_ALIASES in
// purplex/problems_app/services/probe_service.py (issue #135).
const PRIMITIVE_ALIASES = new Map<string, PrimitiveType>([
  ['int', 'int'],
  ['integer', 'int'],
  ['float', 'float'],
  ['number', 'float'],
  ['bool', 'bool'],
  ['boolean', 'bool'],
  ['str', 'str'],
  ['string', 'str'],
])

const INT_PATTERN = /^[+-]?\d+$/
const BOOL_PATTERN = /^(true|false)$/i
// Python float literal syntax: no hex/binary/octal, which Number() would otherwise accept
const FLOAT_PATTERN = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/

/**
 * Map a declared parameter type hint to its canonical primitive type.
 *
 * Strips a trailing ` = default`, trims, lowercases, and resolves aliases.
 * A `= None` default is an implicit Optional and is not checked.
 * Returns null for anything that is not checked (missing hint, Any, list[int],
 * Optional[int], dict, custom classes, ...).
 */
export function normalizePrimitiveType(type: string | null | undefined): PrimitiveType | null {
  if (!type) {
    return null
  }
  const [base, ...defaultParts] = type.split('=')
  if (defaultParts.join('=').trim() === 'None') {
    return null
  }
  return PRIMITIVE_ALIASES.get(base.trim().toLowerCase()) ?? null
}

/**
 * Parse a raw probe input string according to its declared parameter type.
 *
 * Primitive types (int/float/bool/str) are validated strictly; str never errors.
 * Unknown or missing types fall back to JSON parsing, accepting Python-style
 * bare True/False/None, and fall back to the raw text when that fails.
 */
export function parseInputValue(rawValue: string, type: string | null | undefined): ParsedProbeInput {
  const text = rawValue.trim()

  switch (normalizePrimitiveType(type)) {
    case 'int':
      if (!INT_PATTERN.test(text)) {
        return { value: text, error: 'int' }
      }
      // JSON cannot carry ints above 2^53 losslessly, so refuse rather than corrupt
      return Number.isSafeInteger(Number(text))
        ? { value: Number(text), error: null }
        : { value: text, error: 'intRange' }
    case 'float': {
      const num = Number(text)
      return FLOAT_PATTERN.test(text) && Number.isFinite(num)
        ? { value: num, error: null }
        : { value: text, error: 'float' }
    }
    case 'bool':
      return BOOL_PATTERN.test(text)
        ? { value: text.toLowerCase() === 'true', error: null }
        : { value: text, error: 'bool' }
    case 'str':
      if (text.length >= 2 && text.startsWith('"') && text.endsWith('"')) {
        try {
          return { value: JSON.parse(text), error: null }
        } catch {
          // Not a valid JSON string literal - keep the raw text
        }
      }
      return { value: text, error: null }
    default: {
      // Untyped / unchecked: JSON first, accepting Python-style literals
      const pythonLiterals: Record<string, string> = { True: 'true', False: 'false', None: 'null' }
      const jsonText = pythonLiterals[text] ?? text
      try {
        return { value: JSON.parse(jsonText), error: null }
      } catch {
        return { value: text, error: null }
      }
    }
  }
}

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
    const remaining = probeStatus.value.remaining ?? 0
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
      // Keep the default on the type (e.g. "int = None") so normalizePrimitiveType
      // can see it; strip it from the name for untyped defaults like "x=3"
      const [namePart, ...typeParts] = p.split(':')
      return {
        name: namePart.split('=')[0].trim(),
        type: typeParts.join(':').trim() || 'Any'
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

  // Parse every current input once; shared by validation, duplicate detection and execution
  const parsedInputs = computed(() => {
    const values: Record<string, unknown> = {}
    const errors: Record<string, ProbeInputError> = {}
    for (const param of parameters.value) {
      const rawValue = probeInputs[param.name] ?? ''
      const { value, error } = parseInputValue(rawValue, param.type)
      values[param.name] = value
      if (error && rawValue !== '') {
        errors[param.name] = error
      }
    }
    return { values, errors }
  })

  // Translated per-field type errors, keyed by parameter name (non-empty fields only)
  const inputErrors = computed((): Record<string, string> => {
    const messages: Record<string, string> = {}
    for (const [name, code] of Object.entries(parsedInputs.value.errors)) {
      messages[name] = t(`problems.probe.invalidType.${code}`)
    }
    return messages
  })

  const hasValidInputs = computed(() => {
    // Every parameter has a value and none fails its declared type
    const allFilled = parameters.value.every(p => {
      const value = probeInputs[p.name]
      return value !== undefined && value !== ''
    })
    return allFilled && Object.keys(parsedInputs.value.errors).length === 0
  })

  // Check if current inputs match any previous query (real-time duplicate detection)
  const duplicateEntry = computed(() => {
    if (!hasValidInputs.value) {return null}

    const inputKey = JSON.stringify(parsedInputs.value.values)
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
    if (Object.keys(parsedInputs.value.errors).length > 0) {
      return
    }

    probing.value = true
    probeError.value = null

    try {
      // Snapshot parsed values so history records exactly what was sent
      const input = { ...parsedInputs.value.values }

      const p = getProblem()
      const response = await axios.post(`/api/problems/${p.slug}/probe/`, {
        input
      })

      if (response.data.success) {
        // Add to history (most recent first)
        probeHistory.value.unshift({
          input,
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
    inputErrors,
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
