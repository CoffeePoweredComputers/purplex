import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'

// Hoisted so vi.mock factories can reference them
const { mockRange } = vi.hoisted(() => {
  const mockRange = vi.fn().mockImplementation((startLine: number, startCol: number, endLine: number, endCol: number) => ({
    startLine,
    startColumn: startCol,
    endLine,
    endColumn: endCol
  }))
  return { mockRange }
})

// Mock dependencies
vi.mock('@/utils/logger', () => ({
  log: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn()
  }
}))

// Mock ace-builds with a working require() for Range
vi.mock('ace-builds', () => ({
  default: {
    require: vi.fn((module: string) => {
      if (module === 'ace/range') {
        return { Range: mockRange }
      }
      return {}
    })
  }
}))

// Mock VAceEditor component — minimal stub that accepts ref and emits init
vi.mock('vue3-ace-editor', () => ({
  VAceEditor: {
    name: 'VAceEditor',
    props: ['lang', 'theme', 'mode', 'style', 'value', 'options'],
    emits: ['init', 'update:value'],
    template: '<div class="mock-ace-editor"></div>'
  }
}))

vi.mock('ace-builds/src-noconflict/mode-python', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-clouds_midnight', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-chrome', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-monokai', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-github', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-solarized_dark', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-solarized_light', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-dracula', () => ({}))
vi.mock('ace-builds/src-noconflict/theme-tomorrow_night', () => ({}))

type Fn = ReturnType<typeof vi.fn>

// Shape of the mock ACE editor returned by createMockEditor
interface MockAceEditor {
  setOptions: Fn; setOption: Fn; getValue: Fn; setValue: Fn
  setTheme: Fn; setMode: Fn; resize: Fn; clearSelection: Fn
  container: { setAttribute: Fn; getAttribute: Fn; closest: Fn; style: Record<string, string> }
  commands: { addCommand: Fn; removeCommand: Fn }
  renderer: {
    $cursorLayer: { element: { style: { display: string } } }
    container: { style: { pointerEvents: string; userSelect: string } }
    $markerBack: { element: { style: { zIndex: string } } }
    updateLines: Fn; freeze?: Fn; unfreeze?: Fn
  }
  session: { getMode: Fn; addMarker: Fn; removeMarker: Fn }
  on: Fn; getCursorPosition: Fn; moveCursorToPosition: Fn; blur: Fn
}

// Factory for mock ACE editor instances
const createMockEditor = (initialValue = 'test code'): MockAceEditor => {
  const mock: MockAceEditor = {
    setOptions: vi.fn(),
    setOption: vi.fn(),
    getValue: vi.fn().mockReturnValue(initialValue),
    setValue: vi.fn().mockImplementation((val: string) => {
      // Mirror real ACE: getValue reflects the last setValue
      mock.getValue.mockReturnValue(val)
    }),
    setTheme: vi.fn(),
    setMode: vi.fn(),
    resize: vi.fn(),
    clearSelection: vi.fn(),
    container: {
      setAttribute: vi.fn(),
      getAttribute: vi.fn().mockReturnValue('0'),
      closest: vi.fn().mockReturnValue(null),
      style: {}
    },
    commands: {
      addCommand: vi.fn(),
      removeCommand: vi.fn()
    },
    renderer: {
      $cursorLayer: {
        element: { style: { display: '' } }
      },
      container: {
        style: {
          pointerEvents: '',
          userSelect: ''
        }
      },
      $markerBack: {
        element: { style: { zIndex: '' } }
      },
      updateLines: vi.fn()
    },
    session: {
      getMode: vi.fn().mockReturnValue({
        getTokenizer: vi.fn().mockReturnValue({
          getLineTokens: vi.fn().mockReturnValue({
            tokens: [
              { type: 'comment.line', value: '# comment' },
              { type: 'keyword', value: 'def' }
            ],
            state: 'start'
          })
        })
      }),
      addMarker: vi.fn().mockReturnValue(1),
      removeMarker: vi.fn()
    },
    on: vi.fn(),
    getCursorPosition: vi.fn().mockReturnValue({ row: 0, column: 0 }),
    moveCursorToPosition: vi.fn(),
    blur: vi.fn()
  }
  return mock
}

// Helper: mount Editor, emit init, return wrapper + mock + VAceEditor ref
async function mountAndInit(props: Record<string, unknown> = {}, editorValue?: string) {
  const Editor = (await import('../Editor.vue')).default
  const initialValue = (props.value as string) ?? ''
  const mockEditor = createMockEditor(editorValue ?? initialValue)
  const wrapper = mount(Editor, { props })
  const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
  await aceEditor.vm.$emit('init', mockEditor)
  await nextTick()
  // Clear call counts from init phase so tests only see post-init calls
  mockEditor.setValue.mockClear()
  mockEditor.resize.mockClear()
  mockEditor.session.addMarker.mockClear()
  mockEditor.session.removeMarker.mockClear()
  mockEditor.setOption.mockClear()
  mockRange.mockClear()
  return { wrapper, mockEditor, aceEditor }
}

describe('Editor Component', () => {
  let wrapper: VueWrapper

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Component Initialization', () => {
    it('should mount with default props', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor)

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.props()).toEqual({
        lang: 'python',
        theme: 'tomorrow_night',
        mode: 'python',
        height: '300px',
        width: '500px',
        showGutter: true,
        characterLimit: null,
        minLines: null,
        maxLines: null,
        extraLines: 0,
        value: '',
        readOnly: false,
        markers: [],
        tabTargetId: null,
        focusScopeSelector: null
      })
    })

    it('should render VAceEditor with correct props', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor, {
        props: {
          lang: 'python',
          theme: 'dracula',
          value: 'print("Hello")'
        }
      })

      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      expect(aceEditor.exists()).toBe(true)
      expect(aceEditor.props()).toMatchObject({
        lang: 'python',
        theme: 'dracula',
        mode: 'python',
        value: 'print("Hello")',
        style: { height: '300px', width: '500px' },
        options: { readOnly: false }
      })
    })
  })

  describe('Editor Initialization', () => {
    it('should set editor options on init event', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      const mockEditor = createMockEditor()

      await aceEditor.vm.$emit('init', mockEditor)

      expect(mockEditor.setOptions).toHaveBeenCalledWith({
        showGutter: true,
        showFoldWidgets: true,
        minLines: undefined,
        maxLines: undefined,
        readOnly: false,
        highlightActiveLine: false,
        highlightGutterLine: false,
        showPrintMargin: false,
        wrap: true,
        indentedSoftWrap: false
      })
    })

    it('should configure read-only mode correctly', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor, {
        props: { readOnly: true }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      const mockEditor = createMockEditor()

      await aceEditor.vm.$emit('init', mockEditor)

      expect(mockEditor.renderer.$cursorLayer.element.style.display).toBe('none')
      expect(mockEditor.setOptions).toHaveBeenCalledWith(
        expect.objectContaining({ readOnly: true })
      )
      expect(mockEditor.renderer.container.style.pointerEvents).toBe('none')
      expect(mockEditor.renderer.container.style.userSelect).toBe('text')
    })
  })

  describe('Value Handling', () => {
    it('should emit update:value on input', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })

      await aceEditor.vm.$emit('update:value', 'new code')

      expect(wrapper.emitted('update:value')).toBeTruthy()
      expect(wrapper.emitted('update:value')?.[0]).toEqual(['new code'])
    })
  })

  describe('Value Watcher — programmatic content updates', () => {
    it('should call setValue and resize(true) when value prop changes', async () => {
      ({ wrapper } = await mountAndInit({ value: 'original code' }))
      const { mockEditor: _mockEditor } = await mountAndInit({ value: 'original code' })
      // Re-do properly with the same wrapper
      wrapper.unmount()
      const result = await mountAndInit({ value: 'original code' })
      wrapper = result.wrapper
      const editor = result.mockEditor

      await wrapper.setProps({ value: 'modified code' })
      await nextTick()

      expect(editor.setValue).toHaveBeenCalledWith('modified code', 1)
      expect(editor.resize).toHaveBeenCalledWith(true)
    })

    it('should not call setValue or resize when value is unchanged', async () => {
      const result = await mountAndInit({ value: 'same code' })
      wrapper = result.wrapper

      await wrapper.setProps({ value: 'same code' })
      await nextTick()

      expect(result.mockEditor.setValue).not.toHaveBeenCalled()
      expect(result.mockEditor.resize).not.toHaveBeenCalled()
    })

    it('should call resize(true) exactly once per value change (no rAF)', async () => {
      const result = await mountAndInit({ value: 'before' })
      wrapper = result.wrapper

      await wrapper.setProps({ value: 'after' })
      await nextTick()

      expect(result.mockEditor.resize).toHaveBeenCalledTimes(1)
      expect(result.mockEditor.resize).toHaveBeenCalledWith(true)
    })

    it('should sync _contentBackup on VAceEditor after setValue', async () => {
      const result = await mountAndInit({ value: 'original' })
      wrapper = result.wrapper

      await wrapper.setProps({ value: 'updated' })
      await nextTick()

      const vAce = wrapper.findComponent({ name: 'VAceEditor' })
      expect((vAce.vm as unknown as { _contentBackup: string })._contentBackup).toBe('updated')
    })

    it('should never call freeze or unfreeze on the renderer', async () => {
      const result = await mountAndInit({ value: 'before' })
      wrapper = result.wrapper
      // Add freeze/unfreeze spies to verify they're never called
      result.mockEditor.renderer.freeze = vi.fn()
      result.mockEditor.renderer.unfreeze = vi.fn()

      await wrapper.setProps({ value: 'after' })
      await nextTick()

      expect(result.mockEditor.renderer.freeze).not.toHaveBeenCalled()
      expect(result.mockEditor.renderer.unfreeze).not.toHaveBeenCalled()
    })

    it('should call setValue before resize (correct ordering)', async () => {
      const result = await mountAndInit({ value: 'before' })
      wrapper = result.wrapper
      const callOrder: string[] = []
      result.mockEditor.setValue.mockImplementation((val: string) => {
        callOrder.push('setValue')
        result.mockEditor.getValue.mockReturnValue(val)
      })
      result.mockEditor.resize.mockImplementation(() => {
        callOrder.push('resize')
      })

      await wrapper.setProps({ value: 'after' })
      await nextTick()

      expect(callOrder).toEqual(['setValue', 'resize'])
    })
  })

  describe('Marker Application', () => {
    it('should apply markers when value changes and markers prop is set', async () => {
      const markers = [
        { row: 0, className: 'highlight-line' },
        { row: 2, className: 'highlight-step' }
      ]
      const result = await mountAndInit({ value: 'original', markers })
      wrapper = result.wrapper

      await wrapper.setProps({ value: 'modified' })
      await nextTick()

      // addMarker called once per marker
      expect(result.mockEditor.session.addMarker).toHaveBeenCalledTimes(2)
      // Range constructed for each marker row
      expect(mockRange).toHaveBeenCalledWith(0, 0, 0, 1)
      expect(mockRange).toHaveBeenCalledWith(2, 0, 2, 1)
    })

    it('should clear old markers before applying new ones on subsequent value change', async () => {
      let markerId = 10
      const result = await mountAndInit({
        value: 'original',
        markers: [{ row: 0, className: 'a' }]
      })
      wrapper = result.wrapper
      result.mockEditor.session.addMarker.mockImplementation(() => markerId++)

      // First change: applies markers, populates activeMarkerIds
      await wrapper.setProps({ value: 'first change' })
      await nextTick()
      expect(result.mockEditor.session.addMarker).toHaveBeenCalledTimes(1)

      // Reset to observe only the second change
      result.mockEditor.session.addMarker.mockClear()
      result.mockEditor.session.removeMarker.mockClear()

      // Second change: must clear old markers then apply new ones
      await wrapper.setProps({ value: 'second change' })
      await nextTick()

      expect(result.mockEditor.session.removeMarker).toHaveBeenCalledWith(10)
      expect(result.mockEditor.session.addMarker).toHaveBeenCalledTimes(1)
    })

    it('should reapply markers when markers prop changes independently of value', async () => {
      const result = await mountAndInit({
        value: 'code',
        markers: [{ row: 0, className: 'old-marker' }]
      })
      wrapper = result.wrapper

      await wrapper.setProps({
        markers: [{ row: 1, className: 'new-marker' }]
      })
      await nextTick()

      expect(result.mockEditor.session.addMarker).toHaveBeenCalled()
      expect(mockRange).toHaveBeenCalledWith(1, 0, 1, 1)
    })

    it('should not call resize when only markers change (no value change)', async () => {
      const result = await mountAndInit({ value: 'code' })
      wrapper = result.wrapper

      await wrapper.setProps({
        markers: [{ row: 0, className: 'highlight' }]
      })
      await nextTick()

      expect(result.mockEditor.resize).not.toHaveBeenCalled()
    })

    it('should apply markers before resize on value change', async () => {
      const markers = [{ row: 0, className: 'step' }]
      const result = await mountAndInit({ value: 'before', markers })
      wrapper = result.wrapper
      const callOrder: string[] = []
      result.mockEditor.setValue.mockImplementation((val: string) => {
        callOrder.push('setValue')
        result.mockEditor.getValue.mockReturnValue(val)
      })
      result.mockEditor.session.addMarker.mockImplementation(() => {
        callOrder.push('addMarker')
        return 1
      })
      result.mockEditor.resize.mockImplementation(() => {
        callOrder.push('resize')
      })

      await wrapper.setProps({ value: 'after' })
      await nextTick()

      expect(callOrder).toEqual(['setValue', 'addMarker', 'resize'])
    })
  })

  describe('Auto-height (minLines / extraLines)', () => {
    it('should update minLines when content exceeds minLines and extraLines is set', async () => {
      const multiLineCode = 'line1\nline2\nline3\nline4\nline5\nline6'  // 6 lines
      const result = await mountAndInit({
        value: 'short',
        minLines: 5,
        extraLines: 2
      })
      wrapper = result.wrapper

      await wrapper.setProps({ value: multiLineCode })
      await nextTick()

      // 6 lines > minLines(5), so effectiveMinLines = 6 + 2 = 8
      expect(result.mockEditor.setOption).toHaveBeenCalledWith('minLines', 8)
    })

    it('should use base minLines when content does not exceed it', async () => {
      const result = await mountAndInit({
        value: 'short',
        minLines: 10,
        extraLines: 2
      })
      wrapper = result.wrapper

      await wrapper.setProps({ value: 'still\nshort' })  // 2 lines < 10
      await nextTick()

      expect(result.mockEditor.setOption).toHaveBeenCalledWith('minLines', 10)
    })

    it('should set minLines before resize(true) so both flush in one render pass', async () => {
      const multiLineCode = 'a\nb\nc\nd\ne\nf\ng'  // 7 lines
      const result = await mountAndInit({
        value: 'short',
        minLines: 5,
        extraLines: 2
      })
      wrapper = result.wrapper
      const callOrder: string[] = []
      result.mockEditor.setValue.mockImplementation((val: string) => {
        callOrder.push('setValue')
        result.mockEditor.getValue.mockReturnValue(val)
      })
      result.mockEditor.setOption.mockImplementation((name: string) => {
        callOrder.push(`setOption:${name}`)
      })
      result.mockEditor.resize.mockImplementation(() => {
        callOrder.push('resize')
      })

      await wrapper.setProps({ value: multiLineCode })
      await nextTick()

      expect(callOrder).toEqual(['setValue', 'setOption:minLines', 'resize'])
    })

    it('should not update minLines when extraLines is 0', async () => {
      const result = await mountAndInit({
        value: 'short',
        minLines: 5,
        extraLines: 0
      })
      wrapper = result.wrapper

      await wrapper.setProps({ value: 'a\nb\nc\nd\ne\nf\ng' })
      await nextTick()

      // setOption should not be called for minLines
      const minLinesCalls = result.mockEditor.setOption.mock.calls
        .filter(([name]: [string]) => name === 'minLines')
      expect(minLinesCalls).toHaveLength(0)
    })

    it('should omit height key from style when minLines is set (prevent Vue patchStyle from clearing ACE autosize height)', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor, {
        props: { minLines: 10, maxLines: 35, width: '100%' }
      })

      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      const style = aceEditor.props().style as Record<string, unknown>
      // Key must be ABSENT, not just undefined — Vue's patchStyle clears
      // el.style.height to "" for any key with a null/undefined value
      expect(style).not.toHaveProperty('height')
      expect(style.width).toBe('100%')
    })
  })

  describe('Size and Layout', () => {
    it('should apply fixed dimensions when minLines/maxLines not set', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor, {
        props: {
          height: '600px',
          width: '1000px'
        }
      })

      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      expect(aceEditor.props().style).toEqual({
        height: '600px',
        width: '1000px'
      })
    })

    it('should toggle gutter visibility', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor, {
        props: { showGutter: false }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      const mockEditor = createMockEditor()

      await aceEditor.vm.$emit('init', mockEditor)

      expect(mockEditor.setOptions).toHaveBeenCalledWith(
        expect.objectContaining({ showGutter: false })
      )
    })

    it('should set character limit as maxLines', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor, {
        props: { characterLimit: 1000 }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      const mockEditor = createMockEditor()

      await aceEditor.vm.$emit('init', mockEditor)

      expect(mockEditor.setOptions).toHaveBeenCalledWith(
        expect.objectContaining({ maxLines: 1000 })
      )
    })
  })

  describe('Theme Changes', () => {
    it('should pass theme changes to VAceEditor', async () => {
      const Editor = (await import('../Editor.vue')).default
      wrapper = mount(Editor, {
        props: { theme: 'monokai' }
      })

      await wrapper.setProps({ theme: 'dracula' })

      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      expect(aceEditor.props().theme).toBe('dracula')
    })
  })
})
