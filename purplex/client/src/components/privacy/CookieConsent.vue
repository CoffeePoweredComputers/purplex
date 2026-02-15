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
    background: var(--card-bg, #1e1e2e);
    border-top: 1px solid var(--border-color, #333);
    padding: 1rem 1.5rem;
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.3);
}

.cookie-consent__content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    flex-wrap: wrap;
}

.cookie-consent__text {
    margin: 0;
    font-size: 0.85rem;
    color: var(--text-secondary, #999);
    flex: 1;
    min-width: 250px;
}

.cookie-consent__link {
    color: var(--link-color, #9b59b6);
}

.cookie-consent__actions {
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
}

.cookie-consent__btn {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    font-size: 0.85rem;
    cursor: pointer;
    border: 1px solid var(--border-color, #333);
    transition: background 0.2s;
}

.cookie-consent__btn--essential {
    background: transparent;
    color: var(--text-primary, #e0e0e0);
}

.cookie-consent__btn--essential:hover {
    background: rgba(255, 255, 255, 0.05);
}

.cookie-consent__btn--accept {
    background: var(--primary-gradient, linear-gradient(135deg, #9b59b6, #6c3483));
    color: white;
    border-color: transparent;
}
</style>
