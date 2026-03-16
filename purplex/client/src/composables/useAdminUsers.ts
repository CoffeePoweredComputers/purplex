/**
 * useAdminUsers - Composable for admin user management.
 *
 * Wraps useDataTable with user-specific logic including:
 * - User fetching with pagination
 * - Role filtering
 * - Role change functionality
 * - Badge variant mapping
 *
 * Usage:
 *   const { items: users, loading, changeRole, ... } = useAdminUsers();
 */
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import axios from 'axios';
import { useDataTable, type UseDataTableReturn } from './useDataTable';
import type { BadgeVariant, DataTableQueryParams, PaginatedResponseWithFilters } from '@/types/datatable';
import { log } from '@/utils/logger';

// User type for admin management
export interface AdminUser {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'instructor' | 'user';
  is_active: boolean;
}

// Filter options returned by the API
export interface UserFilterOptions {
  roles: Array<{ value: string; label: string }>;
}

// Extend the base return type with user-specific functionality
export interface UseAdminUsersReturn extends Omit<UseDataTableReturn<AdminUser, UserFilterOptions>, 'items'> {
  users: UseDataTableReturn<AdminUser, UserFilterOptions>['items'];
  changeRole: (userId: number, newRole: string) => Promise<boolean>;
  updatingUsers: typeof updatingUsers;
  getBadgeVariant: (role: string) => BadgeVariant;
}

// Track which users are being updated
const updatingUsers = ref<Record<number, boolean>>({});

// Helper to get CSRF token
function getCsrfToken(): string | undefined {
  const value = `; ${document.cookie}`;
  const parts = value.split('; csrftoken=');
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift();
  }
  return undefined;
}

// API function to fetch users with pagination
async function fetchUsers(
  params: DataTableQueryParams
): Promise<PaginatedResponseWithFilters<AdminUser, UserFilterOptions>> {
  // Ensure we have a CSRF token
  await axios.get('/api/csrf/', { withCredentials: true });
  const csrfToken = getCsrfToken();

  const response = await axios.get('/api/admin/users/', {
    params: {
      page: params.page,
      page_size: params.page_size,
      search: params.search || undefined,
      role: params.role || undefined,
    },
    headers: {
      'X-CSRFToken': csrfToken,
    },
    withCredentials: true,
  });

  return response.data;
}

export function useAdminUsers(): UseAdminUsersReturn {
  const { t } = useI18n();
  const table = useDataTable<AdminUser, UserFilterOptions>({
    fetchFn: fetchUsers,
    initialPageSize: 25,
    debounceMs: 300,
    filterKeys: ['role'],
  });

  /**
   * Change a user's role.
   * Returns true on success, false on failure.
   */
  async function changeRole(userId: number, newRole: string): Promise<boolean> {
    try {
      updatingUsers.value = { ...updatingUsers.value, [userId]: true };

      const csrfToken = getCsrfToken();

      await axios.post(
        `/api/admin/user/${userId}/`,
        { role: newRole },
        {
          headers: {
            'X-CSRFToken': csrfToken,
          },
          withCredentials: true,
        }
      );

      // Update the user role locally
      const userIndex = table.items.value.findIndex((user) => user.id === userId);
      if (userIndex !== -1) {
        const updatedUsers = [...table.items.value];
        updatedUsers[userIndex] = {
          ...updatedUsers[userIndex],
          role: newRole as AdminUser['role'],
        };
        table.items.value = updatedUsers;
      }

      log.info('User role updated', { userId, newRole });
      return true;
    } catch (error) {
      log.error('Failed to update user role', { error, userId, newRole });
      table.error.value = t('admin.users.failedToUpdateRole');
      return false;
    } finally {
      updatingUsers.value = { ...updatingUsers.value, [userId]: false };
    }
  }

  /**
   * Get badge variant for a role.
   */
  function getBadgeVariant(role: string): BadgeVariant {
    switch (role) {
      case 'admin':
        return 'admin';
      case 'instructor':
        return 'instructor';
      default:
        return 'default';
    }
  }

  return {
    // Rename items to users for clarity
    users: table.items,
    filterOptions: table.filterOptions,

    // State
    loading: table.loading,
    error: table.error,

    // Pagination
    currentPage: table.currentPage,
    pageSize: table.pageSize,
    totalCount: table.totalCount,
    totalPages: table.totalPages,
    hasNext: table.hasNext,
    hasPrevious: table.hasPrevious,
    rangeStart: table.rangeStart,
    rangeEnd: table.rangeEnd,
    pageNumbers: table.pageNumbers,

    // Filters
    searchQuery: table.searchQuery,
    filters: table.filters,
    hasFilters: table.hasFilters,

    // Actions
    fetch: table.fetch,
    goToPage: table.goToPage,
    handlePageSizeChange: table.handlePageSizeChange,
    setFilter: table.setFilter,
    clearFilter: table.clearFilter,
    clearAllFilters: table.clearAllFilters,
    debouncedSearch: table.debouncedSearch,
    refresh: table.refresh,

    // User-specific
    changeRole,
    updatingUsers,
    getBadgeVariant,
  };
}
