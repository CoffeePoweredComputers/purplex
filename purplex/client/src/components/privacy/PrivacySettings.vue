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
    margin: 2rem auto;
    padding: 0 1rem;
}

.privacy-settings__title {
    margin: 0 0 1.5rem;
    font-size: 1.5rem;
    color: var(--text-primary, #e0e0e0);
}

.privacy-settings__section {
    margin-bottom: 2rem;
}

.privacy-settings__section--danger {
    padding-top: 1rem;
    border-top: 1px solid rgba(231, 76, 60, 0.3);
}

.privacy-settings__section-title {
    margin: 0 0 0.3rem;
    font-size: 1.1rem;
    color: var(--text-primary, #e0e0e0);
}

.privacy-settings__section-desc {
    margin: 0 0 1rem;
    font-size: 0.85rem;
    color: var(--text-secondary, #999);
}

.privacy-settings__loading {
    padding: 1rem;
    color: var(--text-secondary, #999);
}

.consent-toggles {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.consent-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: var(--card-bg, #1e1e2e);
    border-radius: 6px;
    border: 1px solid var(--border-color, #333);
}

.consent-toggle__info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.consent-toggle__label {
    font-size: 0.9rem;
    color: var(--text-primary, #e0e0e0);
}

.consent-toggle__required {
    font-size: 0.7rem;
    padding: 0.15rem 0.4rem;
    background: rgba(155, 89, 182, 0.2);
    color: var(--link-color, #9b59b6);
    border-radius: 3px;
}

.consent-toggle__switch {
    position: relative;
    width: 44px;
    height: 24px;
    cursor: pointer;
}

.consent-toggle__switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.consent-toggle__slider {
    position: absolute;
    inset: 0;
    background: var(--border-color, #333);
    border-radius: 24px;
    transition: background 0.2s;
}

.consent-toggle__slider::before {
    content: '';
    position: absolute;
    width: 18px;
    height: 18px;
    left: 3px;
    bottom: 3px;
    background: white;
    border-radius: 50%;
    transition: transform 0.2s;
}

.consent-toggle__switch input:checked + .consent-toggle__slider {
    background: var(--link-color, #9b59b6);
}

.consent-toggle__switch input:checked + .consent-toggle__slider::before {
    transform: translateX(20px);
}

.consent-toggle__switch input:disabled + .consent-toggle__slider {
    opacity: 0.5;
    cursor: not-allowed;
}
</style>
