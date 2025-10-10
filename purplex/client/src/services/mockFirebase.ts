/**
 * Mock Firebase service for development environment.
 * This provides a Firebase-compatible API that works entirely locally
 * without requiring Firebase infrastructure.
 */
import { environment } from './environment';
import { log } from '../utils/logger';

// Types to match Firebase Auth
export interface MockUser {
  uid: string;
  email: string | null;
  displayName: string | null;
  emailVerified: boolean;
  isAnonymous: boolean;
  metadata: {
    creationTime?: string;
    lastSignInTime?: string;
  };
  refreshToken: string;
  getIdToken: (forceRefresh?: boolean) => Promise<string>;
  reload: () => Promise<void>;
  delete: () => Promise<void>;
}

export interface MockAuthCredential {
  providerId: string;
  signInMethod: string;
}

export interface MockUserCredential {
  user: MockUser | null;
  credential: MockAuthCredential | null;
  operationType: string;
}

// Test users matching backend mock_firebase.py
const TEST_USERS = {
  'dhsmith2@illinois.edu': {
    uid: 'mock-uid-dhsmith2',
    email: 'dhsmith2@illinois.edu',
    displayName: 'DH Smith',
    password: 'testpass123'
  },
  'admin@test.local': {
    uid: 'mock-uid-admin',
    email: 'admin@test.local',
    displayName: 'Test Admin',
    password: 'testpass123'
  },
  'instructor@test.local': {
    uid: 'mock-uid-instructor',
    email: 'instructor@test.local',
    displayName: 'Test Instructor',
    password: 'testpass123'
  },
  'student@test.local': {
    uid: 'mock-uid-student',
    email: 'student@test.local',
    displayName: 'Test Student',
    password: 'testpass123'
  },
  'student2@test.local': {
    uid: 'mock-uid-student2',
    email: 'student2@test.local',
    displayName: 'Test Student 2',
    password: 'testpass123'
  }
};

class MockFirebaseAuth {
  public currentUser: MockUser | null = null;
  private authStateListeners: Array<(user: MockUser | null) => void> = [];
  private idTokenListeners: Array<(user: MockUser | null) => void> = [];
  
  constructor() {
    // Check localStorage for persisted auth
    this.restoreAuthState();
  }
  
  /**
   * Sign in with email and password
   */
  async signInWithEmailAndPassword(email: string, password: string): Promise<MockUserCredential> {
    console.log(`[MockFirebase] Signing in with email: ${email}`);
    
    // Check test users
    const testUser = TEST_USERS[email as keyof typeof TEST_USERS];
    if (testUser && password === testUser.password) {
      this.currentUser = this.createMockUser(testUser);
      this.persistAuthState();
      this.notifyAuthStateListeners();
      
      return {
        user: this.currentUser,
        credential: {
          providerId: 'password',
          signInMethod: 'password'
        },
        operationType: 'signIn'
      };
    }
    
    // In development, allow any email/password combination
    if (environment.isDevelopment) {
      const mockUser = {
        uid: `mock-uid-${email.replace('@', '-').replace('.', '-')}`,
        email,
        displayName: email.split('@')[0],
        password
      };
      
      this.currentUser = this.createMockUser(mockUser);
      this.persistAuthState();
      this.notifyAuthStateListeners();
      
      return {
        user: this.currentUser,
        credential: {
          providerId: 'password',
          signInMethod: 'password'
        },
        operationType: 'signIn'
      };
    }
    
    throw new Error('Invalid email or password');
  }
  
  /**
   * Create a new user account
   */
  async createUserWithEmailAndPassword(email: string, password: string): Promise<MockUserCredential> {
    console.log(`[MockFirebase] Creating account for: ${email}`);
    
    // In development, allow any email
    const mockUser = {
      uid: `mock-uid-new-${email.replace('@', '-').replace('.', '-')}`,
      email,
      displayName: email.split('@')[0],
      password
    };
    
    this.currentUser = this.createMockUser(mockUser);
    this.persistAuthState();
    this.notifyAuthStateListeners();
    
    return {
      user: this.currentUser,
      credential: {
        providerId: 'password',
        signInMethod: 'password'
      },
      operationType: 'signUp'
    };
  }
  
  /**
   * Sign in with popup (mock Google sign-in)
   */
  async signInWithPopup(provider: any): Promise<MockUserCredential> {
    console.log('[MockFirebase] Mock Google sign-in');
    
    // Simulate Google sign-in with a test account
    const mockUser = {
      uid: 'mock-uid-google',
      email: 'googleuser@test.local',
      displayName: 'Google Test User',
      password: ''
    };
    
    this.currentUser = this.createMockUser(mockUser);
    this.persistAuthState();
    this.notifyAuthStateListeners();
    
    return {
      user: this.currentUser,
      credential: {
        providerId: 'google.com',
        signInMethod: 'popup'
      },
      operationType: 'signIn'
    };
  }
  
  /**
   * Sign out the current user
   */
  async signOut(): Promise<void> {
    console.log('[MockFirebase] Signing out');
    this.currentUser = null;
    this.clearAuthState();
    this.notifyAuthStateListeners();
  }
  
  /**
   * Listen for auth state changes
   */
  onAuthStateChanged(callback: (user: MockUser | null) => void): () => void {
    this.authStateListeners.push(callback);
    // Immediately call with current state
    callback(this.currentUser);
    
    // Return unsubscribe function
    return () => {
      const index = this.authStateListeners.indexOf(callback);
      if (index > -1) {
        this.authStateListeners.splice(index, 1);
      }
    };
  }
  
  /**
   * Listen for ID token changes
   */
  onIdTokenChanged(callback: (user: MockUser | null) => void): () => void {
    this.idTokenListeners.push(callback);
    callback(this.currentUser);
    
    return () => {
      const index = this.idTokenListeners.indexOf(callback);
      if (index > -1) {
        this.idTokenListeners.splice(index, 1);
      }
    };
  }
  
  /**
   * Create a mock user object
   */
  private createMockUser(userData: any): MockUser {
    const user: MockUser = {
      uid: userData.uid,
      email: userData.email,
      displayName: userData.displayName,
      emailVerified: true,
      isAnonymous: false,
      metadata: {
        creationTime: new Date().toISOString(),
        lastSignInTime: new Date().toISOString()
      },
      refreshToken: 'mock-refresh-token',
      getIdToken: async (forceRefresh?: boolean) => {
        if (forceRefresh) {
          log.debug('[MockFirebase] Force refresh requested, generating new token');
        }
        // Always generate a fresh token (mock doesn't cache)
        return this.createMockToken(userData);
      },
      reload: async () => {
        // No-op in mock
      },
      delete: async () => {
        this.currentUser = null;
        this.clearAuthState();
        this.notifyAuthStateListeners();
      }
    };
    
    return user;
  }
  
  /**
   * Create a mock JWT token
   */
  private createMockToken(userData: any): string {
    // Create a simple mock token for development
    // Format: MOCK.base64(payload).signature
    const payload = {
      uid: userData.uid,
      email: userData.email,
      name: userData.displayName,
      email_verified: true,
      iat: Math.floor(Date.now() / 1000),
      exp: Math.floor(Date.now() / 1000) + 3600 // 1 hour expiry
    };
    
    // Use a special prefix to indicate this is a mock token
    // The backend will detect this and handle it differently
    const encodedPayload = btoa(JSON.stringify(payload));
    return `MOCK.${encodedPayload}.development`;
  }
  
  /**
   * Persist auth state to localStorage
   */
  private persistAuthState(): void {
    if (this.currentUser) {
      // ✅ ONLY store non-sensitive user data
      // ❌ DO NOT store tokens, passwords, or refresh tokens
      const authData = {
        uid: this.currentUser.uid,
        email: this.currentUser.email,
        displayName: this.currentUser.displayName
        // ❌ DO NOT store tokens here
      };
      localStorage.setItem('mockFirebaseAuth', JSON.stringify(authData));
    }
  }
  
  /**
   * Restore auth state from localStorage
   */
  private restoreAuthState(): void {
    const authData = localStorage.getItem('mockFirebaseAuth');
    if (authData) {
      try {
        const userData = JSON.parse(authData);
        this.currentUser = this.createMockUser(userData);
        console.log('[MockFirebase] Restored auth state for:', userData.email);
      } catch (e) {
        console.error('[MockFirebase] Failed to restore auth state:', e);
        this.clearAuthState();
      }
    }
  }
  
  /**
   * Clear auth state from localStorage
   */
  private clearAuthState(): void {
    localStorage.removeItem('mockFirebaseAuth');
  }
  
  /**
   * Notify all auth state listeners
   */
  private notifyAuthStateListeners(): void {
    this.authStateListeners.forEach(callback => {
      callback(this.currentUser);
    });
    this.idTokenListeners.forEach(callback => {
      callback(this.currentUser);
    });
  }
}

// Mock Google Auth Provider
export class MockGoogleAuthProvider {
  static PROVIDER_ID = 'google.com';
  
  constructor() {
    // No configuration needed for mock
  }
  
  addScope(scope: string): void {
    // No-op in mock
  }
  
  setCustomParameters(params: any): void {
    // No-op in mock
  }
}

// Export mock Firebase auth instance
export const mockFirebaseAuth = new MockFirebaseAuth();
export const mockGoogleProvider = new MockGoogleAuthProvider();

// Helper functions to match Firebase API
export const signInWithEmailAndPassword = (auth: any, email: string, password: string) => {
  return mockFirebaseAuth.signInWithEmailAndPassword(email, password);
};

export const createUserWithEmailAndPassword = (auth: any, email: string, password: string) => {
  return mockFirebaseAuth.createUserWithEmailAndPassword(email, password);
};

export const signInWithPopup = (auth: any, provider: any) => {
  return mockFirebaseAuth.signInWithPopup(provider);
};

export const signOut = (auth: any) => {
  return mockFirebaseAuth.signOut();
};

export const onAuthStateChanged = (auth: any, callback: (user: any) => void) => {
  return mockFirebaseAuth.onAuthStateChanged(callback);
};

export const onIdTokenChanged = (auth: any, callback: (user: any) => void) => {
  return mockFirebaseAuth.onIdTokenChanged(callback);
};