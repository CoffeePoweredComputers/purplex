import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import axios from "axios";
import { firebaseAuth } from './firebaseConfig'
import { onAuthStateChanged } from 'firebase/auth'

import router from "./router";
import store from "./store";

//import { FontAwesomeIcon } from './plugins/font-awesome'

axios.defaults.withCredentials = true
axios.defaults.baseURL = 'http://localhost:8000';

// Create the app
const app = createApp(App)
    .use(router)
    .use(store)

// Listen for Firebase auth state changes to sync with Vuex
onAuthStateChanged(firebaseAuth, (user) => {
  if (user) {
    // User is signed in
    // If we're using Firebase auth in production, update the store
    const userData = {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName,
      photoURL: user.photoURL
    }
    store.commit('auth/loginSuccess', userData)
  } else {
    // User is signed out
    // Only logout if we're not in debug mode
    const debugBypassAuth = store.state.auth.debug || false
    if (!debugBypassAuth) {
      store.commit('auth/logout')
    }
  }
})

// Mount the app
app.mount('#app')
