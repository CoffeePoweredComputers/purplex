import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CourseTeamManager from '../CourseTeamManager.vue'
import type { CourseInstructorMember } from '@/types'

const mockTeam: CourseInstructorMember[] = [
  {
    user_id: 1,
    username: 'prof_smith',
    full_name: 'Prof Smith',
    email: 'smith@example.com',
    role: 'primary',
    added_at: '2026-01-01T00:00:00Z',
  },
  {
    user_id: 2,
    username: 'ta_jones',
    full_name: 'TA Jones',
    email: 'jones@example.com',
    role: 'ta',
    added_at: '2026-01-15T00:00:00Z',
  },
]

// Mock the content service
const mockGetCourseTeam = vi.fn().mockResolvedValue(mockTeam)
const mockAddCourseTeamMember = vi.fn()
const mockUpdateCourseTeamMember = vi.fn()
const mockRemoveCourseTeamMember = vi.fn()

vi.mock('@/services/contentService', () => ({
  createContentService: () => ({
    getCourseTeam: mockGetCourseTeam,
    addCourseTeamMember: mockAddCourseTeamMember,
    updateCourseTeamMember: mockUpdateCourseTeamMember,
    removeCourseTeamMember: mockRemoveCourseTeamMember,
  }),
}))

vi.mock('@/utils/logger', () => ({
  log: {
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    warn: vi.fn(),
  },
}))

function mountComponent(myRole: 'primary' | 'ta' = 'primary') {
  return mount(CourseTeamManager, {
    props: {
      courseId: 'CS101',
      myRole,
    },
  })
}

describe('CourseTeamManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetCourseTeam.mockResolvedValue([...mockTeam])
  })

  it('renders team member list', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(2)
    expect(wrapper.text()).toContain('Prof Smith')
    expect(wrapper.text()).toContain('TA Jones')
  })

  it('shows role badges', async () => {
    const wrapper = mountComponent()
    await flushPromises()

    const badges = wrapper.findAll('.role-badge')
    expect(badges.length).toBe(2)
    expect(badges[0].text()).toBe('Primary')
    expect(badges[1].text()).toBe('TA')
  })

  it('primary sees action buttons', async () => {
    const wrapper = mountComponent('primary')
    await flushPromises()

    expect(wrapper.findAll('.btn-remove').length).toBe(2)
    expect(wrapper.find('.add-member').exists()).toBe(true)
  })

  it('TA sees read-only view', async () => {
    const wrapper = mountComponent('ta')
    await flushPromises()

    expect(wrapper.findAll('.btn-remove').length).toBe(0)
    expect(wrapper.find('.add-member').exists()).toBe(false)
  })

  it('add member calls addCourseTeamMember', async () => {
    const newMember: CourseInstructorMember = {
      user_id: 3,
      username: 'new_ta',
      full_name: 'New TA',
      email: 'new@example.com',
      role: 'ta',
      added_at: '2026-03-01T00:00:00Z',
    }
    mockAddCourseTeamMember.mockResolvedValue(newMember)

    const wrapper = mountComponent('primary')
    await flushPromises()

    // Fill in email and click add
    await wrapper.find('.input-email').setValue('new@example.com')
    await wrapper.find('.btn-add').trigger('click')
    await flushPromises()

    expect(mockAddCourseTeamMember).toHaveBeenCalledWith('CS101', {
      email: 'new@example.com',
      role: 'ta',
    })
    expect(wrapper.text()).toContain('New TA')
  })

  it('change role calls updateCourseTeamMember', async () => {
    const updated = { ...mockTeam[1], role: 'primary' as const }
    mockUpdateCourseTeamMember.mockResolvedValue(updated)

    const wrapper = mountComponent('primary')
    await flushPromises()

    // Change the TA's role via select
    const selects = wrapper.findAll('.role-select')
    // First select in tbody is for the first member's actions
    const taSelect = selects[1] // second team member's role select
    await taSelect.setValue('primary')
    await flushPromises()

    expect(mockUpdateCourseTeamMember).toHaveBeenCalledWith('CS101', 2, {
      role: 'primary',
    })
  })

  it('remove calls removeCourseTeamMember with confirmation', async () => {
    mockRemoveCourseTeamMember.mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mountComponent('primary')
    await flushPromises()

    const removeButtons = wrapper.findAll('.btn-remove')
    await removeButtons[1].trigger('click') // remove TA
    await flushPromises()

    expect(mockRemoveCourseTeamMember).toHaveBeenCalledWith('CS101', 2)
    // TA should be removed from list
    expect(wrapper.findAll('tbody tr').length).toBe(1)
  })

  it('displays last-primary error gracefully', async () => {
    mockRemoveCourseTeamMember.mockRejectedValue({
      response: { data: { error: 'Cannot remove the last primary instructor from a course' } },
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mountComponent('primary')
    await flushPromises()

    const removeButtons = wrapper.findAll('.btn-remove')
    await removeButtons[0].trigger('click') // try to remove primary
    await flushPromises()

    expect(wrapper.text()).toContain('Cannot remove the last primary instructor')
  })
})
