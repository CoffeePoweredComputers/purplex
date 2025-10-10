import { ensureFirebaseInitialized, firebaseAuth } from '../firebaseConfig';
import { log } from './logger';

// Create a promise that resolves when auth state is determined
let authStatePromise: Promise<any> | null = null;
export const waitForAuthState = (): Promise<any> => {
  if (!authStatePromise) {
    authStatePromise = new Promise((resolve) => {
      ensureFirebaseInitialized().then(() => {
        if (firebaseAuth && firebaseAuth.onAuthStateChanged) {
          // Wait for first auth state change
          let unsubscribe: (() => void) | null = null;
          unsubscribe = firebaseAuth.onAuthStateChanged((user: any) => {
            if (unsubscribe) unsubscribe(); // Immediately unsubscribe after first call
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