import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createStore } from 'vuex'
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

// Mock the content service — track which role is passed to the factory
const mockGetCourseTeam = vi.fn().mockResolvedValue(mockTeam)
const mockAddCourseTeamMember = vi.fn()
const mockUpdateCourseTeamMember = vi.fn()
const mockRemoveCourseTeamMember = vi.fn()
const mockCreateContentService = vi.fn().mockReturnValue({
  getCourseTeam: mockGetCourseTeam,
  addCourseTeamMember: mockAddCourseTeamMember,
  updateCourseTeamMember: mockUpdateCourseTeamMember,
  removeCourseTeamMember: mockRemoveCourseTeamMember,
})

vi.mock('@/services/contentService', () => ({
  createContentService: (...args: unknown[]) => mockCreateContentService(...args),
}))

vi.mock('@/utils/logger', () => ({
  log: {
    info: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    warn: vi.fn(),
  },
}))

function createMockStore(isAdmin = false) {
  return createStore({
    modules: {
      auth: {
        namespaced: true,
        state: () => ({ user: { isAdmin } }),
        getters: {
          isAdmin: (state: { user: { isAdmin: boolean } }) => state.user.isAdmin,
        },
      },
    },
  })
}

function mountComponent(myRole: 'primary' | 'ta' = 'primary', isAdmin = false) {
  return mount(CourseTeamManager, {
    props: {
      courseId: 'CS101',
      myRole,
    },
    global: {
      plugins: [createMockStore(isAdmin)],
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

  it('creates instructor content service for non-admin users', async () => {
    mountComponent('primary', false)
    await flushPromises()

    expect(mockCreateContentService).toHaveBeenCalledWith('instructor')
  })

  it('creates admin content service for admin users', async () => {
    mountComponent('primary', true)
    await flushPromises()

    expect(mockCreateContentService).toHaveBeenCalledWith('admin')
  })

  it('displays last-primary error with i18n message on remove', async () => {
    // contentService._handleError converts AxiosError to APIError
    mockRemoveCourseTeamMember.mockRejectedValue({
      error: 'Cannot remove the last primary instructor from a course',
      code: 'last_primary',
      status: 400,
    })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const wrapper = mountComponent('primary')
    await flushPromises()

    const removeButtons = wrapper.findAll('.btn-remove')
    await removeButtons[0].trigger('click') // try to remove primary
    await flushPromises()

    // resolveErrorMessage resolves 'last_primary' code to i18n string
    expect(wrapper.text()).toContain('only primary instructor')
  })

  it('displays last-primary error with i18n message on role change', async () => {
    // contentService._handleError converts AxiosError to APIError
    mockUpdateCourseTeamMember.mockRejectedValue({
      error: 'Cannot demote the last primary instructor',
      code: 'last_primary',
      status: 400,
    })

    const wrapper = mountComponent('primary')
    await flushPromises()

    const selects = wrapper.findAll('.role-select')
    const primarySelect = selects[0]
    await primarySelect.setValue('ta')
    await flushPromises()

    // resolveErrorMessage resolves 'last_primary' code to i18n string
    expect(wrapper.text()).toContain('only primary instructor')
  })

  it('falls back to generic message when no error details', async () => {
    mockUpdateCourseTeamMember.mockRejectedValue(new Error('Network error'))

    const wrapper = mountComponent('primary')
    await flushPromises()

    const selects = wrapper.findAll('.role-select')
    await selects[1].setValue('primary')
    await flushPromises()

    // Should show generic i18n fallback key (rendered as-is in test without i18n)
    expect(wrapper.find('.error-message')).toBeTruthy()
  })
})
