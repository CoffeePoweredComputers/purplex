<template>
  <div class="content-editor-layout">
    <!-- Dynamic NavBar based on role -->
    <component :is="navComponent" />

    <main
      id="main-content"
      class="content-container"
    >
      <!-- Breadcrumb navigation -->
      <nav
        v-if="showBreadcrumb"
        class="breadcrumb border-default"
      >
        <router-link
          :to="backPath"
          class="breadcrumb-link transition-fast"
        >
          ← {{ backLabel }}
        </router-link>
      </nav>

      <!-- Page header with title and actions -->
      <header
        v-if="showHeader"
        class="page-header"
      >
        <h1 class="page-title">
          {{ pageTitle }}
        </h1>
        <div class="header-actions">
          <slot name="header-actions" />
        </div>
      </header>

      <!-- Main content slot -->
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { type Component, computed, markRaw } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  type ContentContext,
  provideContentContext,
  useContentContextOptional
} from '@/composables/useContentContext';
import AdminNavBar from '@/components/AdminNavBar.vue';
import InstructorNavBar from '@/components/instructor/InstructorNavBar.vue';

const props = withDefaults(defineProps<{
  /** Path for the back link. Defaults to role-appropriate problems list. */
  backPath?: string;
  /** Label for the back link */
  backLabel?: string;
  /** Page title to display */
  pageTitle?: string;
  /** Whether to show the breadcrumb navigation */
  showBreadcrumb?: boolean;
  /** Whether to show the page header */
  showHeader?: boolean;
}>(), {
  backPath: '',
  backLabel: '',
  pageTitle: '',
  showBreadcrumb: true,
  showHeader: true,
});

const { t } = useI18n();

// Use existing context if parent provided it, otherwise provide our own
// (Page-level components should call provideContentContext() before rendering this)
const ctx: ContentContext = useContentContextOptional() ?? provideContentContext();

// Select navbar based on role
const navComponent = computed<Component>(() => {
  return ctx.role.value === 'admin'
    ? markRaw(AdminNavBar)
    : markRaw(InstructorNavBar);
});

// Default back path based on role
const backPath = computed(() => {
  if (props.backPath) {
    return props.backPath;
  }
  return ctx.paths.problems.value;
});

// Default back label based on role
const backLabel = computed(() => {
  if (props.backLabel) {
    return props.backLabel;
  }
  return ctx.isInstructor.value ? t('admin.contentLayout.backToMyProblems') : t('admin.contentLayout.backToProblems');
});

// Page title with role awareness
const pageTitle = computed(() => {
  return props.pageTitle ?? t('admin.contentLayout.contentManagement');
});

// Expose context for parent component if needed
defineExpose({ ctx });
</script>

<style scoped>
.content-editor-layout {
  min-height: 100vh;
  background: var(--color-bg-page, var(--color-bg-base));
}

.content-container {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-lg);
}

/* Breadcrumb Navigation */
.breadcrumb {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md) 0;
  border-bottom: 2px solid var(--color-bg-border);
}

.breadcrumb-link {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-text-muted);
  text-decoration: none;
  font-weight: 500;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-xs);
}

.breadcrumb-link:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.breadcrumb-link:focus-visible {
  outline: 2px solid var(--color-primary-gradient-start);
  outline-offset: 2px;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: var(--spacing-md);
}

/* Utility classes */
.border-default {
  border-color: var(--color-bg-border);
}

.transition-fast {
  transition: var(--transition-fast);
}

/* Responsive */
@media (width <= 768px) {
  .content-container {
    padding: var(--spacing-md);
  }

  .page-header {
    flex-direction: column;
    gap: var(--spacing-md);
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
