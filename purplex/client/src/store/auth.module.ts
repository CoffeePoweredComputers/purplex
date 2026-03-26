import { ActionContext, Module } from 'vuex';
import AuthService from '../services/auth.service';
import axios from 'axios';
import { log } from '../utils/logger';
import { ensureFirebaseInitialized } from '../firebaseConfig';
import { environment } from '../services/environment';
import { activityEventService } from '../services/activityEventService';
import privacyService from '../services/privacyService';
import { isValidLocale, setLocale, type SupportedLocale } from '../i18n';
import type { Auth, AuthProvider, User as FirebaseUser, UserCredential } from 'firebase/auth';

/**
 * Fire session.start event if user has behavioral tracking consent.
 * Fire-and-forget — failures are silently caught.
 */
function fireSessionStart(): void {
  privacyService.getConsents().then(consents => {
    if (consents.behavioral_tracking?.granted) {
      activityEventService.record({
        event_type: 'session.start',
        payload: { page: window.location.pathname },
      })
    }
  }).catch(() => { /* consent check failure is non-blocking */ })
}

// Type for Firebase auth functions (works for both real and mock Firebase)
type SignInWithEmailFn = (auth: Auth, email: string, password: string) => Promise<UserCredential>;
type SignInWithPopupFn = (auth: Auth, provider: AuthProvider) => Promise<UserCredential>;
type SignInWithRedirectFn = (auth: Auth, provider: AuthProvider) => Promise<void>;
type GetRedirectResultFn = (auth: Auth) => Promise<UserCredential | null>;
type CreateUserFn = (auth: Auth, email: string, password: string) => Promise<UserCredential>;

// Firebase will be initialized asynchronously
let firebaseAuth: Auth | null = null;
let provider: AuthProvider | null = null;
let signInWithEmailAndPassword: SignInWithEmailFn | null = null;
let signInWithPopup: SignInWithPopupFn | null = null;
let signInWithRedirect: SignInWithRedirectFn | null = null;
let getRedirectResult: GetRedirectResultFn | null = null;
let createUserWithEmailAndPassword: CreateUserFn | null = null;

// Initialize Firebase auth functions
async function initializeAuthFunctions() {
  const firebase = await ensureFirebaseInitialized();
  firebaseAuth = firebase.firebaseAuth;
  provider = firebase.provider;

  // For mock Firebase, functions are on the auth object
  // Cast to proper function types - mock Firebase implements compatible interface
  if (environment.useMockFirebase && firebaseAuth) {
    const mockAuth = firebaseAuth as Auth & {
      signInWithEmailAndPassword: (email: string, password: string) => Promise<UserCredential>;
      signInWithPopup: (provider: AuthProvider) => Promise<UserCredential>;
      createUserWithEmailAndPassword: (email: string, password: string) => Promise<UserCredential>;
      currentUser: FirebaseUser | null;
    };
    signInWithEmailAndPassword = (_auth: Auth, email: string, password: string) =>
      mockAuth.signInWithEmailAndPassword(email, password);
    signInWithPopup = (_auth: Auth, prov: AuthProvider) =>
      mockAuth.signInWithPopup(prov);
    signInWithRedirect = (_auth: Auth, _prov: AuthProvider) =>
      mockAuth.signInWithPopup(provider!) as unknown as Promise<void>; // Mock uses popup
    getRedirectResult = (_auth: Auth) =>
      Promise.resolve(mockAuth.currentUser ? { user: mockAuth.currentUser } as UserCredential : null);
    createUserWithEmailAndPassword = (_auth: Auth, email: string, password: string) =>
      mockAuth.createUserWithEmailAndPassword(email, password);
  } else {
    // For real Firebase, import the functions
    const authModule = await import('firebase/auth');
    signInWithEmailAndPassword = authModule.signInWithEmailAndPassword;
    signInWithPopup = authModule.signInWithPopup;
    signInWithRedirect = authModule.signInWithRedirect;
    getRedirectResult = authModule.getRedirectResult;
    createUserWithEmailAndPassword = authModule.createUserWithEmailAndPassword;
    if (!provider) {
      provider = new authModule.GoogleAuthProvider();
      // Configure for third-party cookie blocking compatibility
      provider.setCustomParameters({
        prompt: 'select_account',
        access_type: 'online',
      });
    }
  }
}

// Initialize on module load
initializeAuthFunctions().catch(err => {
  log.error('Failed to initialize Firebase auth', err);
});

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
  languagePreference?: string;
}

export interface AuthStatus {
  loggedIn: boolean;
}

export interface AuthState {
  status: AuthStatus;
  user: User | null;
  debug: boolean;
  authReady: boolean;
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

// Firebase errors have a code property
interface FirebaseError extends Error {
  code: string;
}

function isFirebaseError(error: unknown): error is FirebaseError {
  return typeof error === 'object' && error !== null && 'code' in error;
}

export interface UserMeResponse {
  role: string;
  is_admin: boolean;
  language_preference: string;
}

// ===== VUEX MODULE TYPES =====

// Import RootState to avoid circular dependency - use inline type
interface RootState {
  auth: AuthState;
  courses: unknown;  // Avoid circular import of CoursesState
}

type AuthActionContext = ActionContext<AuthState, RootState>;

// ===== INITIAL STATE =====

const user = JSON.parse(localStorage.getItem('user') || 'null') as User | null;
log.debug('User from localStorage', user);

const initialState: AuthState = user
  ? { status: { loggedIn: true }, user, debug: DEBUG, authReady: false }
  : { status: { loggedIn: false }, user: null, debug: DEBUG, authReady: false };

log.debug('Auth initial state', initialState);

// ===== MODULE DEFINITION =====

export const auth: Module<AuthState, RootState> = {
  namespaced: true,
  state: initialState,
  actions: {
    // Check auth state and get user data on app init
    async checkAuthState({ commit, state }: AuthActionContext): Promise<void> {
      // Skip if we're already authenticated or in debug mode
      if (state.debug) {
        commit('setAuthReady', true);
        return;
      }

      // Ensure Firebase is initialized
      await initializeAuthFunctions();

      // Check for pending redirect result (from Google redirect sign-in)
      const pendingRedirect = sessionStorage.getItem('pendingGoogleRedirect');
      if (pendingRedirect === 'true' && getRedirectResult) {
        try {
          log.info('Checking for redirect authentication result...');
          const result = await getRedirectResult(firebaseAuth);

          if (result && result.user) {
            log.info('Redirect authentication successful', { email: result.user.email });
            sessionStorage.removeItem('pendingGoogleRedirect');

            // Get user role from backend
            try {
              const response = await axios.get<UserMeResponse>('/api/user/me/');
              const userData: User = {
                uid: result.user.uid,
                email: result.user.email!,
                displayName: result.user.displayName || undefined,
                role: response.data.role as User['role'],
                isAdmin: response.data.is_admin,
                languagePreference: response.data.language_preference
              };
              commit('loginSuccess', userData);

              // Sync locale with user's language preference
              if (response.data.language_preference && isValidLocale(response.data.language_preference)) {
                await setLocale(response.data.language_preference as SupportedLocale);
              }
            } catch (error) {
              log.warn('Failed to fetch user role after redirect, using defaults', error);
              const userData: User = {
                uid: result.user.uid,
                email: result.user.email!,
                displayName: result.user.displayName || undefined,
                role: 'user',
                isAdmin: false,
                languagePreference: 'en'
              };
              commit('loginSuccess', userData);
            }

            fireSessionStart();
            commit('setAuthReady', true);
            return;
          } else {
            // No redirect result found
            log.info('No redirect result found');
            sessionStorage.removeItem('pendingGoogleRedirect');
          }
        } catch (error) {
          log.error('Error processing redirect result', error);
          sessionStorage.removeItem('pendingGoogleRedirect');
          // Redirect errors will be shown on the login page if user is not authenticated
        }
      }

      // Check existing auth state
      if (firebaseAuth && firebaseAuth.currentUser) {
        try {
          // Get user role from backend
          const response = await axios.get<UserMeResponse>('/api/user/me/');
          log.info('User data refreshed', response.data);

          const userData: User = {
            uid: firebaseAuth.currentUser.uid,
            email: firebaseAuth.currentUser.email!,
            displayName: firebaseAuth.currentUser.displayName || undefined,
            role: response.data.role as User['role'],
            isAdmin: response.data.is_admin,
            languagePreference: response.data.language_preference
          };
          commit('loginSuccess', userData);

          // Sync locale with user's language preference
          if (response.data.language_preference && isValidLocale(response.data.language_preference)) {
            await setLocale(response.data.language_preference as SupportedLocale);
          }
        } catch (error) {
          log.error('Error refreshing user data', error);
        }
      } else if (state.status.loggedIn) {
        // Firebase has no current user, but localStorage thinks we're logged in
        // Clear the stale data to maintain consistency
        log.info('Clearing stale auth data - Firebase session expired or invalid');
        commit('logout');
      }

      // Mark auth as ready after checking state
      commit('setAuthReady', true);
    },

    async login({ commit }: AuthActionContext, user: LoginCredentials): Promise<void> {
      log.info('Login attempt', { email: user.email });
      if (!user.email || !user.password) {
        throw { code: 'auth/missing-fields', message: 'Email and password are required', num: 400 } as AuthError;
      }

      // Ensure Firebase is initialized
      await initializeAuthFunctions();

      // In debug mode with mock Firebase, accept test credentials
      if (DEBUG && environment.useMockFirebase) {
        // Mock Firebase handles test users
        try {
          const result = await signInWithEmailAndPassword(firebaseAuth, user.email, user.password);
          if (result && result.user) {
            // Try to get user role from backend
            try {
              const response = await axios.get<UserMeResponse>('/api/user/me/');
              log.debug('User role response', response.data);
              const userData: User = {
                email: result.user.email || user.email,
                role: response.data.role as User['role'],
                isAdmin: response.data.is_admin
              };
              commit('loginSuccess', userData);
            } catch (error) {
              // If role fetch fails, use default values
              const userData: User = {
                email: result.user.email || user.email,
                role: 'user',
                isAdmin: false
              };

              // Check if it's a known test admin
              if (user.email === 'admin@test.local' || user.email === 'dhsmith2@illinois.edu') {
                userData.role = 'admin';
                userData.isAdmin = true;
              } else if (user.email === 'instructor@test.local') {
                userData.role = 'instructor';
                userData.isAdmin = false;
              }

              commit('loginSuccess', userData);
            }
            fireSessionStart();
            return;
          }
        } catch (error) {
          log.error('Mock login failed', error);
          throw { code: 'auth/invalid-credentials', message: 'Invalid email or password', num: 401 } as AuthError;
        }
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
        fireSessionStart();
      } catch (error) {
        throw { code: 'auth/invalid-credentials', message: 'Invalid email or password', num: 401 } as AuthError;
      }
    },

    async loginWithGoogle({ commit, dispatch }: AuthActionContext, options: { useRedirect?: boolean, timeoutMs?: number } = {}): Promise<void> {
      // Ensure Firebase is initialized
      await initializeAuthFunctions();

      const useRedirect = options.useRedirect || false;
      const timeoutMs = options.timeoutMs || 15000; // 15 second timeout (reduced from 30s)

      // If redirect mode explicitly requested, use it directly
      if (useRedirect) {
        log.info('Using redirect-based Google sign-in (explicit)');
        return dispatch('loginWithGoogleRedirect');
      }

      // Track when popup auth started
      const startTime = Date.now();

      try {
        // Use popup for Google sign-in with timeout
        log.info('Initiating Google sign-in popup with timeout...', { timeoutMs });

        // Create a timeout promise that rejects after timeoutMs
        const timeoutPromise = new Promise<never>((_, reject) => {
          setTimeout(() => reject({ code: 'auth/popup-timeout', message: 'Sign-in popup timed out' }), timeoutMs);
        });

        // Race between the popup and timeout
        const result = await Promise.race([
          signInWithPopup(firebaseAuth!, provider!),
          timeoutPromise
        ]) as UserCredential;

        if (result && result.user) {
          log.info('Google sign-in successful', { email: result.user.email });

          // Get user role from backend
          try {
            const response = await axios.get<UserMeResponse>('/api/user/me/');
            const userData: User = {
              uid: result.user.uid,
              email: result.user.email!,
              displayName: result.user.displayName || undefined,
              role: response.data.role as User['role'],
              isAdmin: response.data.is_admin
            };
            commit('loginSuccess', userData);
          } catch (error) {
            // If role fetch fails, set as regular user
            log.warn('Failed to fetch user role, using defaults', error);
            const userData: User = {
              uid: result.user.uid,
              email: result.user.email!,
              displayName: result.user.displayName || undefined,
              role: 'user',
              isAdmin: false
            };
            commit('loginSuccess', userData);
          }
          fireSessionStart();
        }
      } catch (error) {
        log.error('Google sign-in popup failed', error);

        // Calculate how long the popup was open
        const elapsedTime = Date.now() - startTime;
        const errorCode = isFirebaseError(error) ? error.code : '';

        // Handle popup timeout - automatically fallback to redirect
        if (errorCode === 'auth/popup-timeout') {
          log.warn('Popup timed out, falling back to redirect mode');
          throw {
            code: 'auth/popup-timeout-redirect',
            message: 'Connection slow - please try again with redirect mode',
            num: 408,
            shouldUseRedirect: true
          } as AuthError & { shouldUseRedirect: boolean };
        }

        // Handle popup blocked or closed
        if (errorCode === 'auth/popup-closed-by-user') {
          // If popup "closed" in less than 2 seconds, it's likely a third-party cookie issue
          // NOT the user actually closing it
          if (elapsedTime < 2000) {
            log.warn('Popup closed instantly - likely third-party cookie blocking', { elapsedTime });
            throw {
              code: 'auth/cookies-blocked',
              message: 'Browser is blocking authentication cookies. Please try redirect mode or check your browser privacy settings.',
              num: 403,
              shouldUseRedirect: true
            } as AuthError & { shouldUseRedirect: boolean };
          }
          // User actually closed the popup
          throw { code: 'auth/popup-closed', message: 'Sign-in popup was closed', num: 401 } as AuthError;
        } else if (errorCode === 'auth/popup-blocked') {
          throw {
            code: 'auth/popup-blocked',
            message: 'Sign-in popup was blocked - please allow popups or try redirect mode',
            num: 401,
            shouldUseRedirect: true
          } as AuthError & { shouldUseRedirect: boolean };
        }

        // Handle network errors - suggest redirect
        if (errorCode === 'auth/network-request-failed') {
          throw {
            code: 'auth/network-error',
            message: 'Network error - please check your connection or try redirect mode',
            num: 503,
            shouldUseRedirect: true
          } as AuthError & { shouldUseRedirect: boolean };
        }

        throw { code: 'auth/google-login-failed', message: 'Unable to login with Google', num: 401 } as AuthError;
      }
    },

    async loginWithGoogleRedirect({ commit }: AuthActionContext): Promise<void> {
      // Ensure Firebase is initialized
      await initializeAuthFunctions();

      try {
        log.info('Initiating Google sign-in redirect...');

        // Store a flag so we know we're expecting a redirect result
        sessionStorage.setItem('pendingGoogleRedirect', 'true');

        // This will redirect away from the page
        await signInWithRedirect(firebaseAuth, provider);

        // Code after this won't execute because we've redirected
      } catch (error) {
        log.error('Google sign-in redirect failed', error);
        sessionStorage.removeItem('pendingGoogleRedirect');
        throw { code: 'auth/redirect-failed', message: 'Unable to initiate redirect login', num: 500 } as AuthError;
      }
    },

    async logout({ commit }: AuthActionContext): Promise<void> {
      // Record session.end before auth token expires (best-effort)
      activityEventService.record({
        event_type: 'session.end',
        payload: { page: window.location.pathname },
      })

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

      // Ensure Firebase is initialized
      await initializeAuthFunctions();

      // In debug mode with mock Firebase, allow any account creation
      if (DEBUG && environment.useMockFirebase) {
        try {
          const response = await createUserWithEmailAndPassword(firebaseAuth, user.email, user.password);
          if (response) {
            commit('registerSuccess');
            return true;
          }
        } catch (error) {
          log.error('Mock account creation failed', error);
          throw { code: 'auth/registration-failed', message: 'Unable to register user', num: 500 } as AuthError;
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

      // ✅ ONLY store non-sensitive user data
      // ❌ NEVER store tokens, passwords, or credentials
      const safeUserData = {
        uid: user.uid,
        email: user.email,
        displayName: user.displayName,
        role: user.role,
        isAdmin: user.isAdmin,
        languagePreference: user.languagePreference
      };

      localStorage.setItem('user', JSON.stringify(safeUserData));
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
    },

    setAuthReady(state: AuthState, ready: boolean): void {
      state.authReady = ready;
    }
  },

  getters: {
    isLoggedIn: (state: AuthState): boolean => state.status.loggedIn,
    isAdmin: (state: AuthState): boolean => state.user?.isAdmin || false,
    isInstructor: (state: AuthState): boolean => {
      // Instructors and admins can access instructor features
      const role = state.user?.role;
      return role === 'instructor' || role === 'admin';
    },
    getUser: (state: AuthState): User | null => state.user,
    getUserRole: (state: AuthState): string | null => state.user ? state.user.role : null,
    isAuthReady: (state: AuthState): boolean => state.authReady,
    getLanguagePreference: (state: AuthState): string => state.user?.languagePreference || 'en'
  }
};
