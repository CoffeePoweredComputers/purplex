import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DataExport from '../DataExport.vue'

// Mock the privacyService module
vi.mock('../../../services/privacyService', () => ({
  default: {
    exportData: vi.fn(),
    downloadAsJson: vi.fn(),
  },
}))

import privacyService, { type UserDataExport } from '../../../services/privacyService'

describe('DataExport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders download button', () => {
    const wrapper = mount(DataExport)
    expect(wrapper.find('.data-export__btn').exists()).toBe(true)
    expect(wrapper.text()).toContain('Download My Data')
  })

  it('shows loading state during export', async () => {
    // Make exportData hang
    vi.mocked(privacyService.exportData).mockReturnValue(new Promise(() => {}))

    const wrapper = mount(DataExport)
    await wrapper.find('.data-export__btn').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Preparing export...')
    expect((wrapper.find('.data-export__btn').element as HTMLButtonElement).disabled).toBe(true)
  })

  it('calls exportData and downloadAsJson on success', async () => {
    const mockData = { export_version: '1.0', user_id: 1 } as UserDataExport
    vi.mocked(privacyService.exportData).mockResolvedValue(mockData)

    const wrapper = mount(DataExport)
    await wrapper.find('.data-export__btn').trigger('click')
    await flushPromises()

    expect(privacyService.exportData).toHaveBeenCalled()
    expect(privacyService.downloadAsJson).toHaveBeenCalledWith(
      mockData,
      expect.stringContaining('purplex-data-export-')
    )
  })

  it('shows success message after export', async () => {
    vi.mocked(privacyService.exportData).mockResolvedValue({ export_version: '1.0' } as UserDataExport)

    const wrapper = mount(DataExport)
    await wrapper.find('.data-export__btn').trigger('click')
    await flushPromises()

    expect(wrapper.find('.data-export__success').exists()).toBe(true)
    expect(wrapper.text()).toContain('downloaded')
  })

  it('shows error message on failure', async () => {
    vi.mocked(privacyService.exportData).mockRejectedValue(new Error('Network error'))

    const wrapper = mount(DataExport)
    await wrapper.find('.data-export__btn').trigger('click')
    await flushPromises()

    expect(wrapper.find('.data-export__error').exists()).toBe(true)
    expect(wrapper.text()).toContain('Failed to export')
  })

  it('re-enables button after failure', async () => {
    vi.mocked(privacyService.exportData).mockRejectedValue(new Error('fail'))

    const wrapper = mount(DataExport)
    await wrapper.find('.data-export__btn').trigger('click')
    await flushPromises()

    expect((wrapper.find('.data-export__btn').element as HTMLButtonElement).disabled).toBe(false)
  })
})
