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

    <!-- Login page when not authenticated -->
    <Login v-else-if="!loggedIn" />

    <!-- Main app when authenticated -->
    <div v-else>
      <NavBar />
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
    <footer class="app-footer">
      <div class="footer-content">
        <div class="footer-left">
          <span class="copyright">{{ $t('common.footer.copyright', { year: new Date().getFullYear() }) }}</span>
          <router-link to="/privacy" class="footer-link">{{ $t('common.footer.privacyPolicy') }}</router-link>
          <router-link to="/terms" class="footer-link">{{ $t('common.footer.termsOfService') }}</router-link>
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

export default defineComponent({
    name: 'App',
    components: {
        Login,
        NavBar,
        NotificationToast,
        CookieConsent
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
                    const unsubscribe = firebaseAuth.onAuthStateChanged((user: unknown) => {
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
/* CSS Variables for consistent theming */
:root {
    /* Primary Colors */
    --color-primary: #800080;
    --color-primary-hover: #9b009b;
    --color-primary-gradient-start: #667eea;
    --color-primary-gradient-end: #764ba2;
    --color-logo-start: #a78bfa;
    --color-logo-mid: #c4b5fd;
    --color-logo-end: #8b7ec8;

    /* Background Colors */
    --color-bg-main: #242424;
    --color-bg-dark: #1a1a1a;
    --color-bg-panel: #1e1e1e;
    --color-bg-panel-light: #1f1f1f;
    --color-bg-header: #191919;
    --color-bg-table: #272727;
    --color-bg-hover: #2a2a2a;
    --color-bg-input: #333;
    --color-bg-border: #444;
    --color-bg-disabled: #555;

    /* Text Colors */
    --color-text-primary: #ffffff;
    --color-text-secondary: #e0e0e0;
    --color-text-tertiary: #ddd;
    --color-text-muted: #999;
    --color-text-default: rgba(255, 255, 255, 0.87);

    /* Status Colors */
    --color-success: #4CAF50;
    --color-success-bg: #2d4d3a;
    --color-success-text: #a3e9c1;
    --color-warning: #FFC107;
    --color-warning-bg: #4d4c2d;
    --color-warning-text: #e9e4a3;
    --color-error: #dc3545;
    --color-error-bg: #4d2d2d;
    --color-error-text: #e9a3a3;
    --color-info: #2196F3;
    --color-info-bg: #2d3a4d;
    --color-info-text: #a3c9e9;

    /* Admin Colors */
    --color-admin: #673ab7;
    --color-admin-hover: #5e35b1;

    /* Overlay Colors */
    --color-overlay-subtle: rgba(255, 255, 255, 0.05);
    --color-overlay-medium: rgba(255, 255, 255, 0.1);
    --color-overlay-strong: rgba(255, 255, 255, 0.15);

    /* Status Overlays (low-alpha backgrounds) */
    --color-success-overlay: rgba(76, 175, 80, 0.15);
    --color-warning-overlay: rgba(255, 193, 7, 0.15);
    --color-error-overlay: rgba(220, 53, 69, 0.15);
    --color-info-overlay: rgba(33, 150, 243, 0.15);

    /* Primary Overlays */
    --color-primary-overlay: rgba(102, 126, 234, 0.1);
    --color-primary-glow: rgba(102, 126, 234, 0.3);

    /* Status Gradient Endpoints */
    --color-success-accent: #34d399;
    --color-warning-accent: #fbbf24;
    --color-error-accent: #f87171;
    --color-error-dark: #c82333;
    --color-warning-dark: #e0a800;
    --color-success-dark: #218838;
    --color-info-dark: #1976d2;

    /* Extended Overlays (white on dark, black on light) */
    --color-overlay-border: rgba(255, 255, 255, 0.25);
    --color-overlay-shimmer: rgba(255, 255, 255, 0.35);

    /* Status Borders (colored border accents) */
    --color-success-border: rgba(76, 175, 80, 0.4);
    --color-warning-border: rgba(255, 193, 7, 0.4);
    --color-error-border: rgba(220, 53, 69, 0.4);
    --color-info-border: rgba(33, 150, 243, 0.4);

    /* Modal Backdrops */
    --color-backdrop: rgba(0, 0, 0, 0.5);
    --color-backdrop-heavy: rgba(0, 0, 0, 0.75);

    /* Colored Glows (box-shadows) */
    --color-primary-shadow: rgba(102, 126, 234, 0.4);
    --color-admin-shadow: rgba(103, 58, 183, 0.3);
    --color-info-shadow: rgba(59, 130, 246, 0.3);
    --color-segment-shadow: rgba(159, 122, 234, 0.3);
    --color-warning-pulse: rgba(251, 191, 36, 0.7);
    --color-warning-pulse-end: rgba(251, 191, 36, 0);

    /* Ace Editor */
    --color-ace-selection: rgba(128, 0, 128, 0.3);

    /* Spacing */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 12px;
    --spacing-base: 15px;
    --spacing-lg: 20px;
    --spacing-xl: 30px;
    --spacing-xxl: 50px;

    /* Border Radius */
    --radius-xs: 4px;
    --radius-sm: 5px;
    --radius-base: 8px;
    --radius-lg: 12px;
    --radius-xl: 20px;
    --radius-round: 30px;
    --radius-circle: 50%;

    /* Shadows */
    --shadow-xs: 0 1px 3px rgba(0, 0, 0, 0.1);
    --shadow-subtle: 0 2px 4px rgba(0, 0, 0, 0.1);
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
    --shadow-base: 0 4px 12px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 10px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 8px 25px rgba(0, 0, 0, 0.4);
    --shadow-colored: 0 4px 15px rgba(102, 126, 234, 0.3);

    /* One-off shadows */
    --shadow-nav: 0 2px 10px rgba(0, 0, 0, 0.3);
    --shadow-dropdown: 0 8px 32px rgba(0, 0, 0, 0.4);
    --shadow-modal: 0 4px 20px rgba(0, 0, 0, 0.15);
    --shadow-inset: inset 0 1px 3px rgba(0, 0, 0, 0.2);
    --shadow-float: 0 24px 64px rgba(0, 0, 0, 0.5);
    --shadow-up: 0 -2px 10px rgba(0, 0, 0, 0.3);
    --shadow-info-hover: 0 4px 12px rgba(59, 130, 246, 0.5);
    --shadow-info-active: 0 4px 16px rgba(59, 130, 246, 0.6);
    --shadow-admin-hover: 0 4px 12px rgba(103, 58, 183, 0.5);
    --shadow-admin-active: 0 4px 16px rgba(103, 58, 183, 0.6);
    --shadow-segment-hover: 0 4px 16px rgba(159, 122, 234, 0.5);

    /* Transitions */
    --transition-fast: all 0.2s ease;
    --transition-base: all 0.3s ease;
    --transition-slow: all 0.5s ease;

    /* Layout */
    --max-width-app: 1280px;
    --max-width-content: 1200px;
    --max-width-panel: 1000px;

    /* Typography */
    --font-size-xs: 0.75rem;
    --font-size-sm: 0.85rem;
    --font-size-base: 1rem;
    --font-size-md: 1.125rem;
    --font-size-lg: 1.5rem;
    --font-size-xl: 1.75rem;
    --font-size-xxl: 2rem;
    --font-size-title: 5rem;
}

/* ──────────────────────────────────────────────
   Light theme overrides
   Only color and shadow variables are re-declared.
   Spacing, radius, transitions, layout, and typography
   are inherited unchanged from :root.
   ────────────────────────────────────────────── */
[data-theme="light"] {
    /* Primary Colors */
    --color-primary: #6b006b;
    --color-primary-hover: #570057;
    --color-primary-gradient-start: #4f46e5;
    --color-primary-gradient-end: #6d28d9;
    --color-logo-start: #7c3aed;
    --color-logo-mid: #8b5cf6;
    --color-logo-end: #6d28d9;

    /* Background Colors */
    --color-bg-main: #f8f9fa;
    --color-bg-dark: #e9ecef;
    --color-bg-panel: #ffffff;
    --color-bg-panel-light: #ffffff;
    --color-bg-header: #ffffff;
    --color-bg-table: #f1f3f5;
    --color-bg-hover: #e9ecef;
    --color-bg-input: #e9ecef;
    --color-bg-border: #d1d5db;
    --color-bg-disabled: #9ca3af;

    /* Text Colors */
    --color-text-primary: #1a1a2e;
    --color-text-secondary: #374151;
    --color-text-tertiary: #4b5563;
    --color-text-muted: #6b7280;
    --color-text-default: rgba(26, 26, 46, 0.87);

    /* Status Colors */
    --color-success: #15803d;
    --color-success-bg: #dcfce7;
    --color-success-text: #14532d;
    --color-warning: #b45309;
    --color-warning-bg: #fef3c7;
    --color-warning-text: #78350f;
    --color-error: #dc2626;
    --color-error-bg: #fee2e2;
    --color-error-text: #7f1d1d;
    --color-info: #1d4ed8;
    --color-info-bg: #dbeafe;
    --color-info-text: #1e3a5f;

    /* Admin Colors */
    --color-admin: #5b21b6;
    --color-admin-hover: #4c1d95;

    /* Overlay Colors (white-alpha → black-alpha) */
    --color-overlay-subtle: rgba(0, 0, 0, 0.03);
    --color-overlay-medium: rgba(0, 0, 0, 0.05);
    --color-overlay-strong: rgba(0, 0, 0, 0.08);

    /* Status Overlays */
    --color-success-overlay: rgba(21, 128, 61, 0.08);
    --color-warning-overlay: rgba(180, 83, 9, 0.08);
    --color-error-overlay: rgba(220, 38, 38, 0.08);
    --color-info-overlay: rgba(29, 78, 216, 0.08);

    /* Primary Overlays */
    --color-primary-overlay: rgba(79, 70, 229, 0.07);
    --color-primary-glow: rgba(79, 70, 229, 0.15);

    /* Status Gradient Endpoints */
    --color-success-accent: #059669;
    --color-warning-accent: #d97706;
    --color-error-accent: #ef4444;
    --color-error-dark: #b91c1c;
    --color-warning-dark: #92400e;
    --color-success-dark: #065f46;
    --color-info-dark: #1e40af;

    /* Extended Overlays */
    --color-overlay-border: rgba(0, 0, 0, 0.12);
    --color-overlay-shimmer: rgba(0, 0, 0, 0.06);

    /* Status Borders */
    --color-success-border: rgba(21, 128, 61, 0.3);
    --color-warning-border: rgba(180, 83, 9, 0.3);
    --color-error-border: rgba(220, 38, 38, 0.3);
    --color-info-border: rgba(29, 78, 216, 0.3);

    /* Modal Backdrops (reduced — less darkening over light content) */
    --color-backdrop: rgba(0, 0, 0, 0.3);
    --color-backdrop-heavy: rgba(0, 0, 0, 0.5);

    /* Colored Glows (~50% opacity reduction) */
    --color-primary-shadow: rgba(79, 70, 229, 0.2);
    --color-admin-shadow: rgba(91, 33, 182, 0.15);
    --color-info-shadow: rgba(29, 78, 216, 0.15);
    --color-segment-shadow: rgba(124, 58, 237, 0.15);
    --color-warning-pulse: rgba(180, 83, 9, 0.5);
    --color-warning-pulse-end: rgba(180, 83, 9, 0);

    /* Ace Editor */
    --color-ace-selection: rgba(107, 0, 107, 0.2);

    /* Shadows (same geometry, ~60-70% opacity reduction) */
    --shadow-xs: 0 1px 3px rgba(0, 0, 0, 0.04);
    --shadow-subtle: 0 2px 4px rgba(0, 0, 0, 0.04);
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.06);
    --shadow-base: 0 4px 12px rgba(0, 0, 0, 0.08);
    --shadow-md: 0 4px 10px rgba(0, 0, 0, 0.08);
    --shadow-lg: 0 8px 25px rgba(0, 0, 0, 0.1);
    --shadow-colored: 0 4px 15px rgba(79, 70, 229, 0.15);

    /* One-off shadows */
    --shadow-nav: 0 2px 10px rgba(0, 0, 0, 0.06);
    --shadow-dropdown: 0 8px 32px rgba(0, 0, 0, 0.1);
    --shadow-modal: 0 4px 20px rgba(0, 0, 0, 0.08);
    --shadow-inset: inset 0 1px 3px rgba(0, 0, 0, 0.06);
    --shadow-float: 0 24px 64px rgba(0, 0, 0, 0.12);
    --shadow-up: 0 -2px 10px rgba(0, 0, 0, 0.06);
    --shadow-info-hover: 0 4px 12px rgba(29, 78, 216, 0.2);
    --shadow-info-active: 0 4px 16px rgba(29, 78, 216, 0.25);
    --shadow-admin-hover: 0 4px 12px rgba(91, 33, 182, 0.2);
    --shadow-admin-active: 0 4px 16px rgba(91, 33, 182, 0.25);
    --shadow-segment-hover: 0 4px 16px rgba(124, 58, 237, 0.2);
}

/* Skip to main content link - WCAG 2.1 compliant */
.skip-link {
  position: fixed;
  top: -100%;
  left: 0;
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
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
  outline: 3px solid var(--color-text-primary);
  outline-offset: 2px;
}

/* Global Styles */
.main-content {
    max-width: var(--max-width-app);
    margin: 0 auto;
    padding: 0 2rem 80px 2rem; /* No top padding to eliminate gap below navbar */
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
    color: var(--color-text-primary);
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
    opacity: 0.8;
}

.footer-link {
    color: var(--color-text-muted);
    text-decoration: none;
    opacity: 0.8;
    transition: opacity 0.2s;
}

.footer-link:hover {
    opacity: 1;
    color: var(--color-text-secondary);
}

.sponsor {
    opacity: 0.8;
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
@media (max-width: 768px) {
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
