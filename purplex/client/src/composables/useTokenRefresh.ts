/**
 * Token Refresh Composable
 *
 * Responsibilities:
 * 1. Track token expiration time
 * 2. Automatically refresh tokens before expiration
 * 3. Handle concurrent refresh requests (only refresh once)
 * 4. Work with both Mock and Real Firebase
 * 5. Emit events for monitoring
 */

import { ref, onMounted, onUnmounted } from 'vue';
import { ensureFirebaseInitialized, firebaseAuth } from '../firebaseConfig';
import { log } from '../utils/logger';

interface TokenState {
  token: string | null;
  expiresAt: number | null;
  isRefreshing: boolean;
}

interface RefreshMetrics {
  totalRefreshes: number;
  lastRefreshTime: Date | null;
  failedRefreshes: number;
  averageRefreshDuration: number;
}

export function useTokenRefresh() {
  const tokenState = ref<TokenState>({
    token: null,
    expiresAt: null,
    isRefreshing: false
  });

  // Add metrics tracking
  const refreshMetrics = ref<RefreshMetrics>({
    totalRefreshes: 0,
    lastRefreshTime: null,
    failedRefreshes: 0,
    averageRefreshDuration: 0
  });

  let refreshTimer: number | null = null;
  let tokenRefreshPromise: Promise<string> | null = null;

  /**
   * Get current token, refreshing if needed.
   * This is the main public method - use this instead of getIdToken() directly.
   */
  async function getValidToken(forceRefresh = false): Promise<string | null> {
    await ensureFirebaseInitialized();

    if (!firebaseAuth?.currentUser) {
      return null;
    }

    // CRITICAL: Check promise FIRST to prevent race conditions
    if (tokenRefreshPromise) {
      log.debug('Token refresh already in progress, waiting...');
      return tokenRefreshPromise;
    }

    // PROACTIVE CHECK: Always verify expiry, don't rely solely on timer
    // This handles browser tab suspension and laptop sleep/wake scenarios
    const now = Date.now() / 1000;
    const needsRefresh = forceRefresh ||
                        !tokenState.value.token ||
                        !tokenState.value.expiresAt ||
                        (tokenState.value.expiresAt - now) < 300; // 5 min buffer

    if (needsRefresh) {
      const expiresIn = tokenState.value.expiresAt ? (tokenState.value.expiresAt - now).toFixed(0) : 'unknown';
      log.debug(`Proactive refresh triggered (expires in ${expiresIn}s)`);
      return refreshToken();
    }

    return tokenState.value.token;
  }

  /**
   * Refresh the token (private method)
   */
  async function refreshToken(): Promise<string> {
    // Prevent concurrent refreshes
    if (tokenRefreshPromise) {
      return tokenRefreshPromise;
    }

    tokenState.value.isRefreshing = true;
    const startTime = Date.now();

    tokenRefreshPromise = (async () => {
      try {
        log.info('Refreshing Firebase token...');

        // Force refresh: getIdToken(true)
        const newToken = await firebaseAuth.currentUser!.getIdToken(true);

        // Decode to get expiry (don't trust, just for scheduling)
        const payload = parseJwt(newToken);
        const expiresAt = payload.exp;

        tokenState.value.token = newToken;
        tokenState.value.expiresAt = expiresAt;

        // Schedule next refresh (55 minutes from now)
        scheduleRefresh(expiresAt);

        // Update metrics
        const duration = Date.now() - startTime;
        refreshMetrics.value.totalRefreshes++;
        refreshMetrics.value.lastRefreshTime = new Date();
        refreshMetrics.value.averageRefreshDuration =
          (refreshMetrics.value.averageRefreshDuration * (refreshMetrics.value.totalRefreshes - 1) + duration) /
          refreshMetrics.value.totalRefreshes;

        log.info('Token refreshed successfully', {
          expiresAt: new Date(expiresAt * 1000),
          duration: `${duration}ms`,
          totalRefreshes: refreshMetrics.value.totalRefreshes
        });

        return newToken;
      } catch (error) {
        refreshMetrics.value.failedRefreshes++;
        log.error('Token refresh failed', {
          error,
          failedRefreshes: refreshMetrics.value.failedRefreshes
        });

        // GRACEFUL DEGRADATION: If we have a recently expired token, keep using it
        // This provides a 10-minute grace period during Firebase API outages
        const now = Date.now() / 1000;
        if (tokenState.value.token &&
            tokenState.value.expiresAt &&
            (now - tokenState.value.expiresAt) < 600) { // 10 min grace period
          log.warn('Using expired token as fallback (Firebase API unavailable)', {
            expiredSince: Math.floor(now - tokenState.value.expiresAt) + 's'
          });
          return tokenState.value.token;
        }

        throw error;
      } finally {
        tokenState.value.isRefreshing = false;
        tokenRefreshPromise = null;
      }
    })();

    return tokenRefreshPromise;
  }

  /**
   * Schedule automatic refresh before expiration
   * NOTE: This is a BACKUP mechanism - proactive check in getValidToken() is primary
   */
  function scheduleRefresh(expiresAt: number): void {
    if (refreshTimer) {
      clearTimeout(refreshTimer);
    }

    const now = Date.now() / 1000;
    const expiresIn = expiresAt - now;

    // Refresh 5 minutes before expiration (300 seconds)
    const refreshIn = Math.max((expiresIn - 300) * 1000, 0);

    log.debug(`Token refresh scheduled in ${refreshIn / 1000}s (backup timer)`);

    refreshTimer = window.setTimeout(() => {
      log.info('Timer-triggered token refresh (backup mechanism)');
      refreshToken();
    }, refreshIn);
  }

  /**
   * Parse JWT without verification (for client-side expiry reading only)
   * Handles both mock tokens (MOCK.payload.development) and real JWTs (header.payload.signature)
   */
  function parseJwt(token: string): any {
    try {
      let payloadPart: string;

      // Handle mock token format: MOCK.payload.development
      if (token.startsWith('MOCK.')) {
        log.debug('Parsing mock Firebase token');
        payloadPart = token.split('.')[1];
      } else {
        // Standard JWT: header.payload.signature
        payloadPart = token.split('.')[1];
      }

      if (!payloadPart) {
        log.error('Token has no payload part');
        return { exp: 0 }; // Return expired token to force refresh
      }

      const base64 = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (e) {
      log.error('Failed to parse JWT', e);
      // Return expired token to force refresh
      return { exp: 0 };
    }
  }

  /**
   * Initialize token refresh listener
   */
  async function initialize(): Promise<void> {
    await ensureFirebaseInitialized();

    if (!firebaseAuth) return;

    // Initial token fetch
    if (firebaseAuth.currentUser) {
      await getValidToken(false);
    }

    // Listen for token changes (handles sign-in/sign-out)
    if (firebaseAuth.onIdTokenChanged) {
      firebaseAuth.onIdTokenChanged(async (user: any) => {
        if (user) {
          log.debug('ID token changed, updating...');
          await getValidToken(true);
        } else {
          // User signed out
          tokenState.value = {
            token: null,
            expiresAt: null,
            isRefreshing: false
          };
          if (refreshTimer) {
            clearTimeout(refreshTimer);
            refreshTimer = null;
          }
        }
      });
    }
  }

  /**
   * Cleanup
   */
  function cleanup(): void {
    if (refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
    tokenRefreshPromise = null;
  }

  // Auto-initialize on mount
  onMounted(() => {
    initialize();
  });

  onUnmounted(() => {
    cleanup();
  });

  return {
    getValidToken,
    tokenState,
    refreshToken,
    initialize,
    cleanup,
    refreshMetrics // Expose metrics for monitoring
  };
}