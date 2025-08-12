/**
 * Single source of truth for environment configuration in the frontend.
 * This service provides consistent environment detection and configuration
 * across the entire Vue application.
 */

export enum Environment {
  DEVELOPMENT = 'development',
  STAGING = 'staging',
  PRODUCTION = 'production'
}

class EnvironmentService {
  private env: Environment;
  
  constructor() {
    // Detect environment from Vite env variables
    const viteEnv = import.meta.env.VITE_PURPLEX_ENV || import.meta.env.MODE;
    
    // Validate and set environment
    switch (viteEnv) {
      case 'development':
        this.env = Environment.DEVELOPMENT;
        break;
      case 'staging':
        this.env = Environment.STAGING;
        break;
      case 'production':
        this.env = Environment.PRODUCTION;
        break;
      default:
        console.warn(`Unknown environment: ${viteEnv}, defaulting to development`);
        this.env = Environment.DEVELOPMENT;
    }
    
    // Debug log for troubleshooting
    if (this.isDevelopment) {
      console.log('Environment variables:', {
        MODE: import.meta.env.MODE,
        VITE_PURPLEX_ENV: import.meta.env.VITE_PURPLEX_ENV,
        VITE_FIREBASE_MOCK: import.meta.env.VITE_FIREBASE_MOCK,
        VITE_API_URL: import.meta.env.VITE_API_URL
      });
    }
  }
  
  /**
   * Get the current environment
   */
  get current(): Environment {
    return this.env;
  }
  
  /**
   * Check if running in development
   */
  get isDevelopment(): boolean {
    return this.env === Environment.DEVELOPMENT;
  }
  
  /**
   * Check if running in staging
   */
  get isStaging(): boolean {
    return this.env === Environment.STAGING;
  }
  
  /**
   * Check if running in production
   */
  get isProduction(): boolean {
    return this.env === Environment.PRODUCTION;
  }
  
  /**
   * Get the API base URL
   */
  get apiUrl(): string {
    return import.meta.env.VITE_API_URL || 'http://localhost:8000';
  }
  
  /**
   * Check if mock Firebase should be used
   */
  get useMockFirebase(): boolean {
    if (!this.isDevelopment) {
      return false;
    }
    const mockFlag = import.meta.env.VITE_FIREBASE_MOCK;
    // Vite env variables are always strings
    return mockFlag === 'true' || mockFlag === true || mockFlag === '1';
  }
  
  /**
   * Get Firebase configuration
   * Returns null if using mock Firebase
   */
  getFirebaseConfig() {
    if (this.useMockFirebase) {
      return null; // Mock doesn't need config
    }
    
    // Real Firebase config from environment variables
    return {
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
      messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID
    };
  }
  
  /**
   * Get CORS configuration
   */
  getCorsConfig() {
    return {
      credentials: true,
      withCredentials: true
    };
  }
  
  /**
   * Check if debug mode is enabled
   */
  get isDebugMode(): boolean {
    return this.isDevelopment && import.meta.env.VITE_DEBUG === 'true';
  }
  
  /**
   * Get feature flags
   */
  getFeatureFlags() {
    return {
      eipl: import.meta.env.VITE_ENABLE_EIPL !== 'false',
      hints: import.meta.env.VITE_ENABLE_HINTS !== 'false',
      courses: import.meta.env.VITE_ENABLE_COURSES !== 'false',
      debugToolbar: this.isDevelopment && import.meta.env.VITE_SHOW_DEBUG_TOOLBAR === 'true'
    };
  }
  
  /**
   * Get logging configuration
   */
  getLoggingConfig() {
    return {
      level: this.isDevelopment ? 'debug' : 'warn',
      enableConsole: this.isDevelopment,
      enableRemote: this.isProduction,
      remoteUrl: import.meta.env.VITE_LOG_REMOTE_URL
    };
  }
  
  /**
   * Log environment information (useful for debugging)
   */
  logEnvironmentInfo(): void {
    console.group('🌍 Environment Configuration');
    console.log('Environment:', this.env);
    console.log('API URL:', this.apiUrl);
    console.log('Mock Firebase:', this.useMockFirebase);
    console.log('Debug Mode:', this.isDebugMode);
    console.log('Feature Flags:', this.getFeatureFlags());
    console.groupEnd();
  }
}

// Create and export singleton instance
export const environment = new EnvironmentService();

// Log environment info in development
if (environment.isDevelopment) {
  environment.logEnvironmentInfo();
}