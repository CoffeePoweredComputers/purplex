<template>
  <div>
    <AdminNavBar />
    <div class="admin-users">
      <h1 class="page-title">
        User Management Console
      </h1>

      <DataTable
        :columns="columns"
        :items="users"
        :loading="loading"
        :error="error"
        :total-count="totalCount"
        :current-page="currentPage"
        :page-size="pageSize"
        :total-pages="totalPages"
        :has-next="hasNext"
        :has-previous="hasPrevious"
        :page-numbers="pageNumbers"
        :range-start="rangeStart"
        :range-end="rangeEnd"
        item-label="users"
        row-key="id"
        empty-title="No Users Found"
        empty-message="There are no users matching your filters."
        @go-to-page="goToPage"
        @page-size-change="handlePageSizeChange"
        @retry="fetch"
      >
        <!-- Filters -->
        <template #filters>
          <div class="filters-section">
            <div class="filter-group">
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Search by username or email..."
                class="search-input"
                @input="debouncedSearch"
              >
            </div>
            <div class="filter-group">
              <select
                :value="filters.role || ''"
                class="filter-select"
                @change="handleRoleFilterChange"
              >
                <option value="">All Roles</option>
                <option
                  v-for="role in filterOptions?.roles || defaultRoles"
                  :key="role.value"
                  :value="role.value"
                >
                  {{ role.label }}
                </option>
              </select>
            </div>
            <Transition name="fade">
              <button
                v-if="hasFilters"
                class="clear-filters-btn"
                @click="clearAllFilters"
              >
                Clear Filters
              </button>
            </Transition>
          </div>
        </template>

        <!-- Role badge column -->
        <template #cell-role="{ value }">
          <StatusBadge
            :value="value"
            :variant="getBadgeVariant(value)"
          />
        </template>

        <!-- Actions column -->
        <template #cell-actions="{ item }">
          <div class="role-dropdown-container">
            <select
              class="role-dropdown"
              :value="item.role"
              :disabled="updatingUsers[item.id] || item.email === currentUserEmail"
              :title="item.email === currentUserEmail ? 'You cannot change your own role' : 'Select a role'"
              @change="handleRoleChange(item.id, ($event.target as HTMLSelectElement).value)"
            >
              <option value="user">User</option>
              <option value="instructor">Instructor</option>
              <option value="admin">Admin</option>
            </select>
            <span
              v-if="updatingUsers[item.id]"
              class="dropdown-spinner"
            />
          </div>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useStore } from 'vuex';
import { useRouter } from 'vue-router';
import AdminNavBar from './AdminNavBar.vue';
import DataTable from './ui/DataTable.vue';
import StatusBadge from './ui/StatusBadge.vue';
import { useAdminUsers, type AdminUser } from '@/composables/useAdminUsers';
import type { DataTableColumn } from '@/types/datatable';

const store = useStore();
const router = useRouter();

// Check admin access
const isAdmin = computed(() => store.getters['auth/isAdmin']);
const currentUserEmail = computed(() => store.state.auth.user?.email || '');

// Redirect non-admins
if (!isAdmin.value) {
  router.push('/');
}

// Use the admin users composable
const {
  users,
  loading,
  error,
  currentPage,
  pageSize,
  totalCount,
  totalPages,
  hasNext,
  hasPrevious,
  pageNumbers,
  rangeStart,
  rangeEnd,
  searchQuery,
  filters,
  filterOptions,
  hasFilters,
  fetch,
  goToPage,
  handlePageSizeChange,
  setFilter,
  clearAllFilters,
  debouncedSearch,
  changeRole,
  updatingUsers,
  getBadgeVariant,
} = useAdminUsers();

// Default roles for when API hasn't loaded filter options yet
const defaultRoles = [
  { value: 'admin', label: 'Admin' },
  { value: 'instructor', label: 'Instructor' },
  { value: 'user', label: 'User' },
];

// Column definitions
const columns: DataTableColumn<AdminUser>[] = [
  { key: 'username', label: 'Username' },
  { key: 'email', label: 'Email', hideOnMobile: true },
  { key: 'role', label: 'Role', slot: 'cell-role', align: 'center' },
  { key: 'actions', label: 'Actions', slot: 'cell-actions', align: 'center' },
];

// Handlers
function handleRoleFilterChange(event: Event) {
  const target = event.target as HTMLSelectElement;
  if (target.value) {
    setFilter('role', target.value);
  } else {
    // Clear the role filter when "All Roles" is selected
    const newFilters = { ...filters.value };
    delete newFilters.role;
    filters.value = newFilters;
    fetch();
  }
}

async function handleRoleChange(userId: number, newRole: string) {
  await changeRole(userId, newRole);
}

// Fetch users on mount
onMounted(() => {
  if (isAdmin.value) {
    fetch();
  }
});
</script>

<style scoped>
.admin-users {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-lg);
}

.page-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xl) 0;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-input);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

/* Filters */
.filters-section {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  align-items: center;
}

.filter-group {
  flex: 1;
  min-width: 200px;
}

.search-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  transition: var(--transition-base);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.filter-select {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.clear-filters-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-base);
}

.clear-filters-btn:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
}

/* Role dropdown in actions */
.role-dropdown-container {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-width: 130px;
}

.role-dropdown {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
  outline: none;
}

.role-dropdown:hover:not(:disabled) {
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-hover);
}

.role-dropdown:focus {
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.role-dropdown:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--color-bg-disabled);
}

.role-dropdown option {
  background: var(--color-bg-panel);
  color: var(--color-text-primary);
  padding: var(--spacing-sm);
}

.dropdown-spinner {
  position: absolute;
  right: var(--spacing-md);
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: var(--color-text-primary);
  animation: dropdown-spin 1s linear infinite;
  pointer-events: none;
}

@keyframes dropdown-spin {
  to {
    transform: rotate(360deg);
  }
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Responsive Design */
@media (max-width: 768px) {
  .filters-section {
    flex-direction: column;
  }

  .filter-group {
    width: 100%;
    min-width: unset;
  }

  .clear-filters-btn {
    width: 100%;
  }

  .role-dropdown-container {
    min-width: auto;
    width: 100%;
  }

  .role-dropdown {
    font-size: var(--font-size-xs);
  }
}
</style>
