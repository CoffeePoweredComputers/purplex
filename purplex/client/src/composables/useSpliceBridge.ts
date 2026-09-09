import { onMounted, onUnmounted, ref } from 'vue'
import { log } from '../utils/logger'

const logger = log.createComponentLogger('useSpliceBridge')

// Inbound messages must carry one of these subjects to be considered SPLICE traffic.
const SPLICE_SUBJECT_RE = /^(SPLICE\.|lti\.)/

// state must be structured-cloneable and small enough to postMessage cheaply.
const MAX_STATE_JSON_LENGTH = 32 * 1024

const DEFAULT_RESPONSE_TIMEOUT_MS = 5000

export interface SpliceHostContext {
  userId?: string
  userModel?: unknown
  contextId?: string
}

export interface UseSpliceBridgeOptions {
  /**
   * Expected origin of the SPLICE host window, used to validate inbound messages.
   * Defaults to the origin of document.referrer (how a same-origin-policy-respecting
   * iframe normally learns its parent's origin). When neither is available, origin
   * checking is skipped and message_id matching is the sole gate on inbound messages.
   */
  allowedOrigin?: string
  /** How long to wait for a host reply before treating it as "never coming" (ms). */
  responseTimeoutMs?: number
}

interface PendingRequest {
  resolve: (data: Record<string, unknown> | null) => void
  timeoutId: ReturnType<typeof setTimeout>
}

let messageCounter = 0
function nextMessageId(): string {
  messageCounter += 1
  return `splice-${Date.now()}-${messageCounter}`
}

function referrerOrigin(): string {
  try {
    return document.referrer ? new URL(document.referrer).origin : ''
  } catch {
    return ''
  }
}

/**
 * Owns all postMessage I/O with a SPLICE host: the getState handshake,
 * score/state reporting, iframe resize requests, and telemetry events.
 * Problem-type-agnostic — per-type adapters decide what goes in `state`.
 */
export function useSpliceBridge(options: UseSpliceBridgeOptions = {}) {
  const restoredState = ref<unknown>(null)
  const hostContext = ref<SpliceHostContext>({})
  const isReady = ref(false)

  const allowedOrigin = options.allowedOrigin ?? referrerOrigin()
  const responseTimeoutMs = options.responseTimeoutMs ?? DEFAULT_RESPONSE_TIMEOUT_MS

  const pending = new Map<string, PendingRequest>()
  let resizeObserver: ResizeObserver | null = null
  let lastHeight = -1
  let lastWidth = -1

  function post(subject: string, payload: Record<string, unknown> = {}): string {
    const message_id = nextMessageId()
    window.parent.postMessage({ subject, message_id, ...payload }, '*')
    return message_id
  }

  /** Posts a message and resolves with the matching reply, or null if it never arrives. */
  function request(subject: string, payload: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    return new Promise((resolve) => {
      const message_id = nextMessageId()
      const timeoutId = setTimeout(() => {
        pending.delete(message_id)
        resolve(null)
      }, responseTimeoutMs)
      pending.set(message_id, { resolve, timeoutId })
      window.parent.postMessage({ subject, message_id, ...payload }, '*')
    })
  }

  function handleMessage(event: MessageEvent): void {
    const data = event.data
    if (!data || typeof data !== 'object') {
      return
    }

    const { subject, message_id } = data as { subject?: unknown; message_id?: unknown }
    if (typeof subject !== 'string' || !SPLICE_SUBJECT_RE.test(subject)) {
      return
    }
    if (allowedOrigin && event.origin !== allowedOrigin) {
      logger.warn('Rejected SPLICE message from unexpected origin', { origin: event.origin, allowedOrigin })
      return
    }
    if (typeof message_id !== 'string' || !pending.has(message_id)) {
      // Either not a reply we're waiting on, or a duplicate/late arrival. Ignore either way.
      return
    }

    const entry = pending.get(message_id)!
    pending.delete(message_id)
    clearTimeout(entry.timeoutId)
    entry.resolve(data as Record<string, unknown>)
  }

  /** Sends SPLICE.getState — doubles as the "I'm ready" signal to the host. */
  function requestState(): void {
    request('SPLICE.getState').then((data) => {
      isReady.value = true

      if (!data) {
        logger.debug('SPLICE.getState.response not received; continuing without restored state')
        return
      }
      if (data.error) {
        logger.warn('SPLICE.getState.response returned an error', data.error)
      }

      restoredState.value = data.state ?? null
      hostContext.value = {
        userId: typeof data.user_id === 'string' ? data.user_id : undefined,
        userModel: data.user_model,
        contextId: typeof data.context_id === 'string' ? data.context_id : undefined,
      }
    })
  }

  function stateJsonLength(state: unknown): number | null {
    try {
      return JSON.stringify(state ?? null).length
    } catch {
      return null // not structured-cloneable
    }
  }

  /**
   * Reports completion to the host. `score` is the raw 0-100 Submission.score;
   * it's normalized to the 0..1 range SPLICE expects before sending.
   */
  function reportScoreAndState(score: number, state: unknown): boolean {
    const normalizedScore = Math.max(0, Math.min(1, score / 100))

    const jsonLength = stateJsonLength(state)
    if (jsonLength === null || jsonLength > MAX_STATE_JSON_LENGTH) {
      logger.error('Refusing to report state: not structured-cloneable or exceeds size cap', { jsonLength })
      return false
    }

    post('SPLICE.reportScoreAndState', { score: normalizedScore, state })
    return true
  }

  /** Fire-and-forget telemetry event. */
  function sendEvent(name: string, data?: unknown, error?: unknown): void {
    const payload: Record<string, unknown> = { name, data: data ?? null }
    if (error !== undefined) {
      payload.error = error
    }
    post('SPLICE.sendEvent', payload)
  }

  /** Starts watching `el` for size changes and asks the host to resize the iframe. */
  function observeElement(el: HTMLElement | null): void {
    resizeObserver?.disconnect()
    resizeObserver = null
    if (!el) {
      return
    }

    resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) {
        return
      }
      const height = Math.ceil(entry.contentRect.height)
      const width = Math.ceil(entry.contentRect.width)
      if (height === lastHeight && width === lastWidth) {
        return
      }
      lastHeight = height
      lastWidth = width
      // "lti." prefix is intentional — SPLICE reuses the LTI frame-resize message.
      post('lti.frameResize', { height, width })
    })
    resizeObserver.observe(el)
  }

  onMounted(() => {
    window.addEventListener('message', handleMessage)
    requestState()
  })

  onUnmounted(() => {
    window.removeEventListener('message', handleMessage)
    resizeObserver?.disconnect()
    resizeObserver = null
    pending.forEach(({ timeoutId }) => clearTimeout(timeoutId))
    pending.clear()
  })

  return {
    restoredState,
    hostContext,
    isReady,
    observeElement,
    reportScoreAndState,
    sendEvent,
  }
}
