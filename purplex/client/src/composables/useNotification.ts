import type { NotificationPayload } from '../types';
import { logger } from '@/utils/logger';

export interface NotificationMethods {
  success: (message: string, details?: string | null) => void;
  error: (message: string, details?: string | null) => void;
  warning: (message: string, details?: string | null) => void;
  info: (message: string, details?: string | null) => void;
}

export interface UseNotificationReturn {
  notify: NotificationMethods;
}

export const useNotification = (): UseNotificationReturn => {
  const notify: NotificationMethods = {
    success(message: string, details: string | null = null): void {
      if (window.$notify) {
        window.$notify({
          type: 'success',
          message,
          details,
          duration: 3000
        } as NotificationPayload);
      } else {
        logger.warn('[Toast] window.$notify not available, toast skipped:', message);
      }
    },

    error(message: string, details: string | null = null): void {
      if (window.$notify) {
        window.$notify({
          type: 'error',
          message,
          details,
          duration: 5000
        } as NotificationPayload);
      } else {
        logger.warn('[Toast] window.$notify not available, toast skipped:', message);
      }
    },

    warning(message: string, details: string | null = null): void {
      if (window.$notify) {
        window.$notify({
          type: 'warning',
          message,
          details,
          duration: 4000
        } as NotificationPayload);
      }
    },

    info(message: string, details: string | null = null): void {
      if (window.$notify) {
        window.$notify({
          type: 'info',
          message,
          details,
          duration: 3000
        } as NotificationPayload);
      }
    }
  };

  return { notify };
};
