<template>
  <div
    class="locked-segmentation-banner"
  >
    <div class="banner-content">
      <div class="banner-main">
        <div class="progress-section">
          <span class="lock-icon">
            🔒
          </span>
        </div>
        <div class="banner-message">
          <span class="level-text">Comprehension Analysis Locked</span>
          <span class="separator">•</span>
          <span class="description-text">Complete all test cases first</span>
        </div>
      </div>
      <button
        class="analyze-button disabled"
        aria-label="View detailed analysis - disabled until all tests pass"
        title="Complete all test cases to unlock"
        disabled
      >
        <span class="button-icon">›</span>
      </button>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'LockedSegmentationBanner',
});
</script>

<style scoped>
.locked-segmentation-banner {
  margin: var(--spacing-sm) 0;
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: var(--transition-fast);
  opacity: 0.7;
  border-left: 3px solid var(--color-bg-border);
}

.banner-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  gap: var(--spacing-md);
  min-height: 36px;
}

.banner-main {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.progress-section {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.lock-icon {
  font-size: 24px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-circle);
  background: var(--color-bg-input);
  opacity: 0.6;
}

.banner-message {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  line-height: 1.2;
  padding: 0 var(--spacing-xs);
}

.level-text {
  font-weight: 600;
  color: var(--color-text-secondary);
}

.separator {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.description-text {
  color: var(--color-text-muted);
}

.analyze-button {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-muted);
  cursor: not-allowed;
  transition: var(--transition-fast);
  margin-left: var(--spacing-sm);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  opacity: 0.5;
}

.analyze-button.disabled {
  pointer-events: none;
}

.button-icon {
  font-size: var(--font-size-lg);
  line-height: 1;
  font-weight: 700;
  opacity: 0.4;
}

/* Responsive */
@media (max-width: 768px) {
  .banner-content {
    flex-direction: column;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
  }

  .banner-main {
    width: 100%;
    flex-wrap: wrap;
  }

  .lock-icon {
    font-size: 20px;
    width: 28px;
    height: 28px;
  }

  .banner-message {
    width: 100%;
    order: 2;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .analyze-button {
    width: 32px;
    height: 32px;
  }
}
</style>
