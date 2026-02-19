import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import CookieConsent from '../CookieConsent.vue'

const COOKIE_CONSENT_KEY = 'purplex_cookie_consent'

// Node 25 ships a built-in localStorage global that shadows happy-dom/jsdom.
// It's non-functional (no .clear(), .setItem(), etc.), so we stub it.
const store: Record<string, string> = {}
vi.stubGlobal('localStorage', {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => { store[key] = value },
  removeItem: (key: string) => { delete store[key] },
  clear: () => { Object.keys(store).forEach(k => delete store[k]) },
})

describe('CookieConsent', () => {
  beforeEach(() => {
    Object.keys(store).forEach(k => delete store[k])
  })

  it('shows banner when no consent stored', async () => {
    const wrapper = mount(CookieConsent)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.cookie-consent').exists()).toBe(true)
  })

  it('hides banner when consent already stored', async () => {
    store[COOKIE_CONSENT_KEY] = JSON.stringify({ essential: true })
    const wrapper = mount(CookieConsent)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.cookie-consent').exists()).toBe(false)
  })

  it('accept essential sets essential=true and analytics=false', async () => {
    const wrapper = mount(CookieConsent)
    await wrapper.vm.$nextTick()
    await wrapper.find('.cookie-consent__btn--essential').trigger('click')

    const stored = JSON.parse(store[COOKIE_CONSENT_KEY])
    expect(stored.essential).toBe(true)
    expect(stored.analytics).toBe(false)
    expect(stored.timestamp).toBeDefined()
  })

  it('accept all sets both essential and analytics to true', async () => {
    const wrapper = mount(CookieConsent)
    await wrapper.vm.$nextTick()
    await wrapper.find('.cookie-consent__btn--accept').trigger('click')

    const stored = JSON.parse(store[COOKIE_CONSENT_KEY])
    expect(stored.essential).toBe(true)
    expect(stored.analytics).toBe(true)
  })

  it('hides banner after essential click', async () => {
    const wrapper = mount(CookieConsent)
    await wrapper.vm.$nextTick()
    await wrapper.find('.cookie-consent__btn--essential').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.cookie-consent').exists()).toBe(false)
  })

  it('hides banner after accept all click', async () => {
    const wrapper = mount(CookieConsent)
    await wrapper.vm.$nextTick()
    await wrapper.find('.cookie-consent__btn--accept').trigger('click')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.cookie-consent').exists()).toBe(false)
  })
})
