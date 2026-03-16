import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import McqDetail from '../McqDetail.vue'
import RefuteDetail from '../RefuteDetail.vue'
import en from '@/i18n/locales/en'

const detail = en.admin.submissions.detail

describe('McqDetail i18n rendering', () => {
  const baseProps = {
    typeData: {
      question_text: 'What is 2+2?',
      options: [
        { id: 'a', text: 'Three', is_correct: false },
        { id: 'b', text: 'Four', is_correct: true, explanation: 'Basic arithmetic' },
      ],
      selected_option_id: 'b',
      correct_option: { id: 'b', text: 'Four', is_correct: true },
      is_correct: true,
    },
  }

  it('renders "Correct Answer" from locale when is_correct is true', () => {
    const wrapper = mount(McqDetail, { props: baseProps })
    expect(wrapper.find('.result-banner').text()).toBe(detail.correctAnswer)
  })

  it('renders "Incorrect Answer" from locale when is_correct is false', () => {
    const wrapper = mount(McqDetail, {
      props: {
        typeData: { ...baseProps.typeData, is_correct: false, selected_option_id: 'a' },
      },
    })
    expect(wrapper.find('.result-banner').text()).toBe(detail.incorrectAnswer)
  })

  it('renders section labels from locale keys', () => {
    const wrapper = mount(McqDetail, { props: baseProps })
    const labels = wrapper.findAll('.section-label').map(el => el.text())
    expect(labels).toContain(detail.question)
    expect(labels).toContain(detail.options)
  })
})

describe('RefuteDetail i18n rendering', () => {
  const baseProps = {
    typeData: {
      claim_text: 'All primes are odd',
      function_signature: 'is_prime(n: int) -> bool',
      function_name: 'is_prime',
    },
    submission: {
      raw_input: '2',
      is_correct: true,
    },
  }

  it('renders "Valid counterexample found" from locale when is_correct is true', () => {
    const wrapper = mount(RefuteDetail, { props: baseProps })
    expect(wrapper.find('.result-banner').text()).toBe(detail.validCounterexample)
  })

  it('renders "Counterexample not valid" from locale when is_correct is false', () => {
    const wrapper = mount(RefuteDetail, {
      props: {
        ...baseProps,
        submission: { raw_input: '3', is_correct: false },
      },
    })
    expect(wrapper.find('.result-banner').text()).toBe(detail.counterexampleNotValid)
  })

  it('renders section labels from locale keys', () => {
    const wrapper = mount(RefuteDetail, { props: baseProps })
    const labels = wrapper.findAll('.section-label').map(el => el.text())
    expect(labels).toContain(detail.claimToDisprove)
    expect(labels).toContain(detail.functionSignature)
    expect(labels).toContain(detail.studentsCounterexampleInput)
  })
})
