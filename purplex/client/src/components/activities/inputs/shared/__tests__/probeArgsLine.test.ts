import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import axios from 'axios'
import { parseArgsLine, splitTopLevel, stableStringify } from '../probeArgs'
import { useProbeState } from '../useProbeState'
import ProbePanel from '../ProbePanel.vue'
import type { ActivityProblem } from '../../../types'
import { withSetup } from '@/test/setup'

vi.mock('axios')

afterEach(() => {
  vi.clearAllMocks()
})

const PARAMS = ['tasks', 'start', 'label']

describe('splitTopLevel', () => {
  it('ignores commas nested in brackets or inside strings', () => {
    expect(splitTopLevel(`[1, 2], (3, 4), {'a': 1, 'b': 2}, "x, y", 'p\\', q'`)).toEqual([
      '[1, 2]',
      ' (3, 4)',
      ` {'a': 1, 'b': 2}`,
      ' "x, y"',
      ` 'p\\', q'`,
    ])
  })
})

describe('stableStringify', () => {
  it('ignores object key order at every level but keeps list order', () => {
    expect(stableStringify({ b: 2, a: { d: 1, c: [2, 1] } })).toBe(stableStringify({ a: { c: [2, 1], d: 1 }, b: 2 }))
    expect(stableStringify([1, 2])).not.toBe(stableStringify([2, 1]))
  })
})

describe('parseArgsLine', () => {
  it('maps positional arguments in signature order', () => {
    expect(parseArgsLine('["a", "b"], 9, "ci"', PARAMS)).toEqual({
      raw: { tasks: '["a", "b"]', start: '9', label: '"ci"' },
      lineError: null,
    })
  })

  it('maps keyword arguments by name, in any order', () => {
    expect(parseArgsLine('label="ci", tasks=[1, 2], start = 9', PARAMS)).toEqual({
      raw: { tasks: '[1, 2]', start: '9', label: '"ci"' },
      lineError: null,
    })
  })

  it('mixes positional and keyword arguments, keyword first included', () => {
    expect(parseArgsLine('[1], label="x", 3', PARAMS).raw).toEqual({ tasks: '[1]', start: '3', label: '"x"' })
    expect(parseArgsLine('label="x", [1], 3', PARAMS)).toEqual({
      raw: { tasks: '[1]', start: '3', label: '"x"' },
      lineError: null,
    })
  })

  it('keeps commas inside brackets and strings within one argument', () => {
    expect(parseArgsLine(`{'a': 1, 'b': 2}, (1, 2), "x, y=3"`, PARAMS).raw).toEqual({
      tasks: `{'a': 1, 'b': 2}`,
      start: '(1, 2)',
      label: '"x, y=3"',
    })
  })

  it('does not treat == or a string containing = as a keyword', () => {
    expect(parseArgsLine('x == 1, "a=b"', PARAMS).raw).toEqual({ tasks: 'x == 1', start: '"a=b"', label: '' })
  })

  it('allows a trailing comma', () => {
    expect(parseArgsLine('[1], 2, "z",', PARAMS)).toEqual({
      raw: { tasks: '[1]', start: '2', label: '"z"' },
      lineError: null,
    })
  })

  it('reports an unknown keyword', () => {
    expect(parseArgsLine('[1], stop=3', PARAMS).lineError).toEqual({ code: 'unknownKeyword', name: 'stop' })
  })

  it('reports an argument given twice, by keyword or by position', () => {
    expect(parseArgsLine('start=1, start=2', PARAMS).lineError).toEqual({ code: 'duplicateArgument', name: 'start' })
    expect(parseArgsLine('1, tasks=[2]', PARAMS).lineError).toEqual({ code: 'duplicateArgument', name: 'tasks' })
  })

  it('reports a positional argument whose slot a keyword already took', () => {
    expect(parseArgsLine('tasks=[1], [2]', PARAMS).lineError).toEqual({
      code: 'positionalAfterKeyword',
      name: 'tasks',
    })
    expect(parseArgsLine('x=1, 2', ['x', 'y']).lineError).toEqual({ code: 'positionalAfterKeyword', name: 'x' })
    // A keyword for a later parameter leaves the earlier slots to positionals
    expect(parseArgsLine('label="c", [1], 2', PARAMS)).toEqual({
      raw: { tasks: '[1]', start: '2', label: '"c"' },
      lineError: null,
    })
  })

  it('accepts non-ASCII parameter names as keywords', () => {
    expect(parseArgsLine('número=1', ['número'])).toEqual({ raw: { número: '1' }, lineError: null })
    expect(parseArgsLine('café = 2', ['x', 'café']).raw).toEqual({ x: '', café: '2' })
  })

  it('reports too many positional arguments', () => {
    expect(parseArgsLine('1, 2, 3, 4', PARAMS)).toEqual({
      raw: { tasks: '1', start: '2', label: '3' },
      lineError: { code: 'tooManyPositional', name: '' },
    })
  })

  it('reports an empty argument between commas without using a slot', () => {
    expect(parseArgsLine('1,,2', PARAMS)).toEqual({
      raw: { tasks: '1', start: '2', label: '' },
      lineError: { code: 'emptyArgument', name: '' },
    })
    expect(parseArgsLine('1, ,2', ['x', 'y']).lineError).toEqual({ code: 'emptyArgument', name: '' })
    expect(parseArgsLine(',1', ['x']).lineError).toEqual({ code: 'emptyArgument', name: '' })
  })

  it('maps empty text to empty values with no error', () => {
    for (const text of ['', '   ']) {
      expect(parseArgsLine(text, PARAMS)).toEqual({
        raw: { tasks: '', start: '', label: '' },
        lineError: null,
      })
    }
  })

  it('leaves the values of the template empty', () => {
    expect(parseArgsLine('tasks=, start=, label=', PARAMS)).toEqual({
      raw: { tasks: '', start: '', label: '' },
      lineError: null,
    })
  })
})

describe('useProbeState call line', () => {
  function setup(signature: string) {
    vi.mocked(axios.get).mockResolvedValue({ data: { can_probe: true, mode: 'explore' } })
    const problem = {
      slug: 'line-probe',
      function_name: 'schedule',
      probe_config: { function_signature: signature, function_name: 'schedule' },
    } as unknown as ActivityProblem
    return withSetup(() => useProbeState(problem))
  }

  it('builds the keyword template from the parameters', () => {
    const state = setup('def schedule(tasks: list[str], start: int) -> int')
    expect(state.argsTemplate.value).toBe('tasks=, start=')
  })

  it('posts the parsed values of a valid line', async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { success: true, result: 3 } })
    const state = setup('def schedule(tasks: list[str], start: int) -> int')
    await flushPromises()

    state.setArgsLine(`['a', "b"], start=9`)
    await nextTick()
    expect(state.argsLine.value).toBe(`['a', "b"], start=9`)
    expect(state.probeInputs).toEqual({ tasks: `['a', "b"]`, start: '9' })
    expect(state.hasValidInputs.value).toBe(true)

    await state.executeProbe()
    expect(axios.post).toHaveBeenCalledWith('/api/problems/line-probe/probe/', {
      input: { tasks: ['a', 'b'], start: 9 },
    })
  })

  it('posts a single-quoted str argument without its quotes', async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { success: true, result: ['xa'] } })
    const state = setup('def schedule(tasks: list[str], prefix: str) -> list[str]')
    await flushPromises()
    state.setArgsLine(`['a'], 'x'`)
    expect(state.hasValidInputs.value).toBe(true)
    await state.executeProbe()
    expect(axios.post).toHaveBeenCalledWith('/api/problems/line-probe/probe/', {
      input: { tasks: ['a'], prefix: 'x' },
    })
  })

  it('blocks an unterminated str literal with a per-parameter error', async () => {
    const state = setup('def schedule(tasks: list[str], prefix: str) -> list[str]')
    await flushPromises()
    state.setArgsLine(`['a'], "abc`)
    expect(state.inputErrors.value).toEqual({ prefix: 'Not a valid Python value' })
    expect(state.hasValidInputs.value).toBe(false)
  })

  it('blocks a list[str] given integers, with a per-parameter error', async () => {
    const state = setup('def schedule(tasks: list[str], start: int) -> int')
    await flushPromises()
    state.setArgsLine('[1, 2], 9')
    expect(state.inputErrors.value).toEqual({ tasks: 'Every item must be str' })
    expect(state.hasValidInputs.value).toBe(false)
    await state.executeProbe()
    expect(axios.post).not.toHaveBeenCalled()
  })

  it('translates line errors and blocks the probe while one is present', async () => {
    const state = setup('def schedule(start: int) -> int')
    await flushPromises()

    state.setArgsLine('5, stop=3')
    expect(state.lineError.value).toBe('Unknown argument stop')
    expect(state.hasValidInputs.value).toBe(false)

    state.setArgsLine('5, start=3')
    expect(state.lineError.value).toBe('Argument start given twice')

    state.setArgsLine('5, 6')
    expect(state.lineError.value).toBe('Too many arguments for schedule')
    expect(state.probeInputs.start).toBe('5')
    await state.executeProbe()
    expect(axios.post).not.toHaveBeenCalled()

    state.setArgsLine('5,,')
    expect(state.lineError.value).toBe('Empty argument between commas')

    state.setArgsLine('5')
    expect(state.lineError.value).toBeNull()
    expect(state.hasValidInputs.value).toBe(true)
  })

  it('requires every parameter to have a value', () => {
    const state = setup('def schedule(tasks: list[str], start: int) -> int')
    state.setArgsLine('tasks=["a"]')
    expect(state.probeInputs.start).toBe('')
    expect(state.lineError.value).toBeNull()
    expect(state.hasValidInputs.value).toBe(false)
  })

  it('treats a matching probe as a duplicate regardless of argument style', async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { success: true, result: 3 } })
    const state = setup('def schedule(tasks: list[str], start: int) -> int')
    await flushPromises()
    state.setArgsLine('["a"], 9')
    await state.executeProbe()
    state.setArgsLine(`start=9, tasks=['a']`)
    await nextTick()
    expect(state.isDuplicate.value).toBe(true)
  })

  it('treats a dict with its keys in another order as a duplicate', async () => {
    vi.mocked(axios.post).mockResolvedValue({ data: { success: true, result: 3 } })
    const state = setup('def total(m: dict[str, int]) -> int')
    await flushPromises()
    state.setArgsLine(`{'a': 1, 'b': 2}`)
    await state.executeProbe()
    state.setArgsLine(`{'b': 2, 'a': 1}`)
    await nextTick()
    expect(state.isDuplicate.value).toBe(true)
    state.setArgsLine(`{'b': 2, 'a': 3}`)
    await nextTick()
    expect(state.isDuplicate.value).toBe(false)
  })
})

function mountPanel(overrides: Record<string, unknown> = {}) {
  return mount(ProbePanel, {
    attachTo: document.body,
    props: {
      functionName: 'schedule',
      probeStatusClass: 'status-available',
      probeCountDisplay: '2 left',
      probeStatusText: '',
      probeParams: [
        { name: 'tasks', type: 'list[str]' },
        { name: 'start', type: 'int' },
      ],
      argsLine: '',
      argsTemplate: 'tasks=, start=',
      lineError: null,
      canProbe: true,
      isExecuting: false,
      hasValidInputs: false,
      inputErrors: {},
      probeHistory: [],
      probeError: null,
      isDuplicate: false,
      cachedResult: null,
      formatFunctionCall: (input: Record<string, unknown>) => `schedule(${Object.values(input).join(', ')})`,
      formatOutput: (output: unknown) => JSON.stringify(output),
      ...overrides,
    },
  })
}

describe('ProbePanel call line', () => {
  it('renders the function name and parentheses around one accessible argument editor', () => {
    const wrapper = mountPanel()
    const args = wrapper.find('#probe-args')
    expect(wrapper.find('.call-shell').text().replace(/\s/g, '')).toBe('schedule()')
    expect(args.attributes('role')).toBe('textbox')
    // Enter probes rather than breaking the line, so it is single-line to AT
    expect(args.attributes('aria-multiline')).toBe('false')
    // The keyboard behaviour (Enter probes, Tab fills names) is described to AT
    expect(args.attributes('aria-describedby')).toBe('probe-args-help')
    expect(wrapper.find('#probe-args-help').text()).toBe(
      'Enter probes. Tab on an empty line fills in the argument names.'
    )
    expect(args.attributes('aria-label')).toBe('Arguments for schedule')
    // Signature visible: the placeholder carries each parameter's declared type
    expect(args.attributes('data-placeholder')).toBe('tasks: list[str], start: int')
    expect(args.attributes('contenteditable')).toBe('plaintext-only')
    expect(args.attributes('aria-invalid')).toBeUndefined()
    // ")" follows the editor directly, with no whitespace text between them
    expect(args.element.nextSibling).toBe(wrapper.findAll('.fn-paren')[1].element)
    wrapper.unmount()
  })

  it('shows parameter names in the placeholder even when types are hidden', () => {
    const wrapper = mountPanel({ probeParams: [{ name: 'a', type: '' }, { name: 'b', type: '' }] })
    expect(wrapper.find('#probe-args').attributes('data-placeholder')).toBe('a, b')
    wrapper.unmount()
  })

  it('emits the typed text', async () => {
    const wrapper = mountPanel()
    const args = wrapper.find('#probe-args')
    args.element.textContent = '[1], 2'
    await args.trigger('input')
    expect(wrapper.emitted('update-args')).toEqual([['[1], 2']])
    wrapper.unmount()
  })

  it('inserts the template on Tab only when the line is empty', async () => {
    const wrapper = mountPanel()
    const args = wrapper.find('#probe-args')
    await args.trigger('keydown', { key: 'Tab' })
    expect(args.element.textContent).toBe('tasks=, start=')
    expect(wrapper.emitted('update-args')).toEqual([['tasks=, start=']])
    // Caret sits after the first "="
    const range = window.getSelection()?.getRangeAt(0)
    expect(range?.startOffset).toBe('tasks='.length)

    await args.trigger('keydown', { key: 'Tab' })
    expect(wrapper.emitted('update-args')).toHaveLength(1)
    wrapper.unmount()
  })

  it('inserts the template from the fill button', async () => {
    const wrapper = mountPanel()
    await wrapper.find('button.fill-args-btn').trigger('click')
    expect(wrapper.find('#probe-args').element.textContent).toBe('tasks=, start=')
    expect(wrapper.emitted('update-args')).toEqual([['tasks=, start=']])
    wrapper.unmount()
  })

  it('probes on Enter only when valid, and never on Shift+Enter', async () => {
    const wrapper = mountPanel()
    const args = wrapper.find('#probe-args')
    await args.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('execute-probe')).toBeUndefined()

    await wrapper.setProps({ hasValidInputs: true })
    await args.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(wrapper.emitted('execute-probe')).toBeUndefined()
    await args.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('execute-probe')).toHaveLength(1)

    await wrapper.setProps({ isExecuting: true })
    await args.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('execute-probe')).toHaveLength(1)
    wrapper.unmount()
  })

  it('gives focus back to the line after a probe started from it', async () => {
    const wrapper = mountPanel({ hasValidInputs: true })
    const el = wrapper.find('#probe-args').element as HTMLElement
    el.focus()
    await wrapper.setProps({ isExecuting: true })
    // A browser drops focus from an element that stops being editable
    el.blur()
    expect(document.activeElement).not.toBe(el)
    await wrapper.setProps({ isExecuting: false })
    await nextTick()
    expect(document.activeElement).toBe(el)
    wrapper.unmount()
  })

  it('does not steal focus after a probe started from elsewhere', async () => {
    const wrapper = mountPanel({ hasValidInputs: true })
    const el = wrapper.find('#probe-args').element as HTMLElement
    await wrapper.setProps({ isExecuting: true })
    await wrapper.setProps({ isExecuting: false })
    await nextTick()
    expect(document.activeElement).not.toBe(el)
    wrapper.unmount()
  })

  it('pastes plain text on one line', () => {
    const wrapper = mountPanel()
    const args = wrapper.find('#probe-args')
    const el = args.element as HTMLElement
    el.focus()
    const range = document.createRange()
    range.selectNodeContents(el)
    window.getSelection()?.removeAllRanges()
    window.getSelection()?.addRange(range)

    const event = new Event('paste', { bubbles: true, cancelable: true }) as ClipboardEvent
    Object.defineProperty(event, 'clipboardData', { value: { getData: () => '[1,\n2]' } })
    el.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    expect(el.textContent).toBe('[1, 2]')
    expect(wrapper.emitted('update-args')?.slice(-1)).toEqual([['[1, 2]']])
    wrapper.unmount()
  })

  it('shows line and per-parameter errors and marks the editor invalid', () => {
    const wrapper = mountPanel({
      lineError: 'Unknown argument stop',
      inputErrors: { tasks: 'Every item must be str' },
    })
    expect(wrapper.find('li#probe-err-line').text()).toBe('Unknown argument stop')
    expect(wrapper.find('li#probe-err-tasks').text()).toBe('tasks: Every item must be str')
    const args = wrapper.find('#probe-args')
    expect(args.attributes('aria-invalid')).toBe('true')
    expect(args.attributes('aria-describedby')).toBe('probe-field-errors probe-args-help')
    expect(wrapper.find('ul#probe-field-errors').exists()).toBe(true)
    wrapper.unmount()
  })

  it('locks the editor and the fill button when probing is not allowed', () => {
    const wrapper = mountPanel({ canProbe: false })
    const args = wrapper.find('#probe-args')
    expect(args.attributes('contenteditable')).toBe('false')
    expect(args.attributes('aria-disabled')).toBe('true')
    expect(wrapper.find('button.fill-args-btn').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })

  it('follows a reset of the line from outside', async () => {
    const wrapper = mountPanel({ argsLine: '[1], 2' })
    const args = wrapper.find('#probe-args')
    expect(args.element.textContent).toBe('[1], 2')
    await wrapper.setProps({ argsLine: '' })
    expect(args.element.textContent).toBe('')
    wrapper.unmount()
  })

  it('falls back to contenteditable="true" and still pastes plain text where plaintext-only is unsupported', () => {
    // A browser without plaintext-only keeps its previous contentEditable value
    const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'contentEditable')
    Object.defineProperty(HTMLElement.prototype, 'contentEditable', {
      configurable: true,
      get: () => 'inherit',
      set: () => {},
    })
    let wrapper: ReturnType<typeof mountPanel> | undefined
    try {
      wrapper = mountPanel()
    } finally {
      if (descriptor) {
        Object.defineProperty(HTMLElement.prototype, 'contentEditable', descriptor)
      } else {
        delete (HTMLElement.prototype as { contentEditable?: string }).contentEditable
      }
    }
    const el = wrapper.find('#probe-args').element as HTMLElement
    expect(el.getAttribute('contenteditable')).toBe('true')

    el.focus()
    const range = document.createRange()
    range.selectNodeContents(el)
    window.getSelection()?.removeAllRanges()
    window.getSelection()?.addRange(range)
    const event = new Event('paste', { bubbles: true, cancelable: true }) as ClipboardEvent
    Object.defineProperty(event, 'clipboardData', { value: { getData: () => '<b>[1,</b>\r\n2]' } })
    el.dispatchEvent(event)

    expect(event.defaultPrevented).toBe(true)
    // Inserted as text: markup stays literal, line breaks become spaces
    expect(el.children).toHaveLength(0)
    expect(el.textContent).toBe('<b>[1,</b> 2]')
    expect(wrapper.emitted('update-args')?.slice(-1)).toEqual([['<b>[1,</b> 2]']])
    wrapper.unmount()
  })
})
