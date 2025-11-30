/**
 * Vue composable for component-specific logging
 * 
 * Provides a convenient way for Vue components to use structured logging
 * while maintaining component context.
 */

import { getCurrentInstance } from 'vue';
import { log } from '../utils/logger';

export function useLogger(componentName?: string) {
  // Get component name from Vue instance if not provided
  const instance = getCurrentInstance();
  const name = componentName || instance?.type.name || 'UnknownComponent';
  
  // Create component-specific logger
  const logger = log.createComponentLogger(name);
  
  return {
    // Basic logging methods
    debug: logger.debug,
    info: logger.info,
    warn: logger.warn,
    error: logger.error,
    
    // Convenience methods for common patterns
    logError: (message: string, error: unknown, context?: unknown) => {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logger.error(message, { error: errorMessage, context });
    },

    logAsyncError: (operation: string, error: unknown) => {
      logger.error(`Async operation failed: ${operation}`, error);
    },

    logApiError: (endpoint: string, error: unknown) => {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logger.error(`API call failed`, { endpoint, error: errorMessage });
    },

    logUserAction: (action: string, data?: unknown) => {
      logger.info(`User action: ${action}`, data);
    },

    logStateChange: (from: unknown, to: unknown) => {
      logger.debug('State change', { from, to });
    }
  };
}

export default useLogger;