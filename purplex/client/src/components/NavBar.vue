<template>
  <nav class="navbar-wrapper">
    <div class="navbar-container">
      <div class="nav-logo">
        <router-link
          to="/home"
          class="logo-link"
        >
          <img
            src="/plx-logo.png"
            :alt="brandName"
            class="logo-icon"
          >
          <span
            class="logo-text"
            :class="{ 'non-latin': isNonLatinBrand }"
          >{{ brandName }}</span>
        </router-link>
      </div>

      <div class="nav-items">
        <router-link
          v-if="isAdmin"
          to="/admin/users"
          class="nav-item admin-item"
        >
          <span class="nav-icon">⚙️</span>
          <span>Admin</span>
        </router-link>

        <button
          class="nav-item account-item"
          @click="showAccountModal = true"
        >
          <span class="nav-icon">👤</span>
          <span>Account</span>
        </button>
      </div>
    </div>

    <AccountModal
      :is-visible="showAccountModal"
      @close="showAccountModal = false"
    />
  </nav>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useStore } from 'vuex';
import { useI18n } from 'vue-i18n';
import AccountModal from '../modals/AccountModal.vue';
import { getBrandName, usesNonLatinBrand } from '../i18n/brand';

const store = useStore();
const { locale } = useI18n();

const showAccountModal = ref(false);

const isAdmin = computed(() => store.getters['auth/isAdmin']);

const brandName = computed(() => getBrandName(locale.value));
const isNonLatinBrand = computed(() => usesNonLatinBrand(locale.value));
</script>

<style scoped>
/* Navbar wrapper - sticky positioning, full width */
.navbar-wrapper {
    position: sticky;
    top: 0;
    width: 100%;
    z-index: 999;
    background: linear-gradient(180deg, var(--color-bg-panel) 0%, var(--color-bg-dark) 100%);
    border-bottom: 1px solid rgba(139, 126, 200, 0.2);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

/* Inner container for content centering */
.navbar-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) var(--spacing-xl);
}

/* Logo section */
.nav-logo {
    flex-shrink: 0;
}

.logo-link {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: 0 var(--spacing-xl) 0 var(--spacing-lg);
    text-decoration: none;
    transition: var(--transition-base);
    border-radius: var(--radius-base);
    position: relative;
    overflow: visible;
}

.logo-link::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 0;
    height: 2px;
    background: linear-gradient(90deg, #8b7ec8, #9b8fd4);
    transition: var(--transition-base);
}

.logo-link:hover::after {
    width: 100%;
}

.logo-link:hover {
    background: rgba(139, 126, 200, 0.1);
}

.logo-link:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.logo-icon {
    width: 80px;
    height: 80px;
    display: block;
    margin: var(--spacing-sm);
    object-fit: cover;
    object-position: center center;
    transform: scale(2.2);
}

.logo-text {
    font-family: 'Exo 2', sans-serif;
    font-weight: 800;
    font-size: 3rem;
    background: linear-gradient(135deg, #a78bfa 0%, #c4b5fd 50%, #8b7ec8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 1px;
    margin: 0;
    line-height: 1.4;
    padding-bottom: 0.15em;
    overflow: visible;
}

/* Non-Latin script styling (fallback to system fonts for complex scripts) */
.logo-text.non-latin {
    font-family: 'Noto Sans', 'Noto Sans Devanagari', 'Noto Sans Telugu',
                 'Noto Sans Tamil', 'Noto Sans Kannada', 'Noto Sans Gurmukhi',
                 'Noto Sans Thai', 'Noto Sans JP', 'Noto Sans SC', system-ui, sans-serif;
    font-weight: 700;
    letter-spacing: 0;
}

/* Navigation items container */
.nav-items {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

/* Individual nav items (both links and buttons) */
.nav-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-lg);
    background: rgba(255, 255, 255, 0.03);
    color: var(--color-text-secondary);
    border: 1px solid rgba(139, 126, 200, 0.15);
    border-radius: var(--radius-base);
    font-weight: 600;
    font-size: var(--font-size-base);
    text-decoration: none;
    cursor: pointer;
    transition: var(--transition-base);
    position: relative;
    font-family: inherit;
}

.nav-item:hover {
    color: var(--color-text-primary);
    background: rgba(139, 126, 200, 0.15);
    border-color: rgba(139, 126, 200, 0.4);
    box-shadow: 0 2px 8px rgba(139, 126, 200, 0.2);
}

.nav-item:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.nav-icon {
    font-size: var(--font-size-base);
    display: inline-block;
}

/* Admin item styling */
.admin-item {
    background: var(--color-admin);
    color: var(--color-text-primary);
    border-color: transparent;
    box-shadow: 0 2px 8px rgba(103, 58, 183, 0.3);
}

.admin-item:hover {
    background: var(--color-admin-hover);
    border-color: transparent;
    box-shadow: 0 4px 12px rgba(103, 58, 183, 0.5);
}

.admin-item.router-link-active {
    box-shadow: 0 4px 16px rgba(103, 58, 183, 0.6);
}

/* Account button styling */
.account-item {
    background: var(--color-bg-dark);
    border-color: var(--color-bg-border);
}

.account-item:hover {
    background: var(--color-bg-input);
    border-color: var(--color-primary-gradient-start);
}

/* Active route indicator */
.router-link-active.nav-item:not(.admin-item) {
    background: var(--color-bg-hover);
    border-color: var(--color-primary-gradient-start);
    color: var(--color-text-primary);
}

.router-link-active.nav-item:not(.admin-item)::after {
    content: '';
    position: absolute;
    bottom: 4px;
    left: 50%;
    transform: translateX(-50%);
    width: 60%;
    height: 2px;
    background: linear-gradient(90deg, var(--color-primary-gradient-start), var(--color-primary-gradient-end));
    border-radius: var(--radius-xs);
}

/* Mobile responsive */
@media (max-width: 768px) {
    .navbar-container {
        padding: var(--spacing-sm) var(--spacing-lg);
    }

    .logo-text {
        font-size: var(--font-size-md);
    }

    .logo-icon {
        width: 60px;
        height: 60px;
    }

    .logo-link {
        padding: var(--spacing-xs) var(--spacing-sm);
        gap: var(--spacing-md);
    }

    .nav-items {
        gap: var(--spacing-xs);
    }

    .nav-item {
        padding: var(--spacing-xs) var(--spacing-md);
        font-size: var(--font-size-sm);
    }

    .nav-icon {
        font-size: var(--font-size-sm);
    }
}

/* Smaller mobile - hide text, show icons only */
@media (max-width: 480px) {
    .navbar-container {
        padding: var(--spacing-sm) var(--spacing-md);
    }

    .logo-text {
        display: none;
    }

    .logo-link {
        padding: var(--spacing-xs) var(--spacing-md);
    }

    .logo-icon {
        width: 28px;
        height: 28px;
    }

    .nav-item span:not(.nav-icon) {
        display: none;
    }

    .nav-item {
        padding: var(--spacing-xs) var(--spacing-sm);
    }
}
</style>
