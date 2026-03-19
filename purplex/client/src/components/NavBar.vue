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
            ref="etymologyContainer"
            class="logo-text"
            :class="{ 'non-latin': isNonLatinBrand }"
          >{{ brandName }}<button
            v-if="hasEtymology"
            class="etymology-superscript"
            :aria-expanded="showEtymology"
            :aria-label="$t('aria.etymologyMeaning')"
            @click.prevent.stop="showEtymology = !showEtymology"
          >*</button></span>
        </router-link>
        <!-- Etymology panel (outside router-link to avoid navigation on click) -->
        <div
          v-if="etymology && showEtymology"
          class="etymology-panel"
          role="dialog"
          aria-labelledby="etymology-title"
        >
          <button
            class="etymology-close"
            :aria-label="$t('common.close')"
            @click="showEtymology = false"
          >
            ×
          </button>
          <p
            id="etymology-title"
            class="etymology-translation"
          >
            "{{ etymology.translation }}"
          </p>
          <ul class="etymology-breakdown">
            <li
              v-for="(item, index) in etymology.breakdown"
              :key="index"
            >
              {{ item }}
            </li>
          </ul>
          <p
            v-if="etymology.note"
            class="etymology-note"
          >
            {{ etymology.note }}
          </p>
        </div>
      </div>

      <div class="nav-items">
        <router-link
          v-if="isInstructor"
          to="/instructor"
          class="nav-item instructor-item"
        >
          <span class="nav-icon">📚</span>
          <span>{{ $t('nav.instructor') }}</span>
        </router-link>

        <router-link
          v-if="isAdmin"
          to="/admin/users"
          class="nav-item admin-item"
        >
          <span class="nav-icon">⚙️</span>
          <span>{{ $t('nav.admin') }}</span>
        </router-link>

        <button
          class="nav-item account-item"
          @click="showAccountModal = true"
        >
          <span class="nav-icon">👤</span>
          <span>{{ $t('nav.account') }}</span>
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
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useStore } from 'vuex';
import { useI18n } from 'vue-i18n';
import AccountModal from '../modals/AccountModal.vue';
import { type BrandEtymology, getBrandName, getEtymology, usesNonLatinBrand } from '../i18n/brand';

const store = useStore();
const { locale } = useI18n();

const showAccountModal = ref(false);
const showEtymology = ref(false);
const etymologyContainer = ref<HTMLElement | null>(null);

const isAdmin = computed(() => store.getters['auth/isAdmin']);
const isInstructor = computed(() => store.getters['auth/isInstructor']);

const brandName = computed(() => getBrandName(locale.value));
const isNonLatinBrand = computed(() => usesNonLatinBrand(locale.value));
const etymology = computed<BrandEtymology | undefined>(() => getEtymology(locale.value));
const hasEtymology = computed(() => !!etymology.value);

// Click outside to close etymology panel
function handleClickOutside(event: MouseEvent) {
  if (showEtymology.value && etymologyContainer.value &&
      !etymologyContainer.value.contains(event.target as Node)) {
    showEtymology.value = false;
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
/* Navbar wrapper - sticky positioning, full width */
.navbar-wrapper {
    position: sticky;
    top: 0;
    width: 100%;
    z-index: 999;
    background: linear-gradient(180deg, var(--color-bg-panel) 0%, var(--color-bg-dark) 100%);
    border-bottom: 1px solid var(--color-primary-overlay);
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
    background: linear-gradient(90deg, var(--color-primary-gradient-end), var(--color-primary-gradient-start));
    transition: var(--transition-base);
}

.logo-link:hover::after {
    width: 100%;
}

.logo-link:hover {
    background: var(--color-primary-overlay);
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
    background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 50%, var(--color-primary-gradient-end) 100%);
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

/* Inline superscript for etymology */
.etymology-superscript {
    display: inline;
    vertical-align: super;
    font-size: 0.4em;
    font-weight: 400;
    padding: 0 0.15em;
    margin-left: 0.1em;
    background: none;
    border: none;
    color: var(--color-text-muted);
    cursor: pointer;
    transition: var(--transition-fast);
    line-height: 1;
    font-family: inherit;
}

.etymology-superscript:hover,
.etymology-superscript:focus {
    color: var(--color-text-primary);
}

.etymology-superscript:focus {
    outline: none;
    text-decoration: underline;
}

/* Etymology panel (click-to-reveal) */
.etymology-panel {
    position: absolute;
    top: 100%;
    left: var(--spacing-lg);
    margin-top: var(--spacing-sm);
    padding: var(--spacing-md) var(--spacing-lg);
    min-width: 280px;
    max-width: 340px;
    background: var(--color-bg-panel);
    border: 1px solid var(--color-primary-glow);
    border-radius: var(--radius-lg);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4),
                0 0 0 1px var(--color-primary-overlay);
    z-index: 1000;
    animation: panelFadeIn 0.15s ease-out;
}

@keyframes panelFadeIn {
    from {
        opacity: 0;
        transform: translateY(-4px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Arrow/caret at top of panel */
.etymology-panel::before {
    content: '';
    position: absolute;
    top: -7px;
    left: 24px;
    width: 12px;
    height: 12px;
    background: var(--color-bg-panel);
    border-left: 1px solid var(--color-primary-glow);
    border-top: 1px solid var(--color-primary-glow);
    transform: rotate(45deg);
}

/* Close button */
.etymology-close {
    position: absolute;
    top: var(--spacing-xs);
    right: var(--spacing-xs);
    width: 20px;
    height: 20px;
    padding: 0;
    background: transparent;
    border: none;
    border-radius: var(--radius-sm);
    color: var(--color-text-muted);
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    transition: var(--transition-fast);
}

.etymology-close:hover {
    background: var(--color-primary-overlay);
    color: var(--color-text-primary);
}

/* Translation header */
.etymology-translation {
    margin: 0 0 var(--spacing-md) 0;
    padding-right: var(--spacing-lg);
    font-size: var(--font-size-md);
    font-style: italic;
    font-weight: 500;
    color: var(--color-text-primary);
}

/* Breakdown list */
.etymology-breakdown {
    list-style: none;
    margin: 0;
    padding: 0;
}

.etymology-breakdown li {
    position: relative;
    padding-left: var(--spacing-lg);
    margin-bottom: var(--spacing-sm);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
    line-height: 1.5;
}

.etymology-breakdown li::before {
    content: '';
    position: absolute;
    left: 0;
    top: 8px;
    width: 6px;
    height: 6px;
    background: linear-gradient(135deg, var(--color-primary-gradient-start), var(--color-primary-gradient-end));
    border-radius: 50%;
}

/* Cultural note */
.etymology-note {
    margin: 0;
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-primary-overlay);
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    line-height: 1.6;
    font-style: italic;
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
    background: var(--color-overlay-subtle);
    color: var(--color-text-secondary);
    border: 1px solid var(--color-primary-overlay);
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
    background: var(--color-primary-overlay);
    border-color: var(--color-primary-glow);
    box-shadow: 0 2px 8px var(--color-primary-overlay);
}

.nav-item:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.nav-icon {
    font-size: var(--font-size-base);
    display: inline-block;
}

/* Instructor item styling */
.instructor-item {
    background: var(--color-primary);
    color: var(--color-text-primary);
    border-color: transparent;
    box-shadow: 0 2px 8px var(--color-info-shadow);
}

.instructor-item:hover {
    background: var(--color-primary-hover);
    border-color: transparent;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.5);
}

.instructor-item.router-link-active {
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.6);
}

/* Admin item styling */
.admin-item {
    background: var(--color-admin);
    color: var(--color-text-primary);
    border-color: transparent;
    box-shadow: 0 2px 8px var(--color-admin-shadow);
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

    /* Smaller etymology panel on tablets */
    .etymology-panel {
        min-width: 240px;
        max-width: 280px;
        padding: var(--spacing-sm) var(--spacing-md);
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

    .etymology-panel {
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
