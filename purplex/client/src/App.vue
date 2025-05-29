<template>
    <h1 style="display: inline-flex; text-align: center; gap: 10px; margin: 5px; font-size: 80px;">
        <img src="/vite.png" alt="Purplex Logo" style="width: 100px; height: 100px; margin-right: 10px;" />
        Purplex
    </h1>
    <div v-if="!authInitialized" style="visibility: hidden;">
        <!-- Keep content hidden but rendered to prevent layout shift -->
        <Login v-if="!loggedIn" />
        <div v-else>
            <NavBar/>
            <router-view />
        </div>
    </div>
    <Login v-else-if="!loggedIn" />
    <div v-else>
        <NavBar/>
        <router-view />
    </div>
    <NotificationToast />
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { useStore } from 'vuex';

/* Components */
import Login from './features/auth/Login.vue';
import NavBar from './components/NavBar.vue';
import NotificationToast from './components/NotificationToast.vue';

export default defineComponent({
    name: 'App',
    components: {
        Login,
        NavBar,
        NotificationToast
    },
    data() {
        return {
            authInitialized: false
        };
    },
    setup() {
        const store = useStore();
        
        const loggedIn = computed(() => store.state.auth.status.loggedIn);
        const user = computed(() => store.state.auth.user);
        
        return {
            loggedIn,
            user
        };
    },
    async mounted() {
        // Wait for Firebase auth to initialize
        const { firebaseAuth } = await import('./firebaseConfig');
        const { onAuthStateChanged } = await import('firebase/auth');
        
        // Create a promise that resolves when auth state is determined
        await new Promise((resolve) => {
            const unsubscribe = onAuthStateChanged(firebaseAuth, (user) => {
                // Auth state has been determined (user is either signed in or null)
                unsubscribe(); // Stop listening after first update
                resolve();
            });
        });
        
        // Now check authentication state
        await this.$store.dispatch('auth/checkAuthState');
        this.authInitialized = true;
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
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
    --shadow-base: 0 4px 12px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 4px 10px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 8px 25px rgba(0, 0, 0, 0.4);
    --shadow-colored: 0 4px 15px rgba(102, 126, 234, 0.3);
    
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

/* Global Styles */
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
</style>
