import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import axios from "axios";
import { firebaseAuth } from './firebaseConfig'
import { onAuthStateChanged, getIdToken } from 'firebase/auth'

import router from "./router";
import store from "./store";

//import { FontAwesomeIcon } from './plugins/font-awesome'

axios.defaults.withCredentials = true
axios.defaults.baseURL = 'http://localhost:8000';

// Add axios interceptor to include Firebase token in all requests
axios.interceptors.request.use(async (config) => {
  // Skip token for auth status requests to avoid infinite loop
  if (config.url?.includes('/api/auth/status/')) {
    return config;
  }
  
  if (firebaseAuth.currentUser) {
    try {
      const token = await getIdToken(firebaseAuth.currentUser);
      config.headers.Authorization = `Bearer ${token}`;
    } catch (error) {
      console.error('Error getting Firebase token:', error);
    }
  }
  return config;
});

// Create the app
const app = createApp(App)
    .use(router)
    .use(store)

// Listen for Firebase auth state changes to sync with Vuex
onAuthStateChanged(firebaseAuth, async (user) => {
  if (user) {
    // User is signed in - dispatch the checkAuthState action
    // This will get the user's role and update the store
    await store.dispatch('auth/checkAuthState');
  } else {
    // User is signed out
    // Only logout if we're not in debug mode
    const debugBypassAuth = store.state.auth.debug || false
    if (!debugBypassAuth) {
      store.commit('auth/logout')
    }
  }
})

// Check auth state on app initialization
store.dispatch('auth/checkAuthState')

// Mount the app
app.mount('#app')
