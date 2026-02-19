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
    padding: var(--spacing-xl);
    background: var(--color-bg-panel);
    border-radius: var(--radius-base);
    border: 1px solid var(--color-bg-border);
    box-shadow: var(--shadow-base);
}

.age-gate__title {
    margin: 0 0 var(--spacing-sm);
    font-size: var(--font-size-md);
    color: var(--color-text-primary);
}

.age-gate__description {
    margin: 0 0 var(--spacing-base);
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
}

.age-gate__form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-base);
}

.age-gate__label {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    font-size: var(--font-size-sm);
    color: var(--color-text-secondary);
}

.age-gate__input {
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-bg-border);
    border-radius: var(--radius-xs);
    background: var(--color-bg-input);
    color: var(--color-text-primary);
    transition: var(--transition-fast);
}

.age-gate__input:focus {
    outline: none;
    border-color: var(--color-primary-gradient-start);
}

.age-gate__message {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    padding: var(--spacing-sm);
    border-radius: var(--radius-xs);
    background: var(--color-info-bg);
}

.age-gate__message--warning {
    color: var(--color-warning-text);
    background: var(--color-warning-bg);
    border: 1px solid rgba(255, 193, 7, 0.3);
}

.age-gate__error {
    color: var(--color-error);
    font-size: var(--font-size-sm);
}

.age-gate__submit {
    padding: var(--spacing-md);
    background: linear-gradient(135deg, var(--color-primary-gradient-start), var(--color-primary-gradient-end));
    color: var(--color-text-primary);
    border: none;
    border-radius: var(--radius-sm);
    font-size: var(--font-size-base);
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-fast);
}

.age-gate__submit:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-colored);
}

.age-gate__submit:focus-visible {
    outline: 2px solid var(--color-primary-gradient-start);
    outline-offset: 2px;
}

.age-gate__submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}
</style>
