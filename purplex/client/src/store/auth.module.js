import AuthService from '../services/auth.service';
import { firebaseAuth } from '../firebaseConfig';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup
} from 'firebase/auth';
import axios from 'axios';

const provider = new GoogleAuthProvider();

// Get DEBUG mode from environment or default to development mode
// In production build, this will be replaced with false
const DEBUG = import.meta.env.MODE === 'development';

console.log('DEBUG:', import.meta.env.MODE);

const user = JSON.parse(localStorage.getItem('user'));
console.log('user:', user);
const initialState = user
  ? { status: { loggedIn: true }, user, debug: DEBUG }
  : { status: { loggedIn: false }, user: null, debug: DEBUG };

console.log('initialState:', initialState);

export const auth = {
  namespaced: true,
  state: initialState,
  actions: {
    // Check auth state and get user data on app init
    async checkAuthState({ commit, state }) {
      // Skip if we're already authenticated or in debug mode
      if (state.debug) return;
      
      if (firebaseAuth.currentUser) {
        try {
          // Get user role from backend
          const response = await axios.get('/api/user/me/');
          console.log('Refreshed user data:', response.data);
          
          const userData = {
            uid: firebaseAuth.currentUser.uid,
            email: firebaseAuth.currentUser.email,
            displayName: firebaseAuth.currentUser.displayName,
            role: response.data.role,
            isAdmin: response.data.is_admin
          };
          commit('loginSuccess', userData);
        } catch (error) {
          console.error('Error refreshing user data:', error);
        }
      }
    },
    async login({ commit }, user) {
      console.log('login', user);
      if (!user.email || !user.password) {
        throw { code: 'auth/missing-fields', message: 'Email and password are required', num: 400 };
      }

      // In debug mode, only allow specific login credentials
      if (DEBUG && user.email === 'admin@example.com' && user.password === 'password') {
        const userData = {
          ...user,
          role: 'admin',
          isAdmin: true
        };
        commit('loginSuccess', userData);
      }

      else if (await signInWithEmailAndPassword(firebaseAuth, user.email, user.password)) {
        // Get user role from backend
        console.log('login success');
        try {
          const response = await axios.get('/api/user/me/');
          console.log(response);
          const userData = {
            ...user,
            role: response.data.role,
            isAdmin: response.data.is_admin
          };
          commit('loginSuccess', userData);
        } catch (error) {
          // If role fetch fails, set as regular user
          const userData = {
            ...user,
            role: 'user',
            isAdmin: false
          };
          commit('loginSuccess', userData);
        }
      } else {
        throw { code: 'auth/invalid-credentials', message: 'Invalid email or password', num: 401 };
      }
    },

    async loginWithGoogle({ commit }) {
      // In debug mode, require a manual login instead of Google
      if (DEBUG) {
        throw { code: 'auth/no-google-auth-in-debug', message: 'No Google login in debug mode', num: 400 }
      }

      if (await signInWithPopup(firebaseAuth, provider)) {
        // Get user role from backend
        try {
          const response = await axios.get('/api/user/me/');
          const userData = {
            email: firebaseAuth.currentUser.email,
            role: response.data.role,
            isAdmin: response.data.is_admin
          };
          commit('loginSuccess', userData);
        } catch (error) {
          // If role fetch fails, set as regular user
          const userData = {
            email: firebaseAuth.currentUser.email,
            role: 'user',
            isAdmin: false
          };
          commit('loginSuccess', userData);
        }
      } else {
        throw { code: 'auth/google-login-failed', message: 'Unable to login with Google', num: 401 };
      }
    },
    async logout({ commit }) {
      try {
        // Use the auth service to sign out
        await AuthService.logout();
        // Update store
        commit('logout');
      } catch (error) {
        console.error('Logout error:', error);
      }
    },
    async createAccount({ commit }, user) {
      // Check for required fields
      if (!user.email || !user.password) {
        throw { code: 'auth/missing-fields', message: 'Email and password are required', num: 400 };
      }

      // In debug mode, simulate account creation with specific credentials
      if (DEBUG) {
        if (user.email === 'new@example.com' && user.password.length >= 6) {
          commit('registerSuccess');
          return true;
        } else {
          throw { code: 'auth/debug-credentials', message: 'In debug mode, use email "new@example.com" with a password of at least 6 characters', num: 401 };
        }
      }

      const response = await createUserWithEmailAndPassword(firebaseAuth, user.email, user.password);
      if (response) {
        commit('registerSuccess');
      } else {
        throw { code: 'auth/registration-failed', message: 'Unable to register user', num: 500 };
      }
    },
    async refreshUserRole({ commit, state }) {
      if (!state.status.loggedIn) return;

      try {
        const response = await axios.get('/api/user/me/');
        const userData = {
          ...state.user,
          role: response.data.role,
          isAdmin: response.data.is_admin
        };
        commit('updateUserData', userData);
      } catch (error) {
        console.error('Error refreshing user role:', error);
      }
    }
  },
  mutations: {
    loginSuccess(state, user) {
      state.status.loggedIn = true;
      state.user = user;
      // Save to localStorage for persistence
      localStorage.setItem('user', JSON.stringify(user));
    },
    logout(state) {
      state.status.loggedIn = false;
      state.user = null;
      // Remove from localStorage
      localStorage.removeItem('user');
    },
    registerSuccess(state) {
      state.status.loggedIn = false;
      // Ensure no stale user data
      localStorage.removeItem('user');
    },
    updateUserData(state, userData) {
      state.user = userData;
      // Update localStorage
      localStorage.setItem('user', JSON.stringify(userData));
    }
  },
  getters: {
    isLoggedIn: state => state.status.loggedIn,
    isAdmin: state => state.user && state.user.isAdmin,
    getUser: state => state.user,
    getUserRole: state => state.user ? state.user.role : null
  }
};
