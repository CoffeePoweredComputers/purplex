import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import ace from 'ace-builds'

// These tests drive a REAL Ace editor so keybinding precedence is exercised
// end to end: a keydown on Ace's textarea goes through Ace's own key dispatch,
// where a Tab override registered by the component would win over
// indent/outdent. Only the VAceEditor wrapper is stubbed, so the test can hand
// the component a real editor through the `init` event.

vi.mock('@/utils/logger', () => ({
  log: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn()
  }
}))

vi.mock('vue3-ace-editor', () => ({
  VAceEditor: {
    name: 'VAceEditor',
    props: ['lang', 'theme', 'mode', 'style', 'value', 'options'],
    emits: ['init', 'update:value'],
    template: '<div class="mock-ace-editor"></div>'
  }
}))

vi.mock('ace-builds/src-noconflict/mode-python', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-tomorrow', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-tomorrow_night_eighties', () => ({}))

describe('Editor keyboard behaviour (real Ace)', () => {
  type RealAceEditor = import('ace-builds').Ace.Editor
  let wrapper: VueWrapper
  let host: HTMLElement
  let realEditor: RealAceEditor | null = null

  async function mountWithRealAce(
    props: Record<string, unknown> = {},
    { inDialog = false }: { inDialog?: boolean } = {}
  ) {
    host = document.createElement('div')
    document.body.appendChild(host)

    let aceParent: HTMLElement = host
    if (inDialog) {
      const dialog = document.createElement('div')
      dialog.setAttribute('role', 'dialog')
      const closeBtn = document.createElement('button')
      closeBtn.setAttribute('aria-label', 'Close modal')
      dialog.appendChild(closeBtn)
      host.appendChild(dialog)
      aceParent = dialog
    }
    const submitBtn = document.createElement('button')
    submitBtn.id = 'submitButton'
    host.appendChild(submitBtn)

    const aceEl = document.createElement('div')
    aceParent.appendChild(aceEl)
    realEditor = ace.edit(aceEl)

    const mountPoint = document.createElement('div')
    host.appendChild(mountPoint)
    const Editor = (await import('../Editor.vue')).default
    const w = mount(Editor, { props, attachTo: mountPoint })
    await w.findComponent({ name: 'VAceEditor' }).vm.$emit('init', realEditor)
    await nextTick()

    const textInput = aceEl.querySelector('.ace_text-input') as HTMLTextAreaElement
    return { w, editor: realEditor, textInput }
  }

  function pressKey(target: HTMLElement, key: string, keyCode: number, shiftKey = false) {
    target.dispatchEvent(new KeyboardEvent('keydown', {
      key, keyCode, shiftKey, bubbles: true, cancelable: true
    }))
  }

  const flushTimers = () => new Promise(resolve => setTimeout(resolve, 20))

  afterEach(() => {
    wrapper?.unmount()
    realEditor?.destroy()
    realEditor = null
    host?.remove()
  })

  it('does not register a Tab or Shift-Tab override', async () => {
    const { w, editor } = await mountWithRealAce()
    wrapper = w

    expect(editor.commands.byName.overrideTab).toBeUndefined()
    expect(editor.commands.byName.overrideShiftTab).toBeUndefined()
    expect(editor.commands.byName.exitEditor).toBeDefined()
  })

  it('Tab inserts indentation and keeps focus in the editor', async () => {
    const { w, editor, textInput } = await mountWithRealAce()
    wrapper = w
    editor.setValue('x = 1', -1)
    textInput.focus()
    expect(document.activeElement).toBe(textInput)

    pressKey(textInput, 'Tab', 9)
    await flushTimers()

    expect(editor.getValue()).toBe(`${editor.session.getTabString()}x = 1`)
    expect(document.activeElement).toBe(textInput)
  })

  it('Shift-Tab outdents the current line and keeps focus in the editor', async () => {
    const { w, editor, textInput } = await mountWithRealAce()
    wrapper = w
    const indent = editor.session.getTabString()
    editor.setValue(`${indent}x = 1`, 1)
    textInput.focus()

    pressKey(textInput, 'Tab', 9, true)
    await flushTimers()

    expect(editor.getValue()).toBe('x = 1')
    expect(document.activeElement).toBe(textInput)
  })

  it('Escape moves focus to #submitButton outside a dialog', async () => {
    const { w, textInput } = await mountWithRealAce()
    wrapper = w
    textInput.focus()

    pressKey(textInput, 'Escape', 27)
    await flushTimers()

    expect(document.activeElement).toBe(document.getElementById('submitButton'))
  })

  it('Escape moves focus to the dialog close button inside a [role="dialog"]', async () => {
    const { w, textInput } = await mountWithRealAce({}, { inDialog: true })
    wrapper = w
    textInput.focus()

    pressKey(textInput, 'Escape', 27)
    await flushTimers()

    expect(document.activeElement).toBe(
      document.querySelector('[role="dialog"] [aria-label="Close modal"]')
    )
  })

  it('renders the escape hint and links it to Ace\'s text input via aria-describedby', async () => {
    const { w, textInput } = await mountWithRealAce()
    wrapper = w

    const hint = wrapper.find('.editor-escape-hint')
    expect(hint.exists()).toBe(true)
    expect(hint.text()).toBe('Press Escape to leave the editor')
    const hintId = hint.attributes('id')
    expect(hintId).toBeTruthy()
    expect(textInput.getAttribute('aria-describedby')).toBe(hintId)
    expect(document.getElementById(hintId as string)).toBe(hint.element)
  })

  it('hides the escape hint and drops aria-describedby when readOnly', async () => {
    const { w, textInput } = await mountWithRealAce({ readOnly: true })
    wrapper = w

    expect(wrapper.find('.editor-escape-hint').exists()).toBe(false)
    expect(textInput.hasAttribute('aria-describedby')).toBe(false)
  })

  it('gives each editor instance a unique hint id', async () => {
    const Editor = (await import('../Editor.vue')).default
    const first = mount(Editor)
    const second = mount(Editor)

    const firstId = first.find('.editor-escape-hint').attributes('id')
    const secondId = second.find('.editor-escape-hint').attributes('id')
    expect(firstId).toBeTruthy()
    expect(firstId).not.toBe(secondId)

    first.unmount()
    second.unmount()
  })
})
