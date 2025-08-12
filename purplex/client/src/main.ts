import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import axios from "axios";
import router from "./router";
import store from "./store";
import { log } from './utils/logger';
import { environment } from './services/environment';
import { ensureFirebaseInitialized, firebaseAuth } from './firebaseConfig';

//import { FontAwesomeIcon } from './plugins/font-awesome'

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

// Add axios interceptor to include authentication token
axios.interceptors.request.use(async (config) => {
  // Skip token for auth status requests to avoid infinite loop
  if (config.url?.includes('/api/auth/status/')) {
    return config;
  }
  
  // Ensure Firebase is initialized
  await ensureFirebaseInitialized();
  
  // Add authentication token if user is logged in
  if (firebaseAuth && firebaseAuth.currentUser) {
    try {
      // Both mock and real Firebase have getIdToken method
      const token = await firebaseAuth.currentUser.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
      
      if (environment.isDevelopment) {
        log.debug('Added auth token to request', {
          url: config.url,
          hasToken: !!token
        });
      }
    } catch (error) {
      log.error('Error getting auth token', error);
    }
  }
  
  return config;
});

// Create the app
const app = createApp(App)
    .use(router)
    .use(store)

// Listen for Firebase auth state changes to sync with Vuex
// Initialize Firebase first, then set up auth listener
ensureFirebaseInitialized().then(() => {
  // Use the auth state changed method from our Firebase config
  // This works for both mock and real Firebase
  if (firebaseAuth && firebaseAuth.onAuthStateChanged) {
    firebaseAuth.onAuthStateChanged(async (user: any) => {
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

// Mount the app
app.mount('#app')
