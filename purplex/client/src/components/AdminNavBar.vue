<template>
  <nav class="admin-nav">
    <div class="admin-nav-container">
      <ul class="admin-nav-list">
        <li>
          <router-link
            to="/admin/users"
            class="admin-link"
          >
            Users
          </router-link>
        </li>
        <li>
          <router-link
            to="/admin/problems"
            class="admin-link"
          >
            Problems
          </router-link>
        </li>
        <li>
          <router-link
            to="/admin/problem-sets"
            class="admin-link"
          >
            Problem Sets
          </router-link>
        </li>
        <li>
          <router-link
            to="/admin/submissions"
            class="admin-link"
          >
            Submissions
          </router-link>
        </li>
        <li>
          <router-link
            to="/admin/courses"
            class="admin-link"
          >
            Courses
          </router-link>
        </li>
      </ul>
    </div>
  </nav>
</template>

<script setup lang="ts">
// Static navigation component - no props or state needed
</script>

<style scoped>
.admin-nav {
    background: linear-gradient(135deg, var(--color-admin) 0%, var(--color-admin-hover) 100%);
    color: var(--color-text-primary);
    width: 100%;
    padding: var(--spacing-lg) 0;
    margin-bottom: var(--spacing-xl);
    box-shadow: var(--shadow-md);
}

.admin-nav-container {
    max-width: var(--max-width-content);
    margin: 0 auto;
    padding: 0 var(--spacing-xl);
    position: relative;
}

.admin-nav-list {
    display: flex;
    justify-content: center;
    gap: var(--spacing-lg);
    list-style: none;
    padding: 0;
    margin: 0;
}

.admin-nav-list li {
    display: inline-flex;
}

.admin-link {
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
}

.admin-link::before {
    content: '';
    position: absolute;
    inset: 0;
    background: rgba(255, 255, 255, 0.1);
    border-radius: var(--radius-base);
    opacity: 0;
    transition: var(--transition-base);
}

.admin-link:hover::before {
    opacity: 1;
}

.admin-link:hover {
    transform: translateY(-2px);
    border-color: rgba(255, 255, 255, 0.3);
}

.admin-link:focus-visible {
    outline: 2px solid var(--color-text-primary);
    outline-offset: 2px;
}

.admin-link.router-link-active {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.4);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.admin-link.router-link-active::after {
    content: '';
    position: absolute;
    bottom: -2px;
    left: 20%;
    right: 20%;
    height: 3px;
    background: var(--color-text-primary);
    border-radius: var(--radius-xs);
}

/* Mobile responsive */
@media (max-width: 768px) {
    .admin-nav-container {
        padding: 0 var(--spacing-md);
    }

    .admin-nav-list {
        gap: var(--spacing-sm);
    }

    .admin-link {
        padding: var(--spacing-sm) var(--spacing-md);
        font-size: var(--font-size-sm);
    }
}

@media (max-width: 480px) {
    .admin-nav-list {
        flex-direction: column;
        width: 100%;
    }

    .admin-link {
        width: 100%;
        justify-content: center;
    }
}
</style>
