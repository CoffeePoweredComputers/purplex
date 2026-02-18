<template>
  <div class="privacy-settings">
    <h2 class="privacy-settings__title">Privacy & Data Settings</h2>

    <!-- Consent Management -->
    <section class="privacy-settings__section">
      <h3 class="privacy-settings__section-title">Consent Preferences</h3>
      <p class="privacy-settings__section-desc">
        Manage your data processing preferences. Required consents cannot be withdrawn
        without deleting your account.
      </p>

      <div v-if="loadingConsents" class="privacy-settings__loading">Loading...</div>

      <div v-else class="consent-toggles">
        <div
          v-for="(status, type) in consents"
          :key="type"
          class="consent-toggle"
        >
          <div class="consent-toggle__info">
            <span class="consent-toggle__label">{{ consentLabels[type] || type }}</span>
            <span v-if="isRequired(type)" class="consent-toggle__required">Required</span>
          </div>
          <label class="consent-toggle__switch">
            <input
              type="checkbox"
              :checked="status.granted"
              :disabled="isRequired(type)"
              @change="toggleConsent(type, $event)"
            >
            <span class="consent-toggle__slider"></span>
          </label>
        </div>
      </div>
    </section>

    <!-- FERPA Directory Info -->
    <section class="privacy-settings__section">
      <h3 class="privacy-settings__section-title">Directory Information</h3>
      <p class="privacy-settings__section-desc">
        Control whether your name and email are visible to instructors in course rosters.
      </p>
      <label class="consent-toggle">
        <div class="consent-toggle__info">
          <span class="consent-toggle__label">Show my name and email in course rosters</span>
        </div>
        <label class="consent-toggle__switch">
          <input
            type="checkbox"
            v-model="directoryInfoVisible"
            @change="updateDirectoryInfo"
          >
          <span class="consent-toggle__slider"></span>
        </label>
      </label>
    </section>

    <!-- Data Export -->
    <section class="privacy-settings__section">
      <DataExport />
    </section>

    <!-- Account Deletion -->
    <section class="privacy-settings__section privacy-settings__section--danger">
      <AccountDeletion />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import privacyService, { type ConsentType, type ConsentStatus } from '../../services/privacyService';
import DataExport from './DataExport.vue';
import AccountDeletion from './AccountDeletion.vue';

const consents = ref<Record<ConsentType, ConsentStatus>>({} as Record<ConsentType, ConsentStatus>);
const loadingConsents = ref(true);
const directoryInfoVisible = ref(true);

const consentLabels: Record<string, string> = {
    privacy_policy: 'Privacy Policy',
    terms_of_service: 'Terms of Service',
    ai_processing: 'AI Code Analysis',
    third_party_sharing: 'Third-Party Data Sharing',
    research_use: 'Research Data Use',
    behavioral_tracking: 'Progress Tracking',
};

const requiredTypes = ['privacy_policy', 'terms_of_service'];

function isRequired(type: string): boolean {
    return requiredTypes.includes(type);
}

onMounted(async () => {
    try {
        consents.value = await privacyService.getConsents();
    } catch {
        // Consent data unavailable
    } finally {
        loadingConsents.value = false;
    }
});

async function toggleConsent(type: string, event: Event) {
    const target = event.target as HTMLInputElement;
    const granted = target.checked;

    try {
        if (granted) {
            await privacyService.grantConsent(type as ConsentType);
        } else {
            await privacyService.withdrawConsent(type as ConsentType);
        }
        // Refresh consent state
        consents.value = await privacyService.getConsents();
    } catch {
        // Revert on failure
        target.checked = !granted;
    }
}

async function updateDirectoryInfo() {
    try {
        const result = await privacyService.updateDirectoryInfoVisibility(
            directoryInfoVisible.value
        );
        directoryInfoVisible.value = result.directory_info_visible;
    } catch {
        directoryInfoVisible.value = !directoryInfoVisible.value;
    }
}
</script>

<style scoped>
.privacy-settings {
    max-width: 700px;
    margin: var(--spacing-xl) auto;
    padding: 0 var(--spacing-base);
}

.privacy-settings__title {
    margin: 0 0 var(--spacing-xl);
    font-size: var(--font-size-lg);
    color: var(--color-text-primary);
}

.privacy-settings__section {
    margin-bottom: var(--spacing-xl);
}

.privacy-settings__section--danger {
    padding-top: var(--spacing-base);
    border-top: 1px solid rgba(220, 53, 69, 0.3);
}

.privacy-settings__section-title {
    margin: 0 0 var(--spacing-xs);
    font-size: var(--font-size-md);
    color: var(--color-text-primary);
}

.privacy-settings__section-desc {
    margin: 0 0 var(--spacing-base);
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.privacy-settings__loading {
    padding: var(--spacing-base);
    color: var(--color-text-muted);
}

.consent-toggles {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
}

.consent-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-base);
    background: var(--color-bg-panel);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-bg-border);
    transition: var(--transition-fast);
}

.consent-toggle:hover {
    background: var(--color-bg-hover);
}

.consent-toggle__info {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.consent-toggle__label {
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
}

.consent-toggle__required {
    font-size: var(--font-size-xs);
    padding: 2px var(--spacing-xs);
    background: rgba(102, 126, 234, 0.15);
    color: var(--color-primary-gradient-start);
    border-radius: var(--radius-xs);
    font-weight: 600;
}

.consent-toggle__switch {
    position: relative;
    width: 44px;
    height: 24px;
    cursor: pointer;
    flex-shrink: 0;
}

.consent-toggle__switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.consent-toggle__slider {
    position: absolute;
    inset: 0;
    background: var(--color-bg-border);
    border-radius: var(--radius-round);
    transition: var(--transition-fast);
}

.consent-toggle__slider::before {
    content: '';
    position: absolute;
    width: 18px;
    height: 18px;
    left: 3px;
    bottom: 3px;
    background: var(--color-text-primary);
    border-radius: var(--radius-circle);
    transition: var(--transition-fast);
}

.consent-toggle__switch input:checked + .consent-toggle__slider {
    background: var(--color-primary-gradient-start);
}

.consent-toggle__switch input:checked + .consent-toggle__slider::before {
    transform: translateX(20px);
}

.consent-toggle__switch input:disabled + .consent-toggle__slider {
    opacity: 0.5;
    cursor: not-allowed;
}

.consent-toggle__switch input:focus-visible + .consent-toggle__slider {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}
</style>
