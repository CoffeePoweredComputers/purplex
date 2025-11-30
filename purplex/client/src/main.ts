import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import axios from "axios";
import router from "./router";
import store from "./store";
import { i18n, setLocale, getStoredLocale } from './i18n';
import type { SupportedLocale } from './i18n';
import { log } from './utils/logger';
import { environment } from './services/environment';
import { ensureFirebaseInitialized, firebaseAuth } from './firebaseConfig';

// Configure axios with environment-aware settings
axios.defaults.withCredentials = true;
axios.defaults.baseURL = environment.apiUrl;

// Log environment configuration in development
if (environment.isDevelopment) {
  log.debug('Axios configured', {
    baseURL: axios.defaults.baseURL,
    environment: environment.current,
    mockFirebase: environment.useMockFirebase
  });
}

// Create the app FIRST (before interceptors need to reference it)
const app = createApp(App)
    .use(router)
    .use(store)
    .use(i18n)

// Initialize locale from stored preference
const initializeLocale = async () => {
  const storedLocale = getStoredLocale();
  if (storedLocale !== 'en') {
    await setLocale(storedLocale);
  }
};
initializeLocale();

// Circuit breaker for 401 retry protection
let consecutiveAuthFailures = 0;
const MAX_AUTH_FAILURES = 3;

// Add axios interceptor to include authentication token
// Simple direct Firebase token fetching (no timing dependencies on composables)
axios.interceptors.request.use(async (config) => {
  // Skip token for auth status requests to avoid infinite loop
  if (config.url?.includes('/api/auth/status/')) {
    return config;
  }

  // Wait for Firebase to initialize
  await ensureFirebaseInitialized();

  // Get token directly from Firebase currentUser (no composable timing dependencies)
  if (firebaseAuth && firebaseAuth.currentUser) {
    try {
      const token = await firebaseAuth.currentUser.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;

      if (environment.isDevelopment) {
        log.debug('Added auth token to request', {
          url: config.url,
          hasToken: !!token
        });
      }
    } catch (error) {
      if (environment.isDevelopment) {
        log.error('Failed to get Firebase token', error);
      }
    }
  } else if (environment.isDevelopment) {
    log.debug('No auth token available for request', {
      url: config.url
    });
  }

  return config;
}, (error) => {
  return Promise.reject(error);
});

// Add response interceptor to handle 401 with token refresh retry
axios.interceptors.response.use(
  (response) => {
    // Reset counter on successful response
    consecutiveAuthFailures = 0;
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // If 401 and haven't retried yet, try refreshing token
    if (error.response?.status === 401) {
      consecutiveAuthFailures++;

      // Circuit breaker - too many failures, force logout
      if (consecutiveAuthFailures >= MAX_AUTH_FAILURES) {
        log.error(`Circuit breaker triggered: ${consecutiveAuthFailures} consecutive 401s`);

        // Force logout
        await store.dispatch('auth/logout');

        // Redirect to login
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login');
        }

        // Reset counter
        consecutiveAuthFailures = 0;

        return Promise.reject(new Error('Too many authentication failures'));
      }

      if (!originalRequest._retry) {
        originalRequest._retry = true;

        try {
          log.info(`Received 401 (attempt ${consecutiveAuthFailures}/${MAX_AUTH_FAILURES}), refreshing token...`);

          // Wait for Firebase to initialize
          await ensureFirebaseInitialized();

          // Get fresh token directly from Firebase
          if (firebaseAuth && firebaseAuth.currentUser) {
            const newToken = await firebaseAuth.currentUser.getIdToken(true); // Force refresh

            if (newToken) {
              // Update header and retry
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return axios(originalRequest);
            }
          }
        } catch (refreshError) {
          log.error('Token refresh failed after 401', refreshError);
          // Let it fail - user will be redirected to login
        }
      }
    }

    return Promise.reject(error);
  }
);

// Listen for Firebase auth state changes to sync with Vuex
// Initialize Firebase first, then set up auth listener
ensureFirebaseInitialized().then(() => {
  // Use the auth state changed method from our Firebase config
  // This works for both mock and real Firebase
  if (firebaseAuth && firebaseAuth.onAuthStateChanged) {
    firebaseAuth.onAuthStateChanged(async (user: unknown) => {
  if (user) {
    // User is signed in - dispatch the checkAuthState action
    // This will get the user's role and update the store
    await store.dispatch('auth/checkAuthState');
    // Initialize courses after authentication
    await store.dispatch('courses/initializeCourses');
  } else {
    // User is signed out
    // Only logout if we're not in debug mode
    const debugBypassAuth = store.state.auth.debug || false
    if (!debugBypassAuth) {
      store.commit('auth/logout')
      // Clear courses data on logout
      store.commit('courses/SET_ENROLLED_COURSES', [])
      store.commit('courses/SET_CURRENT_COURSE', null)
    }
  }
    });
  }
});

// Check auth state on app initialization
store.dispatch('auth/checkAuthState')

// Mount the app (LAST)
app.mount('#app')