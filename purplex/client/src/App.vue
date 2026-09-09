<template>
  <!-- Wrapper for inert attribute when modals are open -->
  <div id="app-content">
    <!-- Skip to main content link - MUST be first for keyboard users -->
    <a
      :href="skipLinkTarget"
      class="skip-link"
      @click.prevent="handleSkipLink"
    >{{ $t('common.skipNav') }}</a>

    <!-- Loading state while determining auth -->
    <div
      v-if="!authReady"
      class="auth-loading"
    >
      <div class="loading-spinner" />
    </div>

    <!-- Login page when not authenticated on protected routes -->
    <Login v-else-if="!loggedIn && currentRouteRequiresAuth" />

    <!-- Main app (authenticated) or public routes (unauthenticated) -->
    <div v-else>
      <NavBar v-if="loggedIn" />
      <div
        id="main-content"
        class="main-content"
        tabindex="-1"
        aria-label="Main content"
      >
        <router-view />
      </div>
    </div>

    <NotificationToast />
    <CookieConsent />
    <AIConsentModal />
    <footer class="app-footer">
      <div class="footer-content">
        <div class="footer-left">
          <span class="copyright">{{ $t('common.footer.copyright', { year: new Date().getFullYear() }) }}</span>
          <router-link
            to="/privacy"
            class="footer-link"
          >
            {{ $t('common.footer.privacyPolicy') }}
          </router-link>
          <router-link
            to="/terms"
            class="footer-link"
          >
            {{ $t('common.footer.termsOfService') }}
          </router-link>
        </div>
        <div class="footer-right">
          <span class="sponsor">{{ $t('common.footer.sponsoredBy') }}</span>
          <img
            class="meta-logo"
            src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Meta_Platforms_Inc._logo.svg/2560px-Meta_Platforms_Inc._logo.svg.png"
            alt=""
            aria-hidden="true"
            height="20"
          >
        </div>
      </div>
    </footer>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, getCurrentInstance } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import { useTokenRefresh } from './composables/useTokenRefresh';
import { useTheme } from './composables/useTheme';

/* Components */
import Login from './features/auth/Login.vue';
import NavBar from './components/NavBar.vue';
import NotificationToast from './components/NotificationToast.vue';
import CookieConsent from './components/privacy/CookieConsent.vue';
import AIConsentModal from './components/privacy/AIConsentModal.vue';

export default defineComponent({
    name: 'App',
    components: {
        Login,
        NavBar,
        NotificationToast,
        CookieConsent,
        AIConsentModal
    },
    setup() {
        const store = useStore();
        const router = useRouter();
        const tokenRefresh = useTokenRefresh();
        useTheme();

        // Make available globally for axios interceptors
        const instance = getCurrentInstance();
        if (instance) {
            instance.appContext.app.config.globalProperties.$tokenRefresh = tokenRefresh;
        }

        // Initialize token refresh (lifecycle hooks will now fire properly)
        tokenRefresh.initialize();

        const loggedIn = computed(() => store.state.auth.status.loggedIn);
        const user = computed(() => store.state.auth.user);
        const authReady = computed(() => store.getters['auth/isAuthReady']);

        // Allow public routes (e.g., /privacy, /terms) to render without auth
        const currentRouteRequiresAuth = computed(() => {
            return router.currentRoute.value.matched.some(
                record => record.meta?.requiresAuth
            );
        });

        // Dynamic skip link target based on current route
        const skipLinkTarget = computed(() => {
            const currentRoute = router.currentRoute.value;
            // Check if we're on a problem set page (matches /courses/:courseId/problem-set/:slug or /problem-set/:slug)
            if (currentRoute.path.includes('/problem-set/')) {
                return '#code-editor';
            }
            return '#main-content';
        });

        const handleSkipLink = () => {
            // Get target element ID from href (e.g., "#main-content" -> "main-content")
            const targetId = skipLinkTarget.value.substring(1);
            const targetElement = document.getElementById(targetId);

            if (targetElement) {
                // Make element focusable if it isn't already
                if (!targetElement.hasAttribute('tabindex')) {
                    targetElement.setAttribute('tabindex', '-1');
                }

                // Scroll to element
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });

                // Focus the element programmatically
                targetElement.focus();
            }
        };

        return {
            loggedIn,
            user,
            authReady,
            currentRouteRequiresAuth,
            tokenRefresh,
            skipLinkTarget,
            handleSkipLink
        };
    },
    async mounted() {
        try {
            // Wait for Firebase to be initialized
            const { ensureFirebaseInitialized, firebaseAuth } = await import('./firebaseConfig');
            await ensureFirebaseInitialized();

            // Only set up auth listener if firebaseAuth is available
            if (firebaseAuth && firebaseAuth.onAuthStateChanged) {
                // Create a promise that resolves when auth state is determined
                await new Promise<void>((resolve) => {
                    const unsubscribe = firebaseAuth.onAuthStateChanged((_user: unknown) => {
                        // Auth state has been determined (user is either signed in or null)
                        unsubscribe(); // Stop listening after first update
                        resolve();
                    });
                });
            }

            // Now check authentication state (this sets authReady in the store)
            await this.$store.dispatch('auth/checkAuthState');
        } catch (error) {
            // Auth initialization error handled silently - ensure authReady is set
            await this.$store.dispatch('auth/checkAuthState');
        }
    }
});
</script>

<style>
/* Theme CSS variables (:root and [data-theme="light"]) now live in
   src/styles/theme-variables.css (loaded via style.css), so both the main
   app and the embed bundle share one definition instead of duplicating it. */

/* Skip to main content link - WCAG 2.1 compliant */
.skip-link {
  position: fixed;
  top: -100%;
  left: 0;
  background: var(--color-primary-gradient-start);
  color: var(--color-text-on-filled);
  padding: var(--spacing-md) var(--spacing-lg);
  text-decoration: none;
  font-weight: 600;
  z-index: 10000;
  border-radius: 0 0 var(--radius-base) 0;
  transition: top 0.2s ease-in-out;
  box-shadow: var(--shadow-lg);
}

.skip-link:focus {
  top: 0;
  outline: 3px solid var(--color-text-on-filled);
  outline-offset: 2px;
}

/* Global Styles */
.main-content {
    max-width: var(--max-width-app);
    margin: 0 auto;
    padding: 0 2rem 80px; /* No top padding to eliminate gap below navbar */
    scroll-margin-top: 120px; /* Account for sticky navbar height */
}

.terms li {
    list-style: none;
    margin-bottom: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-base);
    padding-left: 0;
}

.workspace {
    display: flex;
    justify-content: space-between;
    gap: var(--spacing-lg);
}

.entryspace {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
}

.entry {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
}

.buttons {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.button {
    color: var(--color-text-primary);
    border: none;
    padding: var(--spacing-sm) var(--spacing-lg);
    cursor: pointer;
    position: relative;
    overflow: hidden;
    border-radius: var(--radius-xs);
    transition: var(--transition-base);
}

.ace_editor {
    border-radius: var(--radius-sm);
}

/* Loading Animation */
.bouncing-dots .dot {
    height: 10px;
    width: 10px;
    background-color: var(--color-primary);
    border-radius: var(--radius-circle);
    display: inline-block;
    animation: bounce 1.4s infinite ease-in-out both;
}

.bouncing-dots .dot:nth-child(1) {
    animation-delay: -0.32s;
}

.bouncing-dots .dot:nth-child(2) {
    animation-delay: -0.16s;
}

@keyframes bounce {
    0%, 80%, 100% {
        transform: scale(0);
    }

    40% {
        transform: scale(1.0);
    }
}

.divider {
    border-top: 3px solid var(--color-bg-dark);
}

/* Common utility classes */
.container {
    max-width: var(--max-width-content);
    margin: 0 auto;
    padding: var(--spacing-lg);
}

.page-title {
    font-size: var(--font-size-xl);
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-xl);
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-lg);
    padding-bottom: var(--spacing-base);
    border-bottom: 2px solid var(--color-bg-input);
}

.action-button {
    background-color: var(--color-primary);
    color: var(--color-text-on-filled);
    padding: var(--spacing-sm) var(--spacing-lg);
    border: none;
    border-radius: var(--radius-xs);
    cursor: pointer;
    transition: var(--transition-base);
    font-weight: 600;
}

.action-button:hover {
    background-color: var(--color-primary-hover);
    transform: translateY(-2px);
}

.badge {
    padding: var(--spacing-xs) var(--spacing-md);
    border-radius: var(--radius-round);
    font-size: var(--font-size-sm);
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
}

.loading-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-xl);
    color: var(--color-text-muted);
}

.error-message {
    color: var(--color-error);
    padding: var(--spacing-md);
    border-radius: var(--radius-xs);
    background-color: var(--color-error-bg);
}

/* Footer Styles */
.app-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    background-color: var(--color-bg-header);
    border-top: 1px solid var(--color-bg-border);
    padding: var(--spacing-md) var(--spacing-xl);
    z-index: 1000;
    box-sizing: border-box;
}

.footer-content {
    max-width: var(--max-width-app);
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.footer-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.footer-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.copyright {
    color: var(--color-text-muted);
}

.footer-link {
    color: var(--color-text-muted);
    text-decoration: none;
    transition: color 0.2s;
}

.footer-link:hover {
    color: var(--color-text-secondary);
}

.sponsor {
    color: var(--color-text-muted);
    margin-right: 8px;
}

.meta-logo {
    vertical-align: middle;
    filter: brightness(0) invert(0.7);  /* Makes the logo lighter for dark theme */
    opacity: 0.8;
    transition: all 0.2s;
}

.meta-logo:hover {
    opacity: 1;
    filter: brightness(0) invert(0.9);  /* Even lighter on hover */
}

[data-theme="light"] .meta-logo {
    filter: brightness(0) invert(0.3);  /* Dark gray for light theme */
}

[data-theme="light"] .meta-logo:hover {
    filter: brightness(0) invert(0.1);  /* Near-black on hover */
}

/* Add padding to body to account for fixed footer */
body {
    margin: 0;
    padding-bottom: 60px; /* Space for fixed footer */
}

@media (prefers-reduced-motion: no-preference) {
  body {
    transition: background-color 0.3s ease, color 0.2s ease;
  }
}

/* Auth Loading State */
.auth-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: var(--color-bg-main);
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-bg-input);
  border-top-color: var(--color-primary-gradient-start);
  border-radius: var(--radius-circle);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Mobile responsive */
@media (width <= 768px) {
    .footer-content {
        flex-direction: column;
        gap: var(--spacing-sm);
        text-align: center;
    }

    .app-footer {
        padding: var(--spacing-sm) var(--spacing-md);
    }
}
</style>
