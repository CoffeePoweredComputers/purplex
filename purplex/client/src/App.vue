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
    --color-bg-section: #2a2a2a;
    --color-bg-input: #333;
    --color-bg-border: #444;
    --color-bg-disabled: #555;

    /* Text Colors */
    --color-text-primary: #fff;
    --color-text-secondary: #e0e0e0;
    --color-text-tertiary: #ddd;
    --color-text-muted: #999;
    --color-text-default: rgb(255 255 255 / 87%);
    --color-text-on-filled: #fff;

    /* Syntax highlighting (token colors — tomorrow_night palette) */
    --color-syntax-keyword: #B294BB;
    --color-syntax-string: #B5BD68;
    --color-syntax-comment: #969896;
    --color-syntax-number: #DE935F;
    --color-syntax-builtin: #81A2BE;
    --color-syntax-variable: #C66;
    --color-syntax-operator: #8ABEB7;
    --color-syntax-punctuation: #C5C8C6;

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
    --color-admin-bg: #673ab7;

    /* Overlay Colors */
    --color-overlay-subtle: rgb(255 255 255 / 5%);
    --color-overlay-medium: rgb(255 255 255 / 10%);
    --color-overlay-strong: rgb(255 255 255 / 15%);

    /* Status Overlays (low-alpha backgrounds) */
    --color-success-overlay: rgb(76 175 80 / 15%);
    --color-warning-overlay: rgb(255 193 7 / 15%);
    --color-error-overlay: rgb(220 53 69 / 15%);
    --color-info-overlay: rgb(33 150 243 / 15%);

    /* Primary Overlays */
    --color-primary-overlay: rgb(102 126 234 / 10%);
    --color-primary-glow: rgb(102 126 234 / 30%);

    /* Status Gradient Endpoints */
    --color-success-accent: #34d399;
    --color-warning-accent: #fbbf24;
    --color-error-accent: #f87171;
    --color-error-dark: #c82333;
    --color-warning-dark: #e0a800;
    --color-success-dark: #218838;
    --color-info-dark: #1976d2;

    /* Extended Overlays (white on dark, black on light) */
    --color-overlay-border: rgb(255 255 255 / 25%);
    --color-overlay-shimmer: rgb(255 255 255 / 35%);

    /* Status Borders (colored border accents) */
    --color-success-border: rgb(76 175 80 / 40%);
    --color-warning-border: rgb(255 193 7 / 40%);
    --color-error-border: rgb(220 53 69 / 40%);
    --color-info-border: rgb(33 150 243 / 40%);

    /* Modal Backdrops */
    --color-backdrop: rgb(0 0 0 / 50%);
    --color-backdrop-heavy: rgb(0 0 0 / 75%);

    /* Colored Glows (box-shadows) */
    --color-primary-shadow: rgb(102 126 234 / 40%);
    --color-admin-shadow: rgb(103 58 183 / 30%);
    --color-info-shadow: rgb(59 130 246 / 30%);
    --color-segment-shadow: rgb(159 122 234 / 30%);
    --color-warning-pulse: rgb(251 191 36 / 70%);
    --color-warning-pulse-end: rgb(251 191 36 / 0%);

    /* Segment Colors (used by SegmentMapping and ViewSubmissionModal) */
    --color-segment-1: #9f7aea;
    --color-segment-2: #4299e1;
    --color-segment-3: #4fd1c5;
    --color-segment-4: #68d391;
    --color-segment-5: #f6ad55;
    --color-segment-6: #fc8181;

    /* Ace Editor */
    --color-ace-selection: rgb(128 0 128 / 30%);

    /* Focus Ring */
    --color-focus-ring: var(--color-primary-gradient-start);

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
    --shadow-xs: 0 1px 3px rgb(0 0 0 / 10%);
    --shadow-subtle: 0 2px 4px rgb(0 0 0 / 10%);
    --shadow-sm: 0 2px 8px rgb(0 0 0 / 20%);
    --shadow-base: 0 4px 12px rgb(0 0 0 / 30%);
    --shadow-md: 0 4px 10px rgb(0 0 0 / 30%);
    --shadow-lg: 0 8px 25px rgb(0 0 0 / 40%);
    --shadow-colored: 0 4px 15px rgb(102 126 234 / 30%);

    /* One-off shadows */
    --shadow-nav: 0 2px 10px rgb(0 0 0 / 30%);
    --shadow-dropdown: 0 8px 32px rgb(0 0 0 / 40%);
    --shadow-modal: 0 4px 20px rgb(0 0 0 / 15%);
    --shadow-inset: inset 0 1px 3px rgb(0 0 0 / 20%);
    --shadow-float: 0 24px 64px rgb(0 0 0 / 50%);
    --shadow-up: 0 -2px 10px rgb(0 0 0 / 30%);
    --shadow-info-hover: 0 4px 12px rgb(59 130 246 / 50%);
    --shadow-info-active: 0 4px 16px rgb(59 130 246 / 60%);
    --shadow-admin-hover: 0 4px 12px rgb(103 58 183 / 50%);
    --shadow-admin-active: 0 4px 16px rgb(103 58 183 / 60%);
    --shadow-segment-hover: 0 4px 16px rgb(159 122 234 / 50%);

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
    --color-bg-panel: #fff;
    --color-bg-panel-light: #fff;
    --color-bg-header: #f1f3f5;
    --color-bg-table: #f1f3f5;
    --color-bg-hover: #dde1e6;
    --color-bg-section: #f5f5f7;
    --color-bg-input: #e9ecef;
    --color-bg-border: #d1d5db;
    --color-bg-disabled: #9ca3af;

    /* Text Colors */
    --color-text-primary: #1a1a2e;
    --color-text-secondary: #1f2937;
    --color-text-tertiary: #374151;
    --color-text-muted: #4b5563;
    --color-text-default: rgb(26 26 46 / 87%);
    --color-text-on-filled: #fff;

    /* Syntax highlighting (token colors — chrome palette) */
    --color-syntax-keyword: #930f80;
    --color-syntax-string: #1A1AA6;
    --color-syntax-comment: #236e24;
    --color-syntax-number: #0000CD;
    --color-syntax-builtin: #3c4c72;
    --color-syntax-variable: #318495;
    --color-syntax-operator: #687687;
    --color-syntax-punctuation: #333;

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
    --color-admin: #7c3aed;
    --color-admin-hover: #6d28d9;
    --color-admin-bg: #ede9fe;

    /* Overlay Colors (white-alpha → black-alpha) */
    --color-overlay-subtle: rgb(0 0 0 / 3%);
    --color-overlay-medium: rgb(0 0 0 / 5%);
    --color-overlay-strong: rgb(0 0 0 / 8%);

    /* Status Overlays */
    --color-success-overlay: rgb(21 128 61 / 8%);
    --color-warning-overlay: rgb(180 83 9 / 8%);
    --color-error-overlay: rgb(220 38 38 / 8%);
    --color-info-overlay: rgb(29 78 216 / 8%);

    /* Primary Overlays */
    --color-primary-overlay: rgb(79 70 229 / 7%);
    --color-primary-glow: rgb(79 70 229 / 15%);

    /* Status Gradient Endpoints */
    --color-success-accent: #059669;
    --color-warning-accent: #d97706;
    --color-error-accent: #ef4444;
    --color-error-dark: #b91c1c;
    --color-warning-dark: #92400e;
    --color-success-dark: #065f46;
    --color-info-dark: #1e40af;

    /* Extended Overlays */
    --color-overlay-border: rgb(0 0 0 / 12%);
    --color-overlay-shimmer: rgb(0 0 0 / 6%);

    /* Status Borders */
    --color-success-border: rgb(21 128 61 / 30%);
    --color-warning-border: rgb(180 83 9 / 30%);
    --color-error-border: rgb(220 38 38 / 30%);
    --color-info-border: rgb(29 78 216 / 30%);

    /* Modal Backdrops (reduced — less darkening over light content) */
    --color-backdrop: rgb(0 0 0 / 30%);
    --color-backdrop-heavy: rgb(0 0 0 / 60%);

    /* Colored Glows (~50% opacity reduction) */
    --color-primary-shadow: rgb(79 70 229 / 20%);
    --color-admin-shadow: rgb(91 33 182 / 15%);
    --color-info-shadow: rgb(29 78 216 / 15%);
    --color-segment-shadow: rgb(124 58 237 / 15%);
    --color-warning-pulse: rgb(180 83 9 / 50%);
    --color-warning-pulse-end: rgb(180 83 9 / 0%);

    /* Segment Colors (deeper for contrast on light backgrounds) */
    --color-segment-1: #7c3aed;
    --color-segment-2: #2563eb;
    --color-segment-3: #0d9488;
    --color-segment-4: #16a34a;
    --color-segment-5: #ea580c;
    --color-segment-6: #dc2626;

    /* Ace Editor */
    --color-ace-selection: rgb(107 0 107 / 20%);

    /* Focus Ring */
    --color-focus-ring: var(--color-primary-gradient-start);

    /* Shadows (same geometry, ~60-70% opacity reduction) */
    --shadow-xs: 0 1px 3px rgb(0 0 0 / 4%);
    --shadow-subtle: 0 2px 4px rgb(0 0 0 / 4%);
    --shadow-sm: 0 2px 8px rgb(0 0 0 / 6%);
    --shadow-base: 0 4px 12px rgb(0 0 0 / 8%);
    --shadow-md: 0 4px 10px rgb(0 0 0 / 8%);
    --shadow-lg: 0 8px 25px rgb(0 0 0 / 10%);
    --shadow-colored: 0 4px 15px rgb(79 70 229 / 15%);

    /* One-off shadows */
    --shadow-nav: 0 2px 10px rgb(0 0 0 / 6%);
    --shadow-dropdown: 0 8px 32px rgb(0 0 0 / 10%);
    --shadow-modal: 0 4px 20px rgb(0 0 0 / 8%);
    --shadow-inset: inset 0 1px 3px rgb(0 0 0 / 6%);
    --shadow-float: 0 24px 64px rgb(0 0 0 / 12%);
    --shadow-up: 0 -2px 10px rgb(0 0 0 / 6%);
    --shadow-info-hover: 0 4px 12px rgb(29 78 216 / 20%);
    --shadow-info-active: 0 4px 16px rgb(29 78 216 / 25%);
    --shadow-admin-hover: 0 4px 12px rgb(91 33 182 / 20%);
    --shadow-admin-active: 0 4px 16px rgb(91 33 182 / 25%);
    --shadow-segment-hover: 0 4px 16px rgb(124 58 237 / 20%);
}

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
