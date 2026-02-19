<template>
  <Teleport to="body">
    <div
      v-if="isVisible"
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="account-modal-title"
      @click.self="closeModal"
    >
      <div
        ref="modalContentRef"
        class="modal-content"
        @keydown.esc="closeModal"
      >
        <div class="modal-header">
          <h3
            id="account-modal-title"
            class="modal-title"
          >
            Account Settings
          </h3>
          <button
            class="close-button"
            @click="closeModal"
          >
            &times;
          </button>
        </div>

        <div class="user-profile">
          <div class="avatar">
            {{ getInitials() }}
          </div>
          <div class="user-info">
            <h4 class="user-name">
              {{ store.state.auth.user.name || 'User' }}
            </h4>
            <p class="user-email">
              {{ store.state.auth.user.email }}
            </p>
          </div>
        </div>

        <div class="info-section">
          <div class="info-item">
            <span class="info-label">Account Type</span>
            <span
              class="role-badge"
              :class="store.state.auth.user.role"
            >
              {{ store.state.auth.user.role }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">Member Since</span>
            <span class="info-value">{{ getMemberSince() }}</span>
          </div>

          <LanguageSwitcher />

          <div class="info-item info-item--link" @click="goToPrivacySettings">
            <span class="info-label">Privacy Settings</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </div>
        </div>

        <div class="modal-footer">
          <button
            class="logout-button"
            @click="logout"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line
                x1="21"
                y1="12"
                x2="9"
                y2="12"
              />
            </svg>
            Sign Out
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { toRef } from 'vue'
import { useStore } from 'vuex'
import { useRouter } from 'vue-router'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'
import { useFocusTrap } from '@/composables/useFocusTrap'

const props = defineProps<{
  isVisible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const store = useStore()
const router = useRouter()

// Focus trap composable
const { modalContentRef } = useFocusTrap(toRef(() => props.isVisible))

function logout(): void {
  store.dispatch('auth/logout')
}

function closeModal(): void {
  emit('close')
}

function goToPrivacySettings(): void {
  closeModal()
  router.push({ name: 'PrivacySettings' })
}

function getInitials(): string {
  const name = store.state.auth.user.name || store.state.auth.user.email || 'User'
  return name.split(' ').map((word: string) => word[0]).join('').toUpperCase().slice(0, 2)
}

function getMemberSince(): string {
  return new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
}
</script>

<style scoped>
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}

.modal-content {
    background: var(--color-bg-panel);
    border-radius: calc(var(--radius-lg) + 4px);
    overflow: hidden;
    max-width: 400px;
    width: 90%;
    box-shadow: var(--shadow-lg);
    border: 2px solid var(--color-bg-input);
    animation: slideUp 0.3s ease;
}

@keyframes slideUp {
    from {
        transform: translateY(20px);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--color-bg-hover);
    padding: var(--spacing-lg) var(--spacing-xl);
    border-bottom: 2px solid var(--color-bg-input);
}

.modal-title {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}


.close-button {
    background: var(--color-bg-input);
    border: none;
    color: var(--color-text-primary);
    width: 36px;
    height: 36px;
    border-radius: var(--radius-circle);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: var(--transition-base);
}

.close-button:hover {
    background: var(--color-bg-border);
    color: var(--color-text-primary);
}

.close-button svg {
    pointer-events: none;
}

/* User Profile Section */
.user-profile {
    display: flex;
    align-items: center;
    gap: var(--spacing-lg);
    padding: var(--spacing-xl);
    background: var(--color-bg-panel);
    border-bottom: 1px solid var(--color-bg-input);
}

.avatar {
    width: 64px;
    height: 64px;
    background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
    border-radius: var(--radius-circle);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--color-text-primary);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.user-info {
    flex: 1;
}

.user-name {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--color-text-primary);
    margin: 0 0 var(--spacing-xs) 0;
}

.user-email {
    font-size: var(--font-size-sm);
    color: var(--color-text-muted);
    margin: 0;
}

/* Info Section */
.info-section {
    padding: var(--spacing-xl);
    background: var(--color-bg-panel);
}

.info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-md) 0;
    border-bottom: 1px solid var(--color-bg-hover);
}

.info-item:last-child {
    border-bottom: none;
}

.info-item--link {
    cursor: pointer;
    border-radius: var(--radius-base);
    margin: 0 calc(-1 * var(--spacing-sm));
    padding: var(--spacing-md) var(--spacing-sm);
    transition: var(--transition-base);
}

.info-item--link:hover {
    background: var(--color-bg-hover);
}

.info-item--link svg {
    color: var(--color-text-muted);
    transition: var(--transition-base);
}

.info-item--link:hover svg {
    color: var(--color-text-secondary);
    transform: translateX(2px);
}

.info-label {
    font-size: var(--font-size-base);
    color: var(--color-text-muted);
}

.info-value {
    font-size: var(--font-size-base);
    color: var(--color-text-secondary);
}

.role-badge {
    padding: var(--spacing-xs) var(--spacing-md);
    border-radius: var(--radius-xl);
    font-size: var(--font-size-xs);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.role-badge.admin {
    background: linear-gradient(135deg, var(--color-admin) 0%, var(--color-admin-hover) 100%);
    color: var(--color-text-primary);
    box-shadow: 0 2px 8px rgba(103, 58, 183, 0.3);
}

.role-badge.user {
    background: var(--color-bg-hover);
    color: var(--color-text-tertiary);
    border: 1px solid var(--color-bg-border);
}

.modal-footer {
    padding: var(--spacing-lg) var(--spacing-xl) var(--spacing-xl);
    background: var(--color-bg-hover);
    border-top: 1px solid var(--color-bg-input);
    display: flex;
    justify-content: center;
}


.logout-button {
    background: var(--color-error-bg);
    border: 1px solid var(--color-error);
    border-radius: var(--radius-base);
    padding: var(--spacing-md) var(--spacing-xl);
    color: var(--color-error);
    font-size: var(--font-size-base);
    font-weight: 600;
    cursor: pointer;
    transition: var(--transition-base);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-sm);
    min-width: 140px;
}

.logout-button:hover {
    background: var(--color-error);
    color: var(--color-text-primary);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
}

.logout-button svg {
    width: 16px;
    height: 16px;
}

/* Responsive Design */
@media (max-width: 768px) {
    .modal-content {
        max-width: 95%;
    }

    .modal-header {
        padding: var(--spacing-md) var(--spacing-lg);
    }

    .modal-title {
        font-size: var(--font-size-md);
    }

    .user-profile {
        padding: var(--spacing-lg);
    }

    .avatar {
        width: 56px;
        height: 56px;
        font-size: var(--font-size-lg);
    }

    .user-name {
        font-size: var(--font-size-base);
    }

    .info-section {
        padding: var(--spacing-lg);
    }

    .modal-footer {
        padding: var(--spacing-lg);
    }

    .logout-button {
        width: 100%;
    }
}
</style>
