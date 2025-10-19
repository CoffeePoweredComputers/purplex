/**
 * Firebase configuration that automatically uses mock or real Firebase
 * based on the environment configuration.
 */
import { environment } from './services/environment';

// Import types
import type { FirebaseApp } from 'firebase/app';
import type { Auth } from 'firebase/auth';

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

// Variables that will be exported
let firebaseApp: FirebaseApp | null = null;
let firebaseAuth: Auth | any = null;
let provider: any = null;

// Initialize based on environment
async function initializeFirebase() {
  console.log('🔥 Initializing Firebase...', {
    environment: environment.current,
    useMockFirebase: environment.useMockFirebase
  });
  
  if (environment.useMockFirebase) {
    // Use mock Firebase in development
    console.log('🔥 Using Mock Firebase for development');
    
    // Import mock Firebase
    const mockModule = await import('./services/mockFirebase');
    firebaseAuth = mockModule.mockFirebaseAuth;
    provider = mockModule.mockGoogleProvider;
    
    // Mock doesn't need an app instance
    firebaseApp = null;
    
  } else {
    // Use real Firebase in staging/production
    console.log('🔥 Using Real Firebase');
    
    try {
      // Import real Firebase dynamically
      const { initializeApp } = await import('firebase/app');
      const {
        getAuth,
        GoogleAuthProvider,
        setPersistence,
        browserLocalPersistence
      } = await import('firebase/auth');

      // Get config from environment or use fallback
      const envConfig = environment.getFirebaseConfig();

      const firebaseConfig: FirebaseConfig = envConfig || {
        // Fallback config - should be replaced with environment variables
        apiKey: "AIzaSyCsyYati6ns2CCWgxIuHlHly_VOhXD2sS4",
        authDomain: "purplex-97ff2.firebaseapp.com",
        projectId: "purplex-97ff2",
        storageBucket: "purplex-97ff2.appspot.com",
        messagingSenderId: "863513714403",
        appId: "1:863513714403:web:7207f4a20890ca236d2fd6"
      };

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

      console.log('✅ Google Auth Provider configured with custom parameters');

      // ⚠️ CRITICAL: Enable persistence for production
      // This keeps users logged in across page refreshes
      await setPersistence(firebaseAuth, browserLocalPersistence);
      console.log('✅ Firebase persistence enabled (browserLocalPersistence)');
    } catch (error) {
      console.error('Failed to initialize Firebase:', error);
      // Fall back to mock in case of error during development
      if (environment.isDevelopment) {
        console.log('Falling back to mock Firebase due to initialization error');
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