<template>
  <div class="age-gate">
    <h3 class="age-gate__title">Age Verification</h3>
    <p class="age-gate__description">
      We need to verify your age to comply with data protection regulations.
      This information is used to determine applicable privacy protections.
    </p>

    <div class="age-gate__form">
      <label class="age-gate__label">
        Date of Birth
        <input
          type="date"
          v-model="dateOfBirth"
          :max="today"
          class="age-gate__input"
          required
        >
      </label>

      <p v-if="ageMessage" class="age-gate__message" :class="{ 'age-gate__message--warning': isMinor }">
        {{ ageMessage }}
      </p>

      <p v-if="error" class="age-gate__error" role="alert">{{ error }}</p>

      <button
        class="age-gate__submit"
        :disabled="!dateOfBirth"
        @click="submitAge"
      >
        Continue
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const emit = defineEmits<{
    (e: 'age-verified', data: { date_of_birth: string; is_minor: boolean; is_child: boolean }): void;
    (e: 'under-age', data: { is_child: boolean }): void;
}>();

const dateOfBirth = ref('');
const error = ref('');
const today = new Date().toISOString().split('T')[0];

const age = computed(() => {
    if (!dateOfBirth.value) return null;
    const birth = new Date(dateOfBirth.value);
    const now = new Date();
    let years = now.getFullYear() - birth.getFullYear();
    const monthDiff = now.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < birth.getDate())) {
        years--;
    }
    return years;
});

const isMinor = computed(() => age.value !== null && age.value < 18);
const isChild = computed(() => age.value !== null && age.value < 13);

const ageMessage = computed(() => {
    if (age.value === null) return '';
    if (isChild.value) {
        return 'Users under 13 require parental or guardian consent (COPPA). A parent or guardian must approve your account.';
    }
    if (isMinor.value) {
        return 'Users under 18 have additional privacy protections. Some features may require parental consent.';
    }
    return '';
});

function submitAge() {
    if (!dateOfBirth.value) {
        error.value = 'Please enter your date of birth.';
        return;
    }

    error.value = '';
    const data = {
        date_of_birth: dateOfBirth.value,
        is_minor: isMinor.value,
        is_child: isChild.value,
    };

    if (isChild.value) {
        emit('under-age', { is_child: true });
    } else {
        emit('age-verified', data);
    }
}
</script>

<style scoped>
.age-gate {
    max-width: 400px;
    margin: 0 auto;
    padding: 1.5rem;
    background: var(--card-bg, #1e1e2e);
    border-radius: 8px;
    border: 1px solid var(--border-color, #333);
}

.age-gate__title {
    margin: 0 0 0.5rem;
    font-size: 1.2rem;
    color: var(--text-primary, #e0e0e0);
}

.age-gate__description {
    margin: 0 0 1rem;
    font-size: 0.85rem;
    color: var(--text-secondary, #999);
}

.age-gate__form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.age-gate__label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.9rem;
    color: var(--text-primary, #e0e0e0);
}

.age-gate__input {
    padding: 0.5rem;
    border: 1px solid var(--border-color, #333);
    border-radius: 4px;
    background: var(--input-bg, #2a2a3e);
    color: var(--text-primary, #e0e0e0);
}

.age-gate__message {
    font-size: 0.85rem;
    color: var(--text-secondary, #999);
    padding: 0.5rem;
    border-radius: 4px;
    background: var(--info-bg, #1a1a2e);
}

.age-gate__message--warning {
    color: var(--warning-color, #f39c12);
    background: rgba(243, 156, 18, 0.1);
    border: 1px solid rgba(243, 156, 18, 0.3);
}

.age-gate__error {
    color: var(--error-color, #e74c3c);
    font-size: 0.85rem;
}

.age-gate__submit {
    padding: 0.75rem;
    background: var(--primary-gradient, linear-gradient(135deg, #9b59b6, #6c3483));
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity 0.2s;
}

.age-gate__submit:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
</style>
