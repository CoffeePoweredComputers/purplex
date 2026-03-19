<template>
  <a href="#main-content" class="skip-link">{{ $t('admin.instructorNav.skipToContent') }}</a>
  <nav class="instructor-nav" role="navigation" aria-label="Instructor navigation">
    <div class="instructor-nav-container">
      <ul class="instructor-nav-list">
        <li>
          <router-link
            to="/instructor"
            class="instructor-link"
            :class="{ 'router-link-active': isExactDashboard }"
            :aria-current="isExactDashboard ? 'page' : undefined"
          >
            <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zm8 0A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm-8 8A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm8 0A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3z"/>
            </svg>
            {{ $t('admin.instructorNav.myCourses') }}
          </router-link>
        </li>
        <template v-if="!courseId">
          <li>
            <router-link
              to="/instructor/problems"
              class="instructor-link"
              :aria-current="isActiveRoute('/instructor/problems') ? 'page' : undefined"
            >
              <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M2 2a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2zm4 1h4a1 1 0 0 0 0-2H6a1 1 0 0 0 0 2zm0 3h4a1 1 0 0 0 0-2H6a1 1 0 0 0 0 2zm0 3h4a1 1 0 0 0 0-2H6a1 1 0 0 0 0 2zm0 3h4a1 1 0 0 0 0-2H6a1 1 0 0 0 0 2z"/>
              </svg>
              {{ $t('admin.instructorNav.myProblems') }}
            </router-link>
          </li>
          <li>
            <router-link
              to="/instructor/problem-sets"
              class="instructor-link"
              :aria-current="isActiveRoute('/instructor/problem-sets') ? 'page' : undefined"
            >
              <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm4 1v2h8V3H4zm8 3H4v2h8V6zm0 3H4v2h8V9zm-8 3v2h4v-2H4z"/>
              </svg>
              {{ $t('admin.instructorNav.problemSets') }}
            </router-link>
          </li>
        </template>
        <template v-if="courseId">
          <li>
            <router-link
              :to="`/instructor/courses/${courseId}`"
              class="instructor-link"
              :aria-current="isActiveRoute(`/instructor/courses/${courseId}`) ? 'page' : undefined"
            >
              <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M4 11H2v3h2v-3zm5-4H7v7h2V7zm5-5h-2v12h2V2zm-2-1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h2a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1h-2zM6 7a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7zm-5 4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1v-3z"/>
              </svg>
              {{ $t('admin.instructorNav.overview') }}
            </router-link>
          </li>
          <li>
            <router-link
              :to="`/instructor/courses/${courseId}/students`"
              class="instructor-link"
              :aria-current="isActiveRoute(`/instructor/courses/${courseId}/students`) ? 'page' : undefined"
            >
              <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M7 14s-1 0-1-1 1-4 5-4 5 3 5 4-1 1-1 1H7zm4-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
                <path fill-rule="evenodd" d="M5.216 14A2.238 2.238 0 0 1 5 13c0-1.355.68-2.75 1.936-3.72A6.325 6.325 0 0 0 5 9c-4 0-5 3-5 4s1 1 1 1h4.216z"/>
                <path d="M4.5 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z"/>
              </svg>
              {{ $t('admin.instructorNav.students') }}
            </router-link>
          </li>
          <li>
            <router-link
              :to="`/instructor/courses/${courseId}/submissions`"
              class="instructor-link"
              :aria-current="isActiveRoute(`/instructor/courses/${courseId}/submissions`) ? 'page' : undefined"
            >
              <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M5.523 12.424c.14-.082.293-.162.459-.238a7.878 7.878 0 0 1-.45.606c-.28.337-.498.516-.635.572a.266.266 0 0 1-.035.012.282.282 0 0 1-.026-.044c-.056-.11-.054-.216.04-.36.106-.165.319-.354.647-.548zm2.455-1.647c-.119.025-.237.05-.356.078a21.148 21.148 0 0 0 .5-1.05 12.045 12.045 0 0 0 .51.858c-.217.032-.436.07-.654.114zm2.525.939a3.881 3.881 0 0 1-.435-.41c.228.005.434.022.612.054.317.057.466.147.518.209a.095.095 0 0 1 .026.064.436.436 0 0 1-.06.2.307.307 0 0 1-.094.124.107.107 0 0 1-.069.015c-.09-.003-.258-.066-.498-.256zM8.278 6.97c-.04.244-.108.524-.2.829a4.86 4.86 0 0 1-.089-.346c-.076-.353-.087-.63-.046-.822.038-.177.11-.248.196-.283a.517.517 0 0 1 .145-.04c.013.03.028.092.032.198.005.122-.007.277-.038.465z"/>
                <path fill-rule="evenodd" d="M4 0h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm.5 1.5v1a1 1 0 0 0 1 1h5a1 1 0 0 0 1-1v-1h-7zm0 5h7v-1h-7v1zm0 3h7v-1h-7v1zm0 3h4v-1h-4v1z"/>
              </svg>
              {{ $t('admin.instructorNav.submissions') }}
            </router-link>
          </li>
          <li>
            <router-link
              :to="`/instructor/courses/${courseId}/problem-sets`"
              class="instructor-link"
              :aria-current="isActiveRoute(`/instructor/courses/${courseId}/problem-sets`) ? 'page' : undefined"
            >
              <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm4 1v2h8V3H4zm8 3H4v2h8V6zm0 3H4v2h8V9zm-8 3v2h4v-2H4z"/>
              </svg>
              {{ $t('admin.instructorNav.courseProblemSets') }}
            </router-link>
          </li>
        </template>
      </ul>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';


const route = useRoute();

const courseId = computed(() => route.params.courseId as string | undefined);

const isExactDashboard = computed(() => route.path === '/instructor');

const isActiveRoute = (path: string): boolean => {
  return route.path === path;
};
</script>

<style scoped>
/* Skip link for keyboard accessibility (WCAG 2.4.1) */
.skip-link {
    position: fixed;
    top: -100%;
    left: 0;
    background: var(--color-primary-gradient-start);
    color: var(--color-text-primary);
    padding: var(--spacing-md) var(--spacing-lg);
    text-decoration: none;
    font-weight: 600;
    z-index: 10000;
    border-radius: 0 0 var(--radius-base) 0;
    transition: top 0.2s ease-in-out;
    box-shadow: var(--shadow-lg);
}

.skip-link:focus {
    top: 0;
    outline: 3px solid var(--color-text-primary);
    outline-offset: 2px;
}

.instructor-nav {
    background: linear-gradient(135deg, var(--color-admin) 0%, var(--color-admin-hover) 100%);
    color: var(--color-text-primary);
    width: 100%;
    padding: var(--spacing-lg) 0;
    margin-bottom: var(--spacing-xl);
    box-shadow: var(--shadow-md);
}

.instructor-nav-container {
    max-width: var(--max-width-content);
    margin: 0 auto;
    padding: 0 var(--spacing-xl);
    position: relative;
}

.instructor-nav-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
}

.instructor-badge {
    font-weight: 700;
    font-size: var(--font-size-lg);
    color: var(--color-text-primary);
    letter-spacing: 0.5px;
}


.header-divider {
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        var(--color-overlay-strong) 20%,
        var(--color-overlay-strong) 80%,
        transparent 100%
    );
    margin-bottom: var(--spacing-lg);
}

.instructor-nav-list {
    display: flex;
    justify-content: center;
    gap: var(--spacing-lg);
    list-style: none;
    padding: 0;
    margin: 0;
}

.instructor-nav-list li {
    display: inline-flex;
}

.nav-icon {
    flex-shrink: 0;
    margin-right: var(--spacing-sm);
}

.instructor-link {
    display: flex;
    align-items: center;
    color: var(--color-text-primary);
    text-decoration: none;
    padding: var(--spacing-md) var(--spacing-xl);
    border-radius: var(--radius-base);
    font-weight: 600;
    font-size: var(--font-size-base);
    transition: var(--transition-base);
    position: relative;
    background: transparent;
    border: 2px solid transparent;
    white-space: nowrap;
}

.instructor-link::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--color-overlay-medium);
    border-radius: var(--radius-base);
    opacity: 0;
    transition: var(--transition-base);
}

.instructor-link:hover::before {
    opacity: 1;
}

.instructor-link:hover {
    transform: translateY(-2px);
    border-color: var(--color-overlay-strong);
}

.instructor-link:focus-visible {
    outline: 2px solid var(--color-text-primary);
    outline-offset: 2px;
}

.instructor-link.router-link-active {
    background: var(--color-overlay-strong);
    border-color: var(--color-overlay-strong);
    box-shadow:
        0 4px 12px rgba(0, 0, 0, 0.2),
        0 0 20px var(--color-overlay-strong);
}

.instructor-link.router-link-active::after {
    content: '';
    position: absolute;
    bottom: -2px;
    left: 20%;
    right: 20%;
    height: 4px;
    background: var(--color-text-primary);
    border-radius: var(--radius-xs);
    box-shadow: 0 0 8px var(--color-overlay-strong);
}

/* Medium viewport - reduce spacing */
@media (max-width: 1024px) {
    .instructor-nav-list {
        gap: var(--spacing-md);
    }

    .instructor-link {
        padding: var(--spacing-sm) var(--spacing-lg);
    }
}

/* Small viewport - further reduce */
@media (max-width: 768px) {
    .instructor-nav-container {
        padding: 0 var(--spacing-md);
    }

    .instructor-nav-list {
        gap: var(--spacing-sm);
    }

    .instructor-link {
        padding: var(--spacing-sm) var(--spacing-md);
        font-size: var(--font-size-sm);
    }

    .nav-icon {
        width: 14px;
        height: 14px;
    }

    .instructor-nav-header {
        flex-direction: column;
        gap: var(--spacing-xs);
    }
}

@media (max-width: 480px) {
    .instructor-nav-list {
        flex-direction: column;
        width: 100%;
    }

    .instructor-link {
        width: 100%;
        justify-content: center;
    }
}
</style>
