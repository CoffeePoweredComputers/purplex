import { ensureFirebaseInitialized, firebaseAuth } from '../firebaseConfig';
import { log } from './logger';

// Firebase user type - could be real Firebase User or mock user
interface FirebaseUser {
  uid: string;
  email: string | null;
  displayName: string | null;
}

// Create a promise that resolves when auth state is determined
let authStatePromise: Promise<FirebaseUser | null> | null = null;
export const waitForAuthState = (): Promise<FirebaseUser | null> => {
  if (!authStatePromise) {
    authStatePromise = new Promise((resolve) => {
      ensureFirebaseInitialized().then(() => {
        if (firebaseAuth && firebaseAuth.onAuthStateChanged) {
          // Wait for first auth state change
          let unsubscribe: (() => void) | null = null;
          unsubscribe = firebaseAuth.onAuthStateChanged((user: FirebaseUser | null) => {
            if (unsubscribe) {unsubscribe();} // Immediately unsubscribe after first call
            log.debug('Auth state determined', { hasUser: !!user });
            resolve(user);
          });
        } else {
          // No Firebase auth available
          resolve(null);
        }
      }).catch(() => {
        // Firebase initialization failed, resolve anyway
        resolve(null);
      });
    });
  }
  return authStatePromise;
};