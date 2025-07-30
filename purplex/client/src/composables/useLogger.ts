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
    logError: (message: string, error: any, context?: any) => {
      logger.error(message, { error: error.message || error, context });
    },
    
    logAsyncError: (operation: string, error: any) => {
      logger.error(`Async operation failed: ${operation}`, error);
    },
    
    logApiError: (endpoint: string, error: any) => {
      logger.error(`API call failed`, { endpoint, error: error.message || error });
    },
    
    logUserAction: (action: string, data?: any) => {
      logger.info(`User action: ${action}`, data);
    },
    
    logStateChange: (from: any, to: any) => {
      logger.debug('State change', { from, to });
    }
  };
}

export default useLogger;