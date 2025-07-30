import { ActionContext, Module } from 'vuex';
import AuthService from '../services/auth.service';
import { firebaseAuth } from '../firebaseConfig';
import { 
  createUserWithEmailAndPassword, 
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  signInWithPopup
} from 'firebase/auth';
import axios from 'axios';
import { log } from '../utils/logger';

const provider = new GoogleAuthProvider();

// Get DEBUG mode from environment or default to development mode
// In production build, this will be replaced with false
const DEBUG = import.meta.env.MODE === 'development';

log.debug('Auth module initialized', { mode: import.meta.env.MODE });

// ===== TYPE DEFINITIONS =====

export interface User {
  uid?: string;
  email: string;
  displayName?: string;
  password?: string;
  role: 'admin' | 'user' | 'instructor';
  isAdmin: boolean;
}

export interface AuthStatus {
  loggedIn: boolean;
}

export interface AuthState {
  status: AuthStatus;
  user: User | null;
  debug: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface CreateAccountCredentials {
  email: string;
  password: string;
}

export interface AuthError {
  code: string;
  message: string;
  num: number;
}

export interface UserMeResponse {
  role: string;
  is_admin: boolean;
}

// ===== VUEX MODULE TYPES =====

interface AuthGetters {
  isLoggedIn: boolean;
  isAdmin: boolean;
  getUser: User | null;
  getUserRole: string | null;
}

interface AuthMutations {
  loginSuccess: User;
  logout: void;
  registerSuccess: void;
  updateUserData: User;
}

interface AuthActions {
  checkAuthState: void;
  login: LoginCredentials;
  loginWithGoogle: void;
  logout: void;
  createAccount: CreateAccountCredentials;
  refreshUserRole: void;
}

type AuthActionContext = ActionContext<AuthState, any>;

// ===== INITIAL STATE =====

const user = JSON.parse(localStorage.getItem('user') || 'null') as User | null;
log.debug('User from localStorage', user);

const initialState: AuthState = user
  ? { status: { loggedIn: true }, user, debug: DEBUG }
  : { status: { loggedIn: false }, user: null, debug: DEBUG };

log.debug('Auth initial state', initialState);

// ===== MODULE DEFINITION =====

export const auth: Module<AuthState, any> = {
  namespaced: true,
  state: initialState,
  actions: {
    // Check auth state and get user data on app init
    async checkAuthState({ commit, state }: AuthActionContext): Promise<void> {
      // Skip if we're already authenticated or in debug mode
      if (state.debug) {return;}
      
      if (firebaseAuth.currentUser) {
        try {
          // Get user role from backend
          const response = await axios.get<UserMeResponse>('/api/user/me/');
          log.info('User data refreshed', response.data);
          
          const userData: User = {
            uid: firebaseAuth.currentUser.uid,
            email: firebaseAuth.currentUser.email!,
            displayName: firebaseAuth.currentUser.displayName || undefined,
            role: response.data.role as User['role'],
            isAdmin: response.data.is_admin
          };
          commit('loginSuccess', userData);
        } catch (error) {
          log.error('Error refreshing user data', error);
        }
      }
    },

    async login({ commit }: AuthActionContext, user: LoginCredentials): Promise<void> {
      log.info('Login attempt', { email: user.email });
      if (!user.email || !user.password) {
        throw { code: 'auth/missing-fields', message: 'Email and password are required', num: 400 } as AuthError;
      }

      // In debug mode, only allow specific login credentials
      if (DEBUG && user.email === 'admin@example.com' && user.password === 'password') {
        const userData: User = {
          ...user,
          role: 'admin',
          isAdmin: true
        };
        commit('loginSuccess', userData);
        return;
      }

      try {
        await signInWithEmailAndPassword(firebaseAuth, user.email, user.password);
        // Get user role from backend
        log.info('Login successful');
        try {
          const response = await axios.get<UserMeResponse>('/api/user/me/');
          log.debug('User role response', response.data);
          const userData: User = {
            ...user,
            role: response.data.role as User['role'],
            isAdmin: response.data.is_admin
          };
          commit('loginSuccess', userData);
        } catch (error) {
          // If role fetch fails, set as regular user
          const userData: User = {
            ...user,
            role: 'user',
            isAdmin: false
          };
          commit('loginSuccess', userData);
        }
      } catch (error) {
        throw { code: 'auth/invalid-credentials', message: 'Invalid email or password', num: 401 } as AuthError;
      }
    },

    async loginWithGoogle({ commit }: AuthActionContext): Promise<void> {
      // In debug mode, require a manual login instead of Google
      if (DEBUG) {
        throw { code: 'auth/no-google-auth-in-debug', message: 'No Google login in debug mode', num: 400 } as AuthError;
      }

      try {
        await signInWithPopup(firebaseAuth, provider);
        // Get user role from backend
        try {
          const response = await axios.get<UserMeResponse>('/api/user/me/');
          const userData: User = {
            email: firebaseAuth.currentUser!.email!,
            role: response.data.role as User['role'],
            isAdmin: response.data.is_admin
          };
          commit('loginSuccess', userData);
        } catch (error) {
          // If role fetch fails, set as regular user
          const userData: User = {
            email: firebaseAuth.currentUser!.email!,
            role: 'user',
            isAdmin: false
          };
          commit('loginSuccess', userData);
        }
      } catch (error) {
        throw { code: 'auth/google-login-failed', message: 'Unable to login with Google', num: 401 } as AuthError;
      }
    },

    async logout({ commit }: AuthActionContext): Promise<void> {
      try {
        // Use the auth service to sign out
        await AuthService.logout();
        // Update store
        commit('logout');
      } catch (error) {
        log.error('Logout error', error);
      }
    },

    async createAccount({ commit }: AuthActionContext, user: CreateAccountCredentials): Promise<boolean> {
      // Check for required fields
      if (!user.email || !user.password) {
        throw { code: 'auth/missing-fields', message: 'Email and password are required', num: 400 } as AuthError;
      }

      // In debug mode, simulate account creation with specific credentials
      if (DEBUG) {
        if (user.email === 'new@example.com' && user.password.length >= 6) {
          commit('registerSuccess');
          return true;
        } else {
          throw { 
            code: 'auth/debug-credentials', 
            message: 'In debug mode, use email "new@example.com" with a password of at least 6 characters', 
            num: 401 
          } as AuthError;
        }
      }

      try {
        const response = await createUserWithEmailAndPassword(firebaseAuth, user.email, user.password);
        if (response) {
          commit('registerSuccess');
          return true;
        } else {
          throw { code: 'auth/registration-failed', message: 'Unable to register user', num: 500 } as AuthError;
        }
      } catch (error) {
        throw { code: 'auth/registration-failed', message: 'Unable to register user', num: 500 } as AuthError;
      }
    },

    async refreshUserRole({ commit, state }: AuthActionContext): Promise<void> {
      if (!state.status.loggedIn) {return;}

      try {
        const response = await axios.get<UserMeResponse>('/api/user/me/');
        const userData: User = {
          ...state.user!,
          role: response.data.role as User['role'],
          isAdmin: response.data.is_admin
        };
        commit('updateUserData', userData);
      } catch (error) {
        log.error('Error refreshing user role', error);
      }
    }
  },

  mutations: {
    loginSuccess(state: AuthState, user: User): void {
      state.status.loggedIn = true;
      state.user = user;
      // Save to localStorage for persistence
      localStorage.setItem('user', JSON.stringify(user));
    },

    logout(state: AuthState): void {
      state.status.loggedIn = false;
      state.user = null;
      // Remove from localStorage
      localStorage.removeItem('user');
    },

    registerSuccess(state: AuthState): void {
      state.status.loggedIn = false;
      // Ensure no stale user data
      localStorage.removeItem('user');
    },

    updateUserData(state: AuthState, userData: User): void {
      state.user = userData;
      // Update localStorage
      localStorage.setItem('user', JSON.stringify(userData));
    }
  },

  getters: {
    isLoggedIn: (state: AuthState): boolean => state.status.loggedIn,
    isAdmin: (state: AuthState): boolean => state.user?.isAdmin || false,
    getUser: (state: AuthState): User | null => state.user,
    getUserRole: (state: AuthState): string | null => state.user ? state.user.role : null
  }
};