/**
 * Firebase configuration that automatically uses mock or real Firebase
 * based on the environment configuration.
 */
import { environment } from './services/environment';
import { log } from './utils/logger';

// Import types
import type { FirebaseApp } from 'firebase/app';
import type { Auth, AuthProvider } from 'firebase/auth';
import type { MockGoogleAuthProvider } from './services/mockFirebase';

// Firebase configuration interface
interface FirebaseConfig {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
  measurementId?: string;
}

// Auth type that supports both real Firebase and mock
type FirebaseAuthType = Auth | {
  currentUser: unknown;
  onAuthStateChanged: (callback: (user: unknown) => void) => () => void;
  onIdTokenChanged: (callback: (user: unknown) => void) => () => void;
};

// Provider type that supports both real and mock
type ProviderType = AuthProvider | MockGoogleAuthProvider | null;

// Variables that will be exported
let firebaseApp: FirebaseApp | null = null;
let firebaseAuth: FirebaseAuthType | null = null;
let provider: ProviderType = null;

// Initialize based on environment
async function initializeFirebase() {
  log.info('Initializing Firebase', {
    environment: environment.current,
    useMockFirebase: environment.useMockFirebase
  });

  if (environment.useMockFirebase) {
    // Use mock Firebase in development
    log.info('Using Mock Firebase for development');

    // Import mock Firebase
    const mockModule = await import('./services/mockFirebase');
    firebaseAuth = mockModule.mockFirebaseAuth;
    provider = mockModule.mockGoogleProvider;

    // Mock doesn't need an app instance
    firebaseApp = null;

  } else {
    // Use real Firebase in staging/production
    log.info('Using Real Firebase');

    try {
      // Import real Firebase dynamically
      const { initializeApp } = await import('firebase/app');
      const {
        getAuth,
        GoogleAuthProvider,
        setPersistence,
        browserLocalPersistence
      } = await import('firebase/auth');

      // Get config from environment — no fallback, env vars are required
      const envConfig = environment.getFirebaseConfig();

      if (!envConfig) {
        const msg = 'Firebase configuration is missing. Set VITE_FIREBASE_API_KEY, VITE_FIREBASE_AUTH_DOMAIN, and VITE_FIREBASE_PROJECT_ID environment variables. See .env.example for details.';
        log.error(msg);
        throw new Error(msg);
      }

      const firebaseConfig: FirebaseConfig = envConfig;

      // Initialize real Firebase
      firebaseApp = initializeApp(firebaseConfig);
      firebaseAuth = getAuth(firebaseApp);
      provider = new GoogleAuthProvider();

      // ⚠️ CRITICAL: Configure Google provider for third-party cookie blocking
      // This helps with international users and browsers with strict privacy settings
      provider.setCustomParameters({
        // Force account selection - helps bypass cookie issues
        prompt: 'select_account',
        // Additional parameters for better compatibility
        access_type: 'online',
      });

      log.info('Google Auth Provider configured with custom parameters');

      // ⚠️ CRITICAL: Enable persistence for production
      // This keeps users logged in across page refreshes
      await setPersistence(firebaseAuth, browserLocalPersistence);
      log.info('Firebase persistence enabled (browserLocalPersistence)');
    } catch (error) {
      log.error('Failed to initialize Firebase', error);
      // Fall back to mock in case of error during development
      if (environment.isDevelopment) {
        log.warn('Falling back to mock Firebase due to initialization error');
        const mockModule = await import('./services/mockFirebase');
        firebaseAuth = mockModule.mockFirebaseAuth;
        provider = mockModule.mockGoogleProvider;
        firebaseApp = null;
      } else {
        throw error;
      }
    }
  }
}

// Initialize but don't block module loading
let initPromise: Promise<void> | null = null;

function startInitialization() {
  if (!initPromise) {
    initPromise = initializeFirebase();
  }
  return initPromise;
}

// Start initialization
startInitialization();

// Export a function to ensure initialization is complete
export async function ensureFirebaseInitialized() {
  await startInitialization();
  return { firebaseApp, firebaseAuth, provider };
}

// Export the instances (may be null until initialization completes)
export { firebaseApp, firebaseAuth, provider };

// For backward compatibility, also export under old names
export { firebaseAuth as auth };
