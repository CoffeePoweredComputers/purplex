import { mount, VueWrapper } from '@vue/test-utils'
import { createRouter, createWebHistory, Router } from 'vue-router'
import { createStore, Store } from 'vuex'
import type { ComponentPublicInstance } from 'vue'
import { vi } from 'vitest'

/**
 * Test helper utilities for Vue component testing
 */

// Create a test router with common routes
export const createTestRouter = (initialRoute = '/'): Router => {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { 
        path: '/', 
        name: 'home',
        component: { template: '<div>Home</div>' }
      },
      { 
        path: '/problems/:problemSetSlug', 
        name: 'problem-set',
        component: { template: '<div>Problem Set</div>' }
      },
      {
        path: '/problems/:problemSetSlug/:problemSlug',
        name: 'problem-detail',
        component: { template: '<div>Problem Detail</div>' }
      },
      { 
        path: '/admin/problems/new', 
        name: 'admin-problem-new',
        component: { template: '<div>New Problem</div>' }
      },
      { 
        path: '/admin/problems/:slug/edit', 
        name: 'admin-problem-edit',
        component: { template: '<div>Edit Problem</div>' }
      },
      {
        path: '/admin/problems',
        name: 'admin-problems',
        component: { template: '<div>Admin Problems</div>' }
      }
    ]
  })
  
  if (initialRoute !== '/') {
    router.push(initialRoute)
  }
  
  return router
}

// Create a test Vuex store with common modules
export const createTestStore = (customModules = {}): Store<any> => {
  const defaultModules = {
    auth: {
      namespaced: true,
      state: () => ({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null
      }),
      getters: {
        isAuthenticated: (state: any) => state.isAuthenticated,
        currentUser: (state: any) => state.user,
        isAdmin: (state: any) => state.user?.role === 'admin'
      },
      actions: {
        login: vi.fn(),
        logout: vi.fn(),
        checkAuth: vi.fn()
      },
      mutations: {
        SET_USER: vi.fn(),
        SET_AUTHENTICATED: vi.fn(),
        SET_LOADING: vi.fn(),
        SET_ERROR: vi.fn()
      }
    },
    courses: {
      namespaced: true,
      state: () => ({
        courses: [],
        enrollments: [],
        currentCourse: null,
        isLoading: false,
        error: null
      }),
      getters: {
        enrolledCourses: (state: any) => state.enrollments,
        currentCourse: (state: any) => state.currentCourse
      },
      actions: {
        fetchCourses: vi.fn(),
        enrollInCourse: vi.fn(),
        selectCourse: vi.fn()
      }
    }
  }

  return createStore({
    modules: {
      ...defaultModules,
      ...customModules
    }
  })
}

// Helper to mount component with common setup
interface MountOptions {
  props?: Record<string, any>
  router?: Router
  store?: Store<any>
  global?: Record<string, any>
  slots?: Record<string, any>
  stubs?: Record<string, any>
}

export const mountComponent = (
  component: any,
  options: MountOptions = {}
): VueWrapper<ComponentPublicInstance> => {
  const {
    props = {},
    router = createTestRouter(),
    store = createTestStore(),
    global = {},
    slots = {},
    stubs = {}
  } = options

  return mount(component, {
    props,
    global: {
      plugins: [router, store],
      stubs: {
        // Common stubs
        'font-awesome-icon': true,
        'router-link': true,
        ...stubs
      },
      ...global
    },
    slots
  })
}

// Wait for async operations
export const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0))

// Wait for component updates
export const waitForUpdates = async (wrapper: VueWrapper) => {
  await wrapper.vm.$nextTick()
  await flushPromises()
}

// Mock common services
export const createMockServices = () => ({
  problemService: {
    loadProblem: vi.fn(),
    loadCategories: vi.fn(),
    createProblem: vi.fn(),
    updateProblem: vi.fn(),
    deleteProblem: vi.fn(),
    testProblem: vi.fn(),
    getHints: vi.fn(),
    getHintContent: vi.fn(),
    updateHints: vi.fn(),
    getProblemHints: vi.fn()
  },
  submissionService: {
    submitEiPL: vi.fn(),
    getSubmissionsSummary: vi.fn(),
    getProblemSubmissions: vi.fn(),
    getProblemBestScore: vi.fn()
  },
  authService: {
    validateToken: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn()
  }
})

// Common test assertions
export const expectToBeVisible = (wrapper: VueWrapper, selector: string) => {
  const element = wrapper.find(selector)
  expect(element.exists()).toBe(true)
  expect(element.isVisible()).toBe(true)
}

export const expectToBeHidden = (wrapper: VueWrapper, selector: string) => {
  const element = wrapper.find(selector)
  expect(element.exists()).toBe(false)
}

export const expectToHaveText = (wrapper: VueWrapper, selector: string, text: string) => {
  const element = wrapper.find(selector)
  expect(element.exists()).toBe(true)
  expect(element.text()).toContain(text)
}

// Mock Firebase
export const mockFirebase = () => {
  vi.mock('../../firebaseConfig', () => ({
    firebaseAuth: {
      currentUser: null,
      onAuthStateChanged: vi.fn()
    }
  }))
}

// Clean up after tests
export const cleanupTest = (wrapper: VueWrapper) => {
  wrapper.unmount()
  vi.clearAllMocks()
}

// Mock notification composable
export const createMockNotification = () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  },
  showSuccess: vi.fn(),
  showError: vi.fn(),
  showWarning: vi.fn(),
  showInfo: vi.fn()
})