import { beforeEach, describe, expect, it } from 'vitest'
import { useMcqOptions, type McqOption } from '../useMcqOptions'

describe('useMcqOptions', () => {
  let mcq: ReturnType<typeof useMcqOptions>

  beforeEach(() => {
    mcq = useMcqOptions()
  })

  describe('initial state', () => {
    it('should initialize with one empty option', () => {
      expect(mcq.options.value).toHaveLength(1)
      expect(mcq.options.value[0].text).toBe('')
      expect(mcq.options.value[0].is_correct).toBe(false)
    })

    it('should initialize with empty question text', () => {
      expect(mcq.questionText.value).toBe('')
    })

    it('should allow adding more options initially', () => {
      expect(mcq.canAddMore.value).toBe(true)
    })

    it('should not allow removing below minimum initially', () => {
      expect(mcq.canRemove.value).toBe(false)
    })
  })

  describe('setOptions', () => {
    it('should load options from API response', () => {
      const apiOptions: McqOption[] = [
        { id: '1', text: 'Option A', is_correct: true, explanation: 'Correct!' },
        { id: '2', text: 'Option B', is_correct: false, explanation: '' },
        { id: '3', text: 'Option C', is_correct: false, explanation: '' },
      ]

      mcq.setOptions(apiOptions)

      expect(mcq.options.value).toHaveLength(3)
      expect(mcq.options.value[0].text).toBe('Option A')
      expect(mcq.options.value[0].is_correct).toBe(true)
      expect(mcq.hasCorrectAnswer.value).toBe(true)
    })

    it('should create default option when given empty array', () => {
      mcq.setOptions([])

      expect(mcq.options.value).toHaveLength(1)
      expect(mcq.options.value[0].text).toBe('')
    })
  })

  describe('setQuestionText', () => {
    it('should set question text on load', () => {
      mcq.setQuestionText('What is 2 + 2?')

      expect(mcq.questionText.value).toBe('What is 2 + 2?')
    })
  })

  describe('getOptionsForApi', () => {
    it('should filter empty options in getOptionsForApi()', () => {
      const apiOptions: McqOption[] = [
        { id: '1', text: 'Option A', is_correct: true, explanation: '' },
        { id: '2', text: '', is_correct: false, explanation: '' }, // Empty
        { id: '3', text: '   ', is_correct: false, explanation: '' }, // Whitespace
        { id: '4', text: 'Option B', is_correct: false, explanation: '' },
      ]

      mcq.setOptions(apiOptions)
      const forApi = mcq.getOptionsForApi()

      expect(forApi).toHaveLength(2)
      expect(forApi[0].text).toBe('Option A')
      expect(forApi[1].text).toBe('Option B')
    })
  })

  describe('setCorrect', () => {
    it('should ensure only one correct answer', () => {
      const apiOptions: McqOption[] = [
        { id: '1', text: 'Option A', is_correct: true, explanation: '' },
        { id: '2', text: 'Option B', is_correct: false, explanation: '' },
        { id: '3', text: 'Option C', is_correct: false, explanation: '' },
      ]

      mcq.setOptions(apiOptions)
      expect(mcq.options.value[0].is_correct).toBe(true)
      expect(mcq.options.value[1].is_correct).toBe(false)

      // Change correct answer to second option
      mcq.setCorrect(1)

      expect(mcq.options.value[0].is_correct).toBe(false)
      expect(mcq.options.value[1].is_correct).toBe(true)
      expect(mcq.options.value[2].is_correct).toBe(false)
      expect(mcq.hasCorrectAnswer.value).toBe(true)
    })
  })

  describe('option limits', () => {
    it('should prevent removing below minimum (2 options)', () => {
      const apiOptions: McqOption[] = [
        { id: '1', text: 'A', is_correct: true, explanation: '' },
        { id: '2', text: 'B', is_correct: false, explanation: '' },
      ]

      mcq.setOptions(apiOptions)
      expect(mcq.options.value).toHaveLength(2)
      expect(mcq.canRemove.value).toBe(false)

      // Try to remove - should be blocked
      mcq.removeOption(0)
      expect(mcq.options.value).toHaveLength(2)
    })

    it('should allow removing when above minimum', () => {
      const apiOptions: McqOption[] = [
        { id: '1', text: 'A', is_correct: true, explanation: '' },
        { id: '2', text: 'B', is_correct: false, explanation: '' },
        { id: '3', text: 'C', is_correct: false, explanation: '' },
      ]

      mcq.setOptions(apiOptions)
      expect(mcq.canRemove.value).toBe(true)

      mcq.removeOption(2)
      expect(mcq.options.value).toHaveLength(2)
    })

    it('should prevent adding above maximum (6 options)', () => {
      const apiOptions: McqOption[] = [
        { id: '1', text: 'A', is_correct: true, explanation: '' },
        { id: '2', text: 'B', is_correct: false, explanation: '' },
        { id: '3', text: 'C', is_correct: false, explanation: '' },
        { id: '4', text: 'D', is_correct: false, explanation: '' },
        { id: '5', text: 'E', is_correct: false, explanation: '' },
        { id: '6', text: 'F', is_correct: false, explanation: '' },
      ]

      mcq.setOptions(apiOptions)
      expect(mcq.options.value).toHaveLength(6)
      expect(mcq.canAddMore.value).toBe(false)

      // Try to add - should be blocked
      mcq.addOption()
      expect(mcq.options.value).toHaveLength(6)
    })
  })

  describe('reset', () => {
    it('should reset to initial state', () => {
      const apiOptions: McqOption[] = [
        { id: '1', text: 'Option A', is_correct: true, explanation: '' },
        { id: '2', text: 'Option B', is_correct: false, explanation: '' },
      ]

      mcq.setOptions(apiOptions)
      mcq.setQuestionText('Test question')

      mcq.reset()

      expect(mcq.options.value).toHaveLength(1)
      expect(mcq.options.value[0].text).toBe('')
      expect(mcq.questionText.value).toBe('')
      expect(mcq.hasCorrectAnswer.value).toBe(false)
    })
  })
})
