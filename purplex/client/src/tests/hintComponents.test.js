import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import HintButton from '../components/hints/HintButton.vue'
import HintModal from '../components/hints/HintModal.vue'
import VariableFadeHint from '../components/hints/VariableFadeHint.vue'
import SubgoalHighlight from '../components/hints/SubgoalHighlight.vue'
import SuggestedTrace from '../components/hints/SuggestedTrace.vue'

describe('HintButton Component', () => {
  const defaultProps = {
    problemSlug: 'test-problem',
    problemSetSlug: 'test-set',
    courseId: 'TEST101',
    attempts: 0,
    requiredAttempts: 3
  }

  it('should render disabled when attempts < required attempts', () => {
    const wrapper = mount(HintButton, {
      props: { ...defaultProps, attempts: 2 }
    })

    expect(wrapper.find('.hint-button').classes()).toContain('disabled')
    expect(wrapper.find('.hint-button').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Need 1 more attempt')
  })

  it('should render enabled when attempts >= required attempts', () => {
    const wrapper = mount(HintButton, {
      props: { ...defaultProps, attempts: 3 }
    })

    expect(wrapper.find('.hint-button').classes()).not.toContain('disabled')
    expect(wrapper.find('.hint-button').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('Get Hint')
  })

  it('should emit hint-requested event when clicked and enabled', async () => {
    const wrapper = mount(HintButton, {
      props: { ...defaultProps, attempts: 5 }
    })

    await wrapper.find('.hint-button').trigger('click')

    expect(wrapper.emitted('hint-requested')).toBeTruthy()
    expect(wrapper.emitted('hint-requested')[0][0]).toEqual({
      problemSlug: 'test-problem',
      problemSetSlug: 'test-set',
      courseId: 'TEST101',
      attempts: 5
    })
  })

  it('should not emit event when clicked and disabled', async () => {
    const wrapper = mount(HintButton, {
      props: { ...defaultProps, attempts: 1 }
    })

    await wrapper.find('.hint-button').trigger('click')

    expect(wrapper.emitted('hint-requested')).toBeFalsy()
  })

  it('should handle singular vs plural attempts correctly', () => {
    const wrapperSingular = mount(HintButton, {
      props: { ...defaultProps, attempts: 2, requiredAttempts: 3 }
    })
    expect(wrapperSingular.text()).toContain('Need 1 more attempt')

    const wrapperPlural = mount(HintButton, {
      props: { ...defaultProps, attempts: 1, requiredAttempts: 3 }
    })
    expect(wrapperPlural.text()).toContain('Need 2 more attempts')
  })

  it('should update tooltip text based on state', () => {
    const wrapperDisabled = mount(HintButton, {
      props: { ...defaultProps, attempts: 1 }
    })
    expect(wrapperDisabled.find('.hint-button').attributes('title'))
      .toContain('You need to make 2 more attempts')

    const wrapperEnabled = mount(HintButton, {
      props: { ...defaultProps, attempts: 3 }
    })
    expect(wrapperEnabled.find('.hint-button').attributes('title'))
      .toBe('Click to request a hint')
  })
})

describe('HintModal Component', () => {
  const defaultProps = {
    visible: true,
    availableHintTypes: ['variable_fade', 'subgoal_highlight', 'suggested_trace']
  }

  it('should render all available hint types', () => {
    const wrapper = mount(HintModal, {
      props: defaultProps
    })

    const hintOptions = wrapper.findAll('.hint-option')
    expect(hintOptions).toHaveLength(3)
    
    expect(wrapper.text()).toContain('Variable Name Hints')
    expect(wrapper.text()).toContain('Code Structure Hints')
    expect(wrapper.text()).toContain('Suggested Trace')
  })

  it('should filter hint types based on availableHintTypes prop', () => {
    const wrapper = mount(HintModal, {
      props: {
        ...defaultProps,
        availableHintTypes: ['variable_fade']
      }
    })

    const hintOptions = wrapper.findAll('.hint-option')
    expect(hintOptions).toHaveLength(1)
    expect(wrapper.text()).toContain('Variable Name Hints')
    expect(wrapper.text()).not.toContain('Code Structure Hints')
  })

  it('should not render when visible is false', () => {
    const wrapper = mount(HintModal, {
      props: {
        ...defaultProps,
        visible: false
      }
    })

    expect(wrapper.find('.modal-overlay').exists()).toBe(false)
  })

  it('should emit close event when overlay is clicked', async () => {
    const wrapper = mount(HintModal, {
      props: defaultProps
    })

    await wrapper.find('.modal-overlay').trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('should emit close event when close button is clicked', async () => {
    const wrapper = mount(HintModal, {
      props: defaultProps
    })

    await wrapper.find('.close-button').trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('should not emit close when modal container is clicked', async () => {
    const wrapper = mount(HintModal, {
      props: defaultProps
    })

    await wrapper.find('.modal-container').trigger('click')

    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('should emit hint-selected event when hint option is clicked', async () => {
    const wrapper = mount(HintModal, {
      props: defaultProps
    })

    await wrapper.find('.hint-option').trigger('click')

    expect(wrapper.emitted('hint-selected')).toBeTruthy()
    expect(wrapper.emitted('hint-selected')[0][0]).toBe('variable_fade')
    expect(wrapper.emitted('close')).toBeTruthy()
  })
})

describe('VariableFadeHint Component', () => {
  const defaultProps = {
    code: 'def func(x, y):\n    result = x + y\n    return result',
    mappings: [
      { from: 'x', to: 'first_number' },
      { from: 'y', to: 'second_number' },
      { from: 'result', to: 'sum' }
    ]
  }

  it('should render original code by default', () => {
    const wrapper = mount(VariableFadeHint, {
      props: defaultProps
    })

    expect(wrapper.find('.code-display').text()).toContain('x')
    expect(wrapper.find('.code-display').text()).toContain('y')
    expect(wrapper.find('.code-display').text()).toContain('result')
    expect(wrapper.text()).toContain('Show Meaningful Names')
  })

  it('should toggle to meaningful variable names when button is clicked', async () => {
    const wrapper = mount(VariableFadeHint, {
      props: defaultProps
    })

    await wrapper.find('.toggle-button').trigger('click')

    expect(wrapper.find('.code-display').text()).toContain('first_number')
    expect(wrapper.find('.code-display').text()).toContain('second_number')
    expect(wrapper.find('.code-display').text()).toContain('sum')
    expect(wrapper.text()).toContain('Show Original Names')
  })

  it('should show mappings legend when showing meaningful names', async () => {
    const wrapper = mount(VariableFadeHint, {
      props: defaultProps
    })

    // Initially no legend
    expect(wrapper.find('.mappings-legend').exists()).toBe(false)

    await wrapper.find('.toggle-button').trigger('click')

    // After toggle, legend should appear
    expect(wrapper.find('.mappings-legend').exists()).toBe(true)
    expect(wrapper.text()).toContain('Variable Mappings:')
    expect(wrapper.text()).toContain('x → first_number')
    expect(wrapper.text()).toContain('y → second_number')
  })

  it('should handle empty mappings gracefully', () => {
    const wrapper = mount(VariableFadeHint, {
      props: {
        code: 'def test(): pass',
        mappings: []
      }
    })

    expect(wrapper.find('.code-display').text()).toContain('def test(): pass')
    
    // Should still render toggle button
    expect(wrapper.find('.toggle-button').exists()).toBe(true)
  })

  it('should preserve word boundaries when replacing variables', async () => {
    const wrapper = mount(VariableFadeHint, {
      props: {
        code: 'x = 1\nmax_x = 2\nx_value = 3',
        mappings: [{ from: 'x', to: 'count' }]
      }
    })

    await wrapper.find('.toggle-button').trigger('click')

    const codeText = wrapper.find('.code-display').text()
    expect(codeText).toContain('count = 1')
    expect(codeText).toContain('max_x = 2') // Should not be changed
    expect(codeText).toContain('x_value = 3') // Should not be changed
  })

  it('should sort mappings by length to avoid partial replacements', async () => {
    const wrapper = mount(VariableFadeHint, {
      props: {
        code: 'x = 1\nxx = 2',
        mappings: [
          { from: 'x', to: 'short' },
          { from: 'xx', to: 'longer' }
        ]
      }
    })

    await wrapper.find('.toggle-button').trigger('click')

    const codeText = wrapper.find('.code-display').text()
    expect(codeText).toContain('longer = 2')
    expect(codeText).toContain('short = 1')
  })

  it('should update description text based on toggle state', async () => {
    const wrapper = mount(VariableFadeHint, {
      props: defaultProps
    })

    expect(wrapper.text()).toContain('Click the button above to see')

    await wrapper.find('.toggle-button').trigger('click')

    expect(wrapper.text()).toContain('Variable names have been replaced')
  })

  it('should apply correct CSS classes to toggle button', async () => {
    const wrapper = mount(VariableFadeHint, {
      props: defaultProps
    })

    expect(wrapper.find('.toggle-button').classes()).not.toContain('active')

    await wrapper.find('.toggle-button').trigger('click')

    expect(wrapper.find('.toggle-button').classes()).toContain('active')
  })
})

describe('SubgoalHighlight Component', () => {
  const defaultProps = {
    code: 'def func():\n    x = 1\n    y = 2\n    return x + y',
    subgoals: [
      {
        id: '1',
        title: 'Initialize variables',
        explanation: 'Set up x and y',
        lineRanges: [{ start: 2, end: 3 }]
      },
      {
        id: '2',
        title: 'Return sum',
        explanation: 'Calculate and return result',
        lineRanges: [{ start: 4, end: 4 }]
      }
    ]
  }

  it('should render with first subgoal selected by default', () => {
    const wrapper = mount(SubgoalHighlight, {
      props: defaultProps
    })

    expect(wrapper.find('.subgoal-title').text()).toBe('Initialize variables')
    expect(wrapper.find('.subgoal-explanation').text()).toBe('Set up x and y')
    expect(wrapper.find('.nav-indicator').text()).toBe('1 / 2')
  })

  it('should navigate between subgoals', async () => {
    const wrapper = mount(SubgoalHighlight, {
      props: defaultProps
    })

    // Initially on first subgoal
    expect(wrapper.find('.subgoal-title').text()).toBe('Initialize variables')

    // Click next button
    await wrapper.findAll('.nav-button')[1].trigger('click')

    // Should be on second subgoal
    expect(wrapper.find('.subgoal-title').text()).toBe('Return sum')
    expect(wrapper.find('.nav-indicator').text()).toBe('2 / 2')
  })

  it('should disable navigation buttons appropriately', async () => {
    const wrapper = mount(SubgoalHighlight, {
      props: defaultProps
    })

    const navButtons = wrapper.findAll('.nav-button')
    
    // Previous button should be disabled on first subgoal
    expect(navButtons[0].attributes('disabled')).toBeDefined()
    expect(navButtons[1].attributes('disabled')).toBeUndefined()

    // Navigate to last subgoal
    await navButtons[1].trigger('click')

    // Next button should be disabled on last subgoal
    expect(navButtons[0].attributes('disabled')).toBeUndefined()
    expect(navButtons[1].attributes('disabled')).toBeDefined()
  })

  it('should allow direct subgoal selection from list', async () => {
    const wrapper = mount(SubgoalHighlight, {
      props: defaultProps
    })

    // Click on second subgoal in list
    await wrapper.findAll('.subgoal-item')[1].trigger('click')

    expect(wrapper.find('.subgoal-title').text()).toBe('Return sum')
    expect(wrapper.findAll('.subgoal-item')[1].classes()).toContain('active')
  })

  it('should highlight correct lines based on current subgoal', () => {
    const wrapper = mount(SubgoalHighlight, {
      props: defaultProps
    })

    // Check that highlighting is applied (through v-html)
    const codeDisplay = wrapper.find('.code-display')
    expect(codeDisplay.html()).toContain('highlighted-line')
    expect(codeDisplay.html()).toContain('normal-line')
  })

  it('should escape HTML in code content', () => {
    const wrapper = mount(SubgoalHighlight, {
      props: {
        ...defaultProps,
        code: 'if x < y:\n    return "test & example"'
      }
    })

    const codeDisplay = wrapper.find('.code-display')
    expect(codeDisplay.html()).toContain('&lt;')
    expect(codeDisplay.html()).toContain('&amp;')
    expect(codeDisplay.html()).toContain('&quot;')
  })

  it('should handle empty subgoals list', () => {
    const wrapper = mount(SubgoalHighlight, {
      props: {
        code: 'def test(): pass',
        subgoals: []
      }
    })

    expect(wrapper.find('.nav-indicator').text()).toBe('1 / 0')
    expect(wrapper.findAll('.nav-button')).toHaveLength(2)
    expect(wrapper.findAll('.nav-button')[0].attributes('disabled')).toBeDefined()
    expect(wrapper.findAll('.nav-button')[1].attributes('disabled')).toBeDefined()
  })

  it('should update subgoal item active state correctly', async () => {
    const wrapper = mount(SubgoalHighlight, {
      props: defaultProps
    })

    // First item should be active initially
    expect(wrapper.findAll('.subgoal-item')[0].classes()).toContain('active')
    expect(wrapper.findAll('.subgoal-item')[1].classes()).not.toContain('active')

    // Navigate to next
    await wrapper.findAll('.nav-button')[1].trigger('click')

    // Second item should be active now
    expect(wrapper.findAll('.subgoal-item')[0].classes()).not.toContain('active')
    expect(wrapper.findAll('.subgoal-item')[1].classes()).toContain('active')
  })
})

describe('SuggestedTrace Component', () => {
  const defaultProps = {
    hintData: {
      content: {
        suggested_call: 'test_function(5, 10)',
        explanation: 'Try tracing this function call'
      }
    },
    solutionCode: 'def test_function(a, b):\n    return a + b',
    isVisible: true
  }

  // Mock PythonTutorService
  const mockPythonTutorService = {
    generateEmbedUrl: vi.fn().mockReturnValue('https://pythontutor.com/embed/url')
  }

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks()
  })

  it('should render when visible', () => {
    const wrapper = mount(SuggestedTrace, {
      props: defaultProps,
      global: {
        mocks: {
          PythonTutorService: mockPythonTutorService
        }
      }
    })

    expect(wrapper.find('.suggested-trace').exists()).toBe(true)
    expect(wrapper.text()).toContain('Try tracing:')
    expect(wrapper.text()).toContain('test_function(5, 10)')
  })

  it('should not render when not visible', () => {
    const wrapper = mount(SuggestedTrace, {
      props: {
        ...defaultProps,
        isVisible: false
      }
    })

    expect(wrapper.find('.suggested-trace').exists()).toBe(false)
  })

  it('should display fallback text when no suggestion available', () => {
    const wrapper = mount(SuggestedTrace, {
      props: {
        ...defaultProps,
        hintData: {}
      }
    })

    expect(wrapper.text()).toContain('No suggestion available')
  })

  it('should enable trace button when all required data is present', () => {
    const wrapper = mount(SuggestedTrace, {
      props: defaultProps
    })

    const traceButton = wrapper.find('.trace-btn')
    expect(traceButton.attributes('disabled')).toBeUndefined()
  })

  it('should disable trace button when required data is missing', () => {
    const wrapper = mount(SuggestedTrace, {
      props: {
        ...defaultProps,
        solutionCode: ''
      }
    })

    const traceButton = wrapper.find('.trace-btn')
    expect(traceButton.attributes('disabled')).toBeDefined()
  })

  it('should disable trace button when suggestion is not available', () => {
    const wrapper = mount(SuggestedTrace, {
      props: {
        ...defaultProps,
        hintData: {
          content: {
            suggested_call: 'No suggestion available'
          }
        }
      }
    })

    const traceButton = wrapper.find('.trace-btn')
    expect(traceButton.attributes('disabled')).toBeDefined()
  })

  it('should emit open-pytutor event when trace button is clicked', async () => {
    const wrapper = mount(SuggestedTrace, {
      props: defaultProps,
      global: {
        mocks: {
          PythonTutorService: mockPythonTutorService
        }
      }
    })

    await wrapper.find('.trace-btn').trigger('click')

    expect(wrapper.emitted('open-pytutor')).toBeTruthy()
    expect(wrapper.emitted('open-pytutor')[0][0]).toBe('https://pythontutor.com/embed/url')
  })

  it('should not emit event when trace button is disabled and clicked', async () => {
    const wrapper = mount(SuggestedTrace, {
      props: {
        ...defaultProps,
        solutionCode: ''
      }
    })

    await wrapper.find('.trace-btn').trigger('click')

    expect(wrapper.emitted('open-pytutor')).toBeFalsy()
  })

  it('should format code correctly for Python Tutor', async () => {
    const wrapper = mount(SuggestedTrace, {
      props: defaultProps,
      global: {
        mocks: {
          PythonTutorService: mockPythonTutorService
        }
      }
    })

    await wrapper.find('.trace-btn').trigger('click')

    expect(mockPythonTutorService.generateEmbedUrl).toHaveBeenCalledWith(
      expect.stringContaining('def test_function(a, b):')
    )
    expect(mockPythonTutorService.generateEmbedUrl).toHaveBeenCalledWith(
      expect.stringContaining('print(test_function(5, 10))')
    )
  })

  it('should handle missing content gracefully', () => {
    const wrapper = mount(SuggestedTrace, {
      props: {
        ...defaultProps,
        hintData: null
      }
    })

    expect(wrapper.text()).toContain('No suggestion available')
    expect(wrapper.find('.trace-btn').attributes('disabled')).toBeDefined()
  })

  it('should handle deeply nested missing content', () => {
    const wrapper = mount(SuggestedTrace, {
      props: {
        ...defaultProps,
        hintData: {
          content: null
        }
      }
    })

    expect(wrapper.text()).toContain('No suggestion available')
  })

  it('should apply correct CSS classes based on state', () => {
    const enabledWrapper = mount(SuggestedTrace, {
      props: defaultProps
    })

    const disabledWrapper = mount(SuggestedTrace, {
      props: {
        ...defaultProps,
        solutionCode: ''
      }
    })

    expect(enabledWrapper.find('.trace-btn').classes()).not.toContain('disabled')
    expect(disabledWrapper.find('.trace-btn').attributes('disabled')).toBeDefined()
  })
})