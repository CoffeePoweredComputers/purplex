<template>
  <div v-if="showBanner" class="cookie-consent" role="dialog" aria-label="Cookie consent">
    <div class="cookie-consent__content">
      <p class="cookie-consent__text">
        We use essential cookies for site functionality. Optional cookies help us improve the experience.
        <a href="/privacy" class="cookie-consent__link">Learn more</a>
      </p>
      <div class="cookie-consent__actions">
        <button
          class="cookie-consent__btn cookie-consent__btn--essential"
          @click="acceptEssential"
        >
          Essential Only
        </button>
        <button
          class="cookie-consent__btn cookie-consent__btn--accept"
          @click="acceptAll"
        >
          Accept All
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const COOKIE_CONSENT_KEY = 'purplex_cookie_consent';

const showBanner = ref(false);

onMounted(() => {
    const stored = localStorage.getItem(COOKIE_CONSENT_KEY);
    if (!stored) {
        showBanner.value = true;
    }
});

function acceptEssential() {
    localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
        essential: true,
        analytics: false,
        timestamp: new Date().toISOString(),
    }));
    showBanner.value = false;
}

function acceptAll() {
    localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({
        essential: true,
        analytics: true,
        timestamp: new Date().toISOString(),
    }));
    showBanner.value = false;
}
</script>

<style scoped>
.cookie-consent {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background: var(--color-bg-header);
    border-top: 1px solid var(--color-bg-border);
    padding: var(--spacing-base) var(--spacing-xl);
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.3);
}

.cookie-consent__content {
    max-width: var(--max-width-content);
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-xl);
    flex-wrap: wrap;
}

.cookie-consent__text {
    margin: 0;
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    flex: 1;
    min-width: 250px;
}

.cookie-consent__link {
    color: var(--color-primary-gradient-start);
}

.cookie-consent__link:hover {
    color: var(--color-primary-gradient-end);
}

.cookie-consent__actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-shrink: 0;
}

.cookie-consent__btn {
    padding: var(--spacing-sm) var(--spacing-base);
    border-radius: var(--radius-xs);
    font-size: var(--font-size-sm);
    font-weight: 500;
    cursor: pointer;
    border: 1px solid var(--color-bg-border);
    transition: var(--transition-fast);
}

.cookie-consent__btn:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.cookie-consent__btn--essential {
    background: transparent;
    color: var(--color-text-secondary);
}

.cookie-consent__btn--essential:hover {
    background: var(--color-bg-hover);
    border-color: var(--color-primary-gradient-start);
}

.cookie-consent__btn--accept {
    background: linear-gradient(135deg, var(--color-primary-gradient-start), var(--color-primary-gradient-end));
    color: var(--color-text-primary);
    border-color: transparent;
}

.cookie-consent__btn--accept:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-colored);
}

@media (max-width: 768px) {
    .cookie-consent__content {
        flex-direction: column;
        gap: var(--spacing-md);
        text-align: center;
    }

    .cookie-consent__actions {
        width: 100%;
        justify-content: center;
    }
}
</style>
