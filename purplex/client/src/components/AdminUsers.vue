<template>
  <div>
    <AdminNavBar />
    <div class="admin-users">
      <h1 class="page-title">
        User Management Console
      </h1>
      
      <div class="status-container">
        <div
          v-if="loading"
          class="loading-indicator"
        >
          Loading users...
        </div>
        
        <div
          v-if="error"
          class="error-message"
        >
          {{ error }}
        </div>
      </div>
    
      <div
        v-if="!loading && !error"
        class="table-responsive"
      >
        <table class="users-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="user in users"
              :key="user.id"
              :class="{ 'admin-row': user.role === 'admin' }"
            >
              <td>{{ user.username }}</td>
              <td>{{ user.email }}</td>
              <td>
                <span
                  class="badge"
                  :class="getBadgeClass(user.role)"
                >
                  {{ user.role }}
                </span>
              </td>
              <td>
                <div class="role-dropdown-container">
                  <select 
                    class="role-dropdown" 
                    :value="user.role"
                    :disabled="updatingUsers[user.id] || user.email === $store.state.auth.user.email"
                    :title="user.email === $store.state.auth.user.email ? 'You cannot change your own role' : 'Select a role'"
                    @change="changeRole(user.id, $event.target.value)"
                  >
                    <option value="user">
                      User
                    </option>
                    <option value="instructor">
                      Instructor
                    </option>
                    <option value="admin">
                      Admin
                    </option>
                  </select>
                  <span
                    v-if="updatingUsers[user.id]"
                    class="dropdown-spinner"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';
import axios from 'axios';
import AuthService from '../services/auth.service';
import AdminNavBar from './AdminNavBar.vue';
import { log } from '@/utils/logger';

// Setup axios to include credentials and CSRF token
axios.defaults.withCredentials = true;

export default {
  name: 'AdminUsers',
  components: {
    AdminNavBar
  },
  data() {
    return {
      users: [],
      loading: true,
      error: null,
      updatingUsers: {} // Track which users are being updated
    };
  },
  computed: {
    ...mapGetters('auth', ['isAdmin'])
  },
  created() {
    // Redirect non-admin users
    if (!this.isAdmin) {
      this.$router.push('/');
      return;
    }
    
    this.fetchUsers();
  },
  methods: {
    async fetchUsers() {
      try {
        this.loading = true;
        
        // Get CSRF token from cookie if present
        function getCookie(name) {
          const value = `; ${document.cookie}`;
          const parts = value.split(`; ${name}=`);
          if (parts.length === 2) {return parts.pop().split(';').shift();}
        }
        
        // First make a GET request to get the CSRF token
        await axios.get('/api/csrf/', { withCredentials: true });
        
        const csrfToken = getCookie('csrftoken');
        
        const response = await axios.get('/api/admin/users/', { 
          headers: {
            'X-CSRFToken': csrfToken
          },
          withCredentials: true 
        });
        
        this.users = response.data;
        this.loading = false;
      } catch (error) {
        this.error = 'Failed to load users. Please try again.';
        this.loading = false;
        log.error('Error fetching users', { error });
      }
    },
    
    getBadgeClass(role) {
      switch (role) {
        case 'admin':
          return 'admin-badge';
        case 'instructor':
          return 'instructor-badge';
        case 'user':
        default:
          return 'user-badge';
      }
    },
    
    async changeRole(userId, newRole) {
      log.debug('Changing role for user', { userId, newRole });
      try {
        // Set this user as updating
        this.updatingUsers = {
          ...this.updatingUsers,
          [userId]: true
        };
        
        // Get CSRF token from cookie if present
        function getCookie(name) {
          const value = `; ${document.cookie}`;
          const parts = value.split(`; ${name}=`);
          if (parts.length === 2) {return parts.pop().split(';').shift();}
        }
        
        const csrfToken = getCookie('csrftoken');
        
        // Send the request to the server
        await axios.post(`/api/admin/user/${userId}/`, {
          role: newRole
        }, { 
          headers: {
            'X-CSRFToken': csrfToken
          },
          withCredentials: true 
        });
        
        // Update the user role locally instead of refetching all users
        const userIndex = this.users.findIndex(user => user.id === userId);
        if (userIndex !== -1) {
          // Create a copy of the users array to avoid mutating the state directly
          const updatedUsers = [...this.users];
          updatedUsers[userIndex] = {
            ...updatedUsers[userIndex],
            role: newRole
          };
          this.users = updatedUsers;
        }
      } catch (error) {
        this.error = 'Failed to update user role. Please try again.';
        log.error('Error updating user role', { error, userId, newRole });
      } finally {
        // Remove updating status when done
        this.updatingUsers = {
          ...this.updatingUsers,
          [userId]: false
        };
      }
    }
  }
}
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


.status-container {
  margin-bottom: var(--spacing-xl);
}

.loading-indicator {
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  text-align: center;
  box-shadow: var(--shadow-md);
}

.error-message {
  padding: var(--spacing-xl);
  background: var(--color-error-bg);
  border-radius: var(--radius-lg);
  color: var(--color-error-text);
  text-align: center;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-error);
}

.table-responsive {
  overflow-x: auto;
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  border: 2px solid transparent;
  transition: var(--transition-base);
}

.table-responsive:hover {
  border-color: var(--color-bg-input);
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.users-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.users-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.users-table tr:hover {
  background: var(--color-bg-hover);
}

.users-table tr:last-child td {
  border-bottom: none;
}

.admin-row {
  background: linear-gradient(to right, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
}

.badge {
  min-width: 80px;
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-weight: 600;
  font-size: var(--font-size-xs);
  display: inline-block;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.admin-badge {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.instructor-badge {
  background: linear-gradient(135deg, var(--color-info) 0%, #1976d2 100%);
  color: var(--color-text-primary);
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
}

.user-badge {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.role-dropdown-container {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-width: 150px;
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

/* Responsive Design */
@media (max-width: 768px) {
  .users-table {
    font-size: var(--font-size-sm);
  }
  
  .users-table th,
  .users-table td {
    padding: var(--spacing-md);
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
