import { afterEach, beforeEach, describe, expect, it, Mock, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import Editor from '../Editor.vue'
import { nextTick } from 'vue'
import { log } from '@/utils/logger'

// Mock dependencies
vi.mock('@/utils/logger', () => ({
  log: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn()
  }
}))

// Mock VAceEditor component
vi.mock('vue3-ace-editor', () => ({
  VAceEditor: {
    name: 'VAceEditor',
    props: ['lang', 'theme', 'mode', 'style', 'value', 'options'],
    emits: ['init', 'update:value'],
    template: '<div class="mock-ace-editor"></div>'
  }
}))

// Mock ace-builds
vi.mock('ace-builds/src-noconflict/worker-json?url', () => ({
  default: 'mocked-worker-url'
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

// Mock ace global
const mockRange = vi.fn().mockImplementation((startLine, startCol, endLine, endCol) => ({
  startLine,
  startColumn: startCol,
  endLine,
  endColumn: endCol
}))

// @ts-ignore
global.ace = {
  require: vi.fn((module) => {
    if (module === 'ace/range') {
      return { Range: mockRange }
    }
    return {}
  })
}

// Mock editor instance
const createMockEditor = () => ({
  setOptions: vi.fn(),
  setOption: vi.fn(),
  getValue: vi.fn().mockReturnValue('test code'),
  setValue: vi.fn(),
  setTheme: vi.fn(),
  setMode: vi.fn(),
  resize: vi.fn(),
  clearSelection: vi.fn(),
  container: {
    setAttribute: vi.fn(),
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
  moveCursorToPosition: vi.fn()
})

describe('Editor Component', () => {
  let wrapper: VueWrapper<any>
  let mockEditor: ReturnType<typeof createMockEditor>

  beforeEach(() => {
    mockEditor = createMockEditor()
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Component Initialization', () => {
    it('should mount with default props', () => {
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
        tabTargetId: null
      })
    })

    it('should mount with custom props', () => {
      wrapper = mount(Editor, {
        props: {
          lang: 'javascript',
          theme: 'monokai',
          height: '500px',
          width: '800px',
          value: 'const x = 42;',
          readOnly: true
        }
      })

      expect(wrapper.props().lang).toBe('javascript')
      expect(wrapper.props().theme).toBe('monokai')
      expect(wrapper.props().height).toBe('500px')
      expect(wrapper.props().width).toBe('800px')
      expect(wrapper.props().value).toBe('const x = 42;')
      expect(wrapper.props().readOnly).toBe(true)
    })

    it('should render VAceEditor with correct props', () => {
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
    it('should initialize editor instance on init event', async () => {
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })

      // Trigger init event
      await aceEditor.vm.$emit('init', mockEditor)

      expect(mockEditor.setOptions).toHaveBeenCalledWith({
        showGutter: true,
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
      wrapper = mount(Editor, {
        props: { readOnly: true }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })

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
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })

      await aceEditor.vm.$emit('update:value', 'new code')

      expect(wrapper.emitted('update:value')).toBeTruthy()
      expect(wrapper.emitted('update:value')?.[0]).toEqual(['new code'])
    })

  })

  describe('Theme Changes', () => {
    it('should pass theme changes to ace editor', async () => {
      wrapper = mount(Editor, {
        props: { theme: 'monokai' }
      })

      await wrapper.setProps({ theme: 'dracula' })

      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      expect(aceEditor.props().theme).toBe('dracula')
    })
  })

  describe('Size and Layout', () => {
    it('should apply custom dimensions', () => {
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
      wrapper = mount(Editor, {
        props: { showGutter: false }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })

      await aceEditor.vm.$emit('init', mockEditor)

      expect(mockEditor.setOptions).toHaveBeenCalledWith(
        expect.objectContaining({ showGutter: false })
      )
    })

    it('should set character limit', async () => {
      wrapper = mount(Editor, {
        props: { characterLimit: 1000 }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })

      await aceEditor.vm.$emit('init', mockEditor)

      expect(mockEditor.setOptions).toHaveBeenCalledWith(
        expect.objectContaining({ maxLines: 1000 })
      )
    })
  })
})
