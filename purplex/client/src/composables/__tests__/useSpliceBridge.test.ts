import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type App, createApp, defineComponent } from 'vue'
import { testI18n } from '@/test/setup'
import { useSpliceBridge } from '../useSpliceBridge'

const HOST_ORIGIN = 'https://host.example'

// Local mount helper (rather than the shared withSetup()) so each test's app can be
// unmounted in afterEach — this exercises the onUnmounted cleanup path and prevents
// message listeners from accumulating across tests in this file.
let activeApps: App[] = []

function mountBridge<T>(composable: () => T): T {
  let result!: T
  const app = createApp(defineComponent({
    setup() {
      result = composable()
      return () => null
    },
  }))
  app.use(testI18n)
  app.mount(document.createElement('div'))
  activeApps.push(app)
  return result
}

class MockResizeObserver {
  static instances: MockResizeObserver[] = []
  callback: ResizeObserverCallback
  observed: Element | null = null

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback
    MockResizeObserver.instances.push(this)
  }

  observe(el: Element): void {
    this.observed = el
  }

  unobserve(): void {
    this.observed = null
  }

  disconnect(): void {
    this.observed = null
  }

  trigger(contentRect: { height: number; width: number }): void {
    this.callback(
      [{ contentRect } as ResizeObserverEntry],
      this as unknown as ResizeObserver
    )
  }
}

function postMessageCalls(spy: ReturnType<typeof vi.spyOn>) {
  return spy.mock.calls.map((call) => call[0] as Record<string, unknown>)
}

function setup(options: Parameters<typeof useSpliceBridge>[0] = {}) {
  return mountBridge(() =>
    useSpliceBridge({ allowedOrigin: HOST_ORIGIN, responseTimeoutMs: 50, ...options })
  )
}

function replyToLastRequest(postSpy: ReturnType<typeof vi.spyOn>, subject: string, extra: Record<string, unknown> = {}) {
  const calls = postMessageCalls(postSpy)
  const request = [...calls].reverse().find((call) => call.subject === subject.replace('.response', ''))
  const message_id = request?.message_id as string
  window.dispatchEvent(
    new MessageEvent('message', {
      data: { subject, message_id, ...extra },
      origin: HOST_ORIGIN,
    })
  )
  return message_id
}

describe('useSpliceBridge', () => {
  let postSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    MockResizeObserver.instances = []
    vi.stubGlobal('ResizeObserver', MockResizeObserver)
    postSpy = vi.spyOn(window.parent, 'postMessage').mockImplementation(() => {})
  })

  afterEach(() => {
    activeApps.forEach((app) => app.unmount())
    activeApps = []
    postSpy.mockRestore()
    vi.unstubAllGlobals()
  })

  it('sends SPLICE.getState on mount as the readiness handshake', () => {
    setup()

    const calls = postMessageCalls(postSpy)
    expect(calls).toHaveLength(1)
    expect(calls[0].subject).toBe('SPLICE.getState')
    expect(typeof calls[0].message_id).toBe('string')
  })

  it('normalizes a 0-100 score to 0..1 before posting reportScoreAndState', () => {
    const bridge = setup()

    const ok = bridge.reportScoreAndState(80, { step: 1 })

    expect(ok).toBe(true)
    const calls = postMessageCalls(postSpy)
    const reportCall = calls.find((c) => c.subject === 'SPLICE.reportScoreAndState')
    expect(reportCall?.score).toBeCloseTo(0.8)
  })

  it('clamps scores to the 0..1 range', () => {
    const bridge = setup()

    bridge.reportScoreAndState(0, {})
    bridge.reportScoreAndState(100, {})
    bridge.reportScoreAndState(150, {})

    const scores = postMessageCalls(postSpy)
      .filter((c) => c.subject === 'SPLICE.reportScoreAndState')
      .map((c) => c.score)
    expect(scores).toEqual([0, 1, 1])
  })

  it('round-trips state through reportScoreAndState unchanged', () => {
    const bridge = setup()
    const state = { code: 'print(1)', cursor: 4, nested: { ok: true } }

    bridge.reportScoreAndState(50, state)

    const calls = postMessageCalls(postSpy)
    const reportCall = calls.find((c) => c.subject === 'SPLICE.reportScoreAndState')
    expect(reportCall?.state).toEqual(state)
  })

  it('restores state from a matched SPLICE.getState.response', async () => {
    const bridge = setup()
    const state = { answer: 'restored' }

    replyToLastRequest(postSpy, 'SPLICE.getState.response', {
      state,
      user_id: 'user-123',
      context_id: 'ctx-456',
    })
    await vi.waitFor(() => expect(bridge.isReady.value).toBe(true))

    expect(bridge.restoredState.value).toEqual(state)
    expect(bridge.hostContext.value.userId).toBe('user-123')
    expect(bridge.hostContext.value.contextId).toBe('ctx-456')
  })

  it('does not block readiness when the host never replies to getState', async () => {
    const bridge = setup({ allowedOrigin: HOST_ORIGIN, responseTimeoutMs: 20 })

    expect(bridge.isReady.value).toBe(false)
    await vi.waitFor(() => expect(bridge.isReady.value).toBe(true), { timeout: 200 })
    expect(bridge.restoredState.value).toBeNull()
  })

  it('emits lti.frameResize when the observed element changes size', () => {
    const bridge = setup()
    const el = document.createElement('div')

    bridge.observeElement(el)
    expect(MockResizeObserver.instances).toHaveLength(1)
    MockResizeObserver.instances[0].trigger({ height: 320, width: 640 })

    const calls = postMessageCalls(postSpy)
    const resizeCall = calls.find((c) => c.subject === 'lti.frameResize')
    expect(resizeCall).toMatchObject({ height: 320, width: 640 })
  })

  it('ignores a reply whose message_id was never requested', async () => {
    const bridge = setup()

    window.dispatchEvent(
      new MessageEvent('message', {
        data: { subject: 'SPLICE.getState.response', message_id: 'not-a-real-id', state: { hijacked: true } },
        origin: HOST_ORIGIN,
      })
    )
    await new Promise((r) => setTimeout(r, 10))

    expect(bridge.restoredState.value).toBeNull()
  })

  it('ignores inbound messages whose subject is not SPLICE./lti.-prefixed', async () => {
    const bridge = setup()
    const calls = postMessageCalls(postSpy)
    const message_id = calls[0].message_id as string

    window.dispatchEvent(
      new MessageEvent('message', {
        data: { subject: 'some.other.protocol', message_id, state: { hijacked: true } },
        origin: HOST_ORIGIN,
      })
    )
    await new Promise((r) => setTimeout(r, 10))

    expect(bridge.restoredState.value).toBeNull()
  })

  it('posts to the host origin rather than "*" when the origin is known', () => {
    const bridge = setup()
    bridge.reportScoreAndState(50, {})

    const targets = postSpy.mock.calls.map((call) => call[1])
    expect(targets.length).toBeGreaterThan(0)
    targets.forEach((target) => expect(target).toBe(HOST_ORIGIN))
  })

  it('falls back to "*" only when no host origin is available', () => {
    setup({ allowedOrigin: '' })

    expect(postSpy.mock.calls[0][1]).toBe('*')
  })

  it('ignores replies from an unexpected origin', async () => {
    const bridge = setup()
    const calls = postMessageCalls(postSpy)
    const message_id = calls[0].message_id as string

    window.dispatchEvent(
      new MessageEvent('message', {
        data: { subject: 'SPLICE.getState.response', message_id, state: { spoofed: true } },
        origin: 'https://evil.example',
      })
    )
    await new Promise((r) => setTimeout(r, 10))

    expect(bridge.restoredState.value).toBeNull()
  })
})
