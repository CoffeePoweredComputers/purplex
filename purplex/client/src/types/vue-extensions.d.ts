/**
 * Vue 3 Global Properties Type Extensions
 *
 * Augments Vue's ComponentCustomProperties interface to add
 * custom global properties with full type safety.
 *
 * This file extends Vue's type system to recognize the $tokenRefresh
 * property that we expose globally via app.config.globalProperties
 * in App.vue's setup() function.
 */

import type { useTokenRefresh } from '../composables/useTokenRefresh'

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    /**
     * Token refresh composable exposed globally for axios interceptors
     *
     * Set in App.vue setup() via getCurrentInstance() and accessed in
     * main.ts axios interceptors for authentication token management.
     *
     * Provides methods for token refresh, validation, and metrics tracking.
     */
    $tokenRefresh: ReturnType<typeof useTokenRefresh>
  }
}

// Required to make this a module (must export something)
export {}
