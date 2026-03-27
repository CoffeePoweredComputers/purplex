import { beforeEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'
import privacyService from '../privacyService'

vi.mock('axios')

describe('PrivacyService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Consent management
  describe('getConsents', () => {
    it('calls GET /api/users/me/consents/', async () => {
      const mockData = { privacy_policy: { granted: true } }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const result = await privacyService.getConsents()
      expect(axios.get).toHaveBeenCalledWith('/api/users/me/consents/')
      expect(result).toEqual(mockData)
    })
  })

  describe('grantConsent', () => {
    it('calls POST with consent_type', async () => {
      const mockData = { consent_type: 'ai_processing', granted: true }
      vi.mocked(axios.post).mockResolvedValue({ data: mockData })

      const result = await privacyService.grantConsent('ai_processing')
      expect(axios.post).toHaveBeenCalledWith('/api/users/me/consents/', {
        consent_type: 'ai_processing',
      })
      expect(result.granted).toBe(true)
    })
  })

  describe('withdrawConsent', () => {
    it('calls DELETE with consent_type in URL', async () => {
      const mockData = { consent_type: 'ai_processing', granted: false, withdrawn_at: '2024-01-01' }
      vi.mocked(axios.delete).mockResolvedValue({ data: mockData })

      const result = await privacyService.withdrawConsent('ai_processing')
      expect(axios.delete).toHaveBeenCalledWith('/api/users/me/consents/ai_processing/')
      expect(result.granted).toBe(false)
    })
  })

  // Data export
  describe('exportData', () => {
    it('calls GET /api/users/me/data-export/', async () => {
      const mockData = { export_version: '1.0', user_id: 1 }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const result = await privacyService.exportData()
      expect(axios.get).toHaveBeenCalledWith('/api/users/me/data-export/')
      expect(result.export_version).toBe('1.0')
    })
  })

  // Account deletion
  describe('requestDeletion', () => {
    it('calls DELETE /api/users/me/delete/', async () => {
      const mockData = { status: 'deletion_scheduled' }
      vi.mocked(axios.delete).mockResolvedValue({ data: mockData })

      const result = await privacyService.requestDeletion()
      expect(axios.delete).toHaveBeenCalledWith('/api/users/me/delete/')
      expect(result.status).toBe('deletion_scheduled')
    })
  })

  describe('cancelDeletion', () => {
    it('calls POST /api/users/me/cancel-deletion/', async () => {
      const mockData = { status: 'deletion_cancelled' }
      vi.mocked(axios.post).mockResolvedValue({ data: mockData })

      const result = await privacyService.cancelDeletion()
      expect(axios.post).toHaveBeenCalledWith('/api/users/me/cancel-deletion/')
      expect(result.status).toBe('deletion_cancelled')
    })
  })

  // Age verification
  describe('getAgeVerification', () => {
    it('calls GET /api/users/me/age-verification/', async () => {
      const mockData = { verified: false }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const result = await privacyService.getAgeVerification()
      expect(axios.get).toHaveBeenCalledWith('/api/users/me/age-verification/')
      expect(result.verified).toBe(false)
    })
  })

  describe('submitAgeVerification', () => {
    it('posts age verification data', async () => {
      const input = { is_minor: false, is_child: false, date_of_birth: '1990-01-01' }
      const mockData = { ...input, verified_at: '2024-01-01' }
      vi.mocked(axios.post).mockResolvedValue({ data: mockData })

      const result = await privacyService.submitAgeVerification(input)
      expect(axios.post).toHaveBeenCalledWith('/api/users/me/age-verification/', input)
      expect(result.is_minor).toBe(false)
    })
  })

  // Nominee (DPDPA)
  describe('getNominee', () => {
    it('calls GET /api/users/me/nominee/', async () => {
      const mockData = { nominee: null }
      vi.mocked(axios.get).mockResolvedValue({ data: mockData })

      const result = await privacyService.getNominee()
      expect(axios.get).toHaveBeenCalledWith('/api/users/me/nominee/')
      expect(result).toEqual({ nominee: null })
    })
  })

  describe('setNominee', () => {
    it('posts nominee data', async () => {
      const input = { nominee_name: 'Jane', nominee_email: 'jane@example.com', nominee_relationship: 'parent' }
      vi.mocked(axios.post).mockResolvedValue({ data: input })

      const result = await privacyService.setNominee(input)
      expect(axios.post).toHaveBeenCalledWith('/api/users/me/nominee/', input)
      expect(result.nominee_name).toBe('Jane')
    })
  })

  describe('removeNominee', () => {
    it('calls DELETE /api/users/me/nominee/', async () => {
      vi.mocked(axios.delete).mockResolvedValue({ data: null })

      await privacyService.removeNominee()
      expect(axios.delete).toHaveBeenCalledWith('/api/users/me/nominee/')
    })
  })

  // Directory info (FERPA)
  describe('updateDirectoryInfoVisibility', () => {
    it('calls PATCH with visibility flag', async () => {
      const mockData = { directory_info_visible: false }
      vi.mocked(axios.patch).mockResolvedValue({ data: mockData })

      const result = await privacyService.updateDirectoryInfoVisibility(false)
      expect(axios.patch).toHaveBeenCalledWith('/api/users/me/directory-info/', {
        directory_info_visible: false,
      })
      expect(result.directory_info_visible).toBe(false)
    })
  })

  // Utility
  describe('downloadAsJson', () => {
    it('creates and clicks a download link', () => {
      const mockClick = vi.fn()
      const mockAppendChild = vi.fn()
      const mockRemoveChild = vi.fn()
      const mockCreateObjectURL = vi.fn().mockReturnValue('blob:test')
      const mockRevokeObjectURL = vi.fn()

      document.createElement = vi.fn().mockReturnValue({
        href: '',
        download: '',
        click: mockClick,
      }) as any
      document.body.appendChild = mockAppendChild
      document.body.removeChild = mockRemoveChild
      URL.createObjectURL = mockCreateObjectURL
      URL.revokeObjectURL = mockRevokeObjectURL

      privacyService.downloadAsJson({ test: true }, 'export.json')

      expect(mockCreateObjectURL).toHaveBeenCalled()
      expect(mockClick).toHaveBeenCalled()
      expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:test')
    })

    it('propagates errors from API calls', async () => {
      vi.mocked(axios.get).mockRejectedValue(new Error('Network error'))

      await expect(privacyService.exportData()).rejects.toThrow('Network error')
    })
  })
})
