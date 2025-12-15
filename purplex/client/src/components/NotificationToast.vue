<template>
  <Teleport to="body">
    <TransitionGroup
      name="notification"
      tag="div"
      class="notification-container"
    >
      <div
        v-for="notification in notifications"
        :key="notification.id"
        :class="['notification', notification.type]"
        @click="removeNotification(notification.id)"
      >
        <span class="notification-icon">{{ getIcon(notification.type) }}</span>
        <div class="notification-content">
          <p class="notification-message">
            {{ notification.message }}
          </p>
          <p
            v-if="notification.details"
            class="notification-details"
          >
            {{ notification.details }}
          </p>
        </div>
        <button
          class="notification-close"
          @click.stop="removeNotification(notification.id)"
        >
          ×
        </button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import type { NotificationPayload, NotificationType } from '@/types'

interface Notification extends NotificationPayload {
  id: number
}

export default defineComponent({
  name: 'NotificationToast',
  data(): {
    notifications: Notification[]
  } {
    return {
      notifications: []
    };
  },
  mounted() {
    // Make this component globally accessible
    window.$notify = this.addNotification.bind(this);
  },
  beforeUnmount() {
    delete window.$notify;
  },
  methods: {
    addNotification(notification: NotificationPayload): void {
      const id = Date.now();
      this.notifications.push({
        id,
        ...notification
      });

      // Auto-remove after duration
      setTimeout(() => {
        this.removeNotification(id);
      }, notification.duration || 5000);
    },
    removeNotification(id: number): void {
      const index = this.notifications.findIndex(n => n.id === id);
      if (index > -1) {
        this.notifications.splice(index, 1);
      }
    },
    getIcon(type: NotificationType): string {
      const icons = {
        success: '✓',
        error: '⚠️',
        warning: '⚡',
        info: 'ℹ️'
      };
      return icons[type] || 'ℹ️';
    }
  }
});
</script>

<style scoped>
.notification-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  max-width: 400px;
}

.notification {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-lg);
  border-left: 4px solid;
  cursor: pointer;
  transition: var(--transition-base);
}

.notification:hover {
  transform: translateX(-5px);
  box-shadow: var(--shadow-xl);
}

.notification.success {
  border-left-color: var(--color-success);
}

.notification.error {
  border-left-color: var(--color-error);
}

.notification.warning {
  border-left-color: var(--color-warning);
}

.notification.info {
  border-left-color: var(--color-info);
}

.notification-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.notification-content {
  flex: 1;
}

.notification-message {
  margin: 0;
  color: var(--color-text-primary);
  font-weight: 600;
  font-size: var(--font-size-sm);
}

.notification-details {
  margin: var(--spacing-xs) 0 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.notification-close {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-circle);
  transition: var(--transition-fast);
}

.notification-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

/* Transitions */
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.notification-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.notification-move {
  transition: transform 0.3s ease;
}

/* Mobile */
@media (max-width: 768px) {
  .notification-container {
    left: 10px;
    right: 10px;
    max-width: none;
  }
}
</style>
