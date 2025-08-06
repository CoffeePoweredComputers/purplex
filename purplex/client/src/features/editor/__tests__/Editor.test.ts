import { describe, it, expect, vi, beforeEach, afterEach, Mock } from 'vitest'
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
        theme: 'clouds_midnight',
        mode: 'python',
        height: '300px',
        width: '500px',
        showGutter: true,
        characterLimit: null,
        hintMarkers: [],
        value: '',
        readOnly: false
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
        maxLines: null,
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

    it('should set proper z-index for marker layer', async () => {
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      await aceEditor.vm.$emit('init', mockEditor)
      
      expect(mockEditor.renderer.$markerBack.element.style.zIndex).toBe('3')
    })

    it('should customize comment token rendering', async () => {
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      await aceEditor.vm.$emit('init', mockEditor)
      
      const tokenizer = mockEditor.session.getMode().getTokenizer()
      const result = tokenizer.getLineTokens('# comment', 'start')
      
      expect(result.tokens[0].type).toContain('ace-comment-transparent')
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

    it('should handle non-string values with error', async () => {
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      // @ts-ignore - testing error case
      await aceEditor.vm.$emit('update:value', { invalid: 'object' })
      
      expect(log.error).toHaveBeenCalledWith(
        'ACE editor sent non-string value',
        expect.objectContaining({
          value: { invalid: 'object' },
          type: 'object'
        })
      )
      expect(wrapper.emitted('update:value')).toBeFalsy()
    })

    it('should update editor value via exposed method', async () => {
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      await aceEditor.vm.$emit('init', mockEditor)
      
      // Call exposed setValue method
      wrapper.vm.setValue('updated code')
      
      expect(mockEditor.setOptions).toHaveBeenCalledWith({
        value: 'updated code'
      })
    })

    it('should get editor value via exposed method', async () => {
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      await aceEditor.vm.$emit('init', mockEditor)
      mockEditor.getValue.mockReturnValue('current code')
      
      const value = wrapper.vm.getValue()
      
      expect(value).toBe('current code')
    })

    it('should return empty string when editor not initialized', () => {
      wrapper = mount(Editor)
      
      const value = wrapper.vm.getValue()
      
      expect(value).toBe('')
    })
  })

  describe('Hint Markers', () => {
    const mockMarkers = [
      {
        startLine: 0,
        endLine: 0,
        className: 'hint-highlight',
        type: 'fullLine',
        hintType: 'subgoal'
      },
      {
        startLine: 2,
        endLine: 2,
        startColumn: 4,
        endColumn: 10,
        className: 'variable-fade',
        type: 'text',
        hintType: 'variable_fade'
      }
    ]

    it('should set hint markers on initialization', async () => {
      wrapper = mount(Editor, {
        props: { hintMarkers: mockMarkers }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      await aceEditor.vm.$emit('init', mockEditor)
      
      expect(mockEditor.session.addMarker).toHaveBeenCalledTimes(2)
      expect(mockRange).toHaveBeenCalledWith(0, 0, 0, Number.MAX_SAFE_INTEGER)
      expect(mockRange).toHaveBeenCalledWith(2, 4, 2, 10)
    })

    it('should update markers when prop changes', async () => {
      wrapper = mount(Editor)
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      await aceEditor.vm.$emit('init', mockEditor)
      
      // Add markers
      await wrapper.setProps({ hintMarkers: mockMarkers })
      await nextTick()
      
      expect(mockEditor.session.addMarker).toHaveBeenCalledTimes(2)
    })

    it('should clear existing markers before setting new ones', async () => {
      wrapper = mount(Editor, {
        props: { hintMarkers: [mockMarkers[0]] }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      await aceEditor.vm.$emit('init', mockEditor)
      mockEditor.session.addMarker.mockReturnValue(1)
      
      // Update markers
      await wrapper.setProps({ hintMarkers: [mockMarkers[1]] })
      await nextTick()
      
      expect(mockEditor.session.removeMarker).toHaveBeenCalledWith(1)
      expect(log.debug).toHaveBeenCalledWith('Cleared all hint markers')
    })

    it('should handle empty markers array', async () => {
      wrapper = mount(Editor, {
        props: { hintMarkers: mockMarkers }
      })
      const aceEditor = wrapper.findComponent({ name: 'VAceEditor' })
      
      await aceEditor.vm.$emit('init', mockEditor)
      
      // Clear markers
      await wrapper.setProps({ hintMarkers: [] })
      await nextTick()
      
      expect(mockEditor.session.removeMarker).toHaveBeenCalled()
      expect(log.debug).toHaveBeenCalledWith('setHintMarkers called with', { markers: [] })
    })

    it('should not set markers if editor not initialized', async () => {
      wrapper = mount(Editor, {
        props: { hintMarkers: mockMarkers }
      })
      
      // Don't initialize editor
      wrapper.vm.setHintMarkers(mockMarkers)
      
      expect(log.debug).toHaveBeenCalledWith('setHintMarkers: Editor not available')
      expect(mockEditor.session.addMarker).not.toHaveBeenCalled()
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