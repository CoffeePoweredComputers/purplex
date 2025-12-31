import { afterEach, beforeEach, describe, expect, it, Mock, vi } from 'vitest'
import axios from 'axios'
import authService from '../auth.service'
import { firebaseAuth } from '../../firebaseConfig'
import { getIdToken, signOut, User } from 'firebase/auth'
import { log } from '../../utils/logger'

// Mock dependencies
vi.mock('axios')
vi.mock('../../firebaseConfig', () => ({
  firebaseAuth: {
    currentUser: null
  }
}))
vi.mock('firebase/auth', () => ({
  getIdToken: vi.fn(),
  signOut: vi.fn()
}))
vi.mock('../../utils/logger', () => ({
  log: {
    error: vi.fn()
  }
}))

// Mock localStorage for happy-dom environment
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
    get length() { return Object.keys(store).length },
    key: (index: number) => Object.keys(store)[index] || null
  }
})()

Object.defineProperty(globalThis, 'localStorage', {
  value: localStorageMock,
  writable: true
})

// Mock user object
const mockUser: Partial<User> = {
  uid: 'test-uid',
  email: 'test@example.com',
  displayName: 'Test User'
}

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset localStorage
    localStorage.clear()
  })

  afterEach(() => {
    // Clean up
    firebaseAuth.currentUser = null
  })

  describe('validateToken', () => {
    it('should return authenticated false when no user is logged in', async () => {
      firebaseAuth.currentUser = null

      const result = await authService.validateToken()

      expect(result).toEqual({ authenticated: false })
      expect(getIdToken).not.toHaveBeenCalled()
      expect(axios.post).not.toHaveBeenCalled()
    })

    it('should validate token successfully when user is logged in', async () => {
      firebaseAuth.currentUser = mockUser as User
      const mockToken = 'test-token'
      const mockResponse = {
        authenticated: true,
        user: {
          username: 'testuser',
          email: 'test@example.com',
          role: 'student'
        }
      };

      (getIdToken as Mock).mockResolvedValue(mockToken);
      (axios.post as Mock).mockResolvedValue({ data: mockResponse })

      const result = await authService.validateToken()

      expect(getIdToken).toHaveBeenCalledWith(mockUser)
      expect(axios.post).toHaveBeenCalledWith(
        '/api/auth/status/',
        {},
        {
          headers: {
            Authorization: `Bearer ${mockToken}`
          }
        }
      )
      expect(result).toEqual(mockResponse)
    })

    it('should handle token retrieval errors', async () => {
      firebaseAuth.currentUser = mockUser as User
      const mockError = new Error('Token retrieval failed');

      (getIdToken as Mock).mockRejectedValue(mockError)

      const result = await authService.validateToken()

      expect(result).toEqual({
        authenticated: false,
        error: 'Token retrieval failed'
      })
      expect(log.error).toHaveBeenCalledWith('Token validation error', mockError)
    })

    it('should handle backend validation errors', async () => {
      firebaseAuth.currentUser = mockUser as User
      const mockToken = 'test-token'
      const mockError = new Error('Backend validation failed');

      (getIdToken as Mock).mockResolvedValue(mockToken);
      (axios.post as Mock).mockRejectedValue(mockError)

      const result = await authService.validateToken()

      expect(result).toEqual({
        authenticated: false,
        error: 'Backend validation failed'
      })
      expect(log.error).toHaveBeenCalledWith('Token validation error', mockError)
    })

    it('should handle network errors gracefully', async () => {
      firebaseAuth.currentUser = mockUser as User
      const mockToken = 'test-token'
      const networkError = new Error('Network error')
      networkError.name = 'NetworkError';

      (getIdToken as Mock).mockResolvedValue(mockToken);
      (axios.post as Mock).mockRejectedValue(networkError)

      const result = await authService.validateToken()

      expect(result).toEqual({
        authenticated: false,
        error: 'Network error'
      })
    })
  })

  describe('logout', () => {
    it('should logout successfully', async () => {
      localStorage.setItem('user', JSON.stringify({ email: 'test@example.com' }));
      (signOut as Mock).mockResolvedValue(undefined)

      const result = await authService.logout()

      expect(signOut).toHaveBeenCalledWith(firebaseAuth)
      expect(localStorage.getItem('user')).toBeNull()
      expect(result).toBe(true)
    })

    it('should handle logout errors', async () => {
      const mockError = new Error('Logout failed');
      (signOut as Mock).mockRejectedValue(mockError)

      await expect(authService.logout()).rejects.toThrow('Logout failed')
      expect(log.error).toHaveBeenCalledWith('Logout error', mockError)
    })

    it('should clear localStorage even if not set', async () => {
      // localStorage is already empty
      (signOut as Mock).mockResolvedValue(undefined)

      const result = await authService.logout()

      expect(result).toBe(true)
      expect(localStorage.getItem('user')).toBeNull()
    })
  })

  describe('getCurrentUser', () => {
    it('should return null when no user is logged in', () => {
      firebaseAuth.currentUser = null

      const user = authService.getCurrentUser()

      expect(user).toBeNull()
    })

    it('should return the current user when logged in', () => {
      firebaseAuth.currentUser = mockUser as User

      const user = authService.getCurrentUser()

      expect(user).toEqual(mockUser)
    })
  })
})
