<template>
  <div>
    <AdminNavBar />
    <div class="admin-users">
      <h1 class="page-title">User Management Console</h1>
      
      <div class="status-container">
        <div class="loading-indicator" v-if="loading">
          Loading users...
        </div>
        
        <div class="error-message" v-if="error">
          {{ error }}
        </div>
      </div>
    
    <div class="table-responsive" v-if="!loading && !error">
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
          <tr v-for="user in users" :key="user.id" :class="{ 'admin-row': user.role === 'admin' }">
            <td>{{ user.username }}</td>
            <td>{{ user.email }}</td>
            <td>
              <span class="badge" :class="user.role === 'admin' ? 'admin-badge' : 'user-badge'">
                {{ user.role }}
              </span>
            </td>
            <td>
              <button 
                v-if="user.role === 'user'" 
                class="action-button promote-button" 
                @click="changeRole(user.id, 'admin')"
                :disabled="updatingUsers[user.id] || user.email === this.$store.state.auth.user.email"
                :title="user.email === this.$store.state.auth.user.email ? 'You cannot change your own role' : ''"
              >
                <span v-if="updatingUsers[user.id]" class="button-spinner"></span>
                <span v-else>Promote to Admin</span>
              </button>
              <button 
                v-if="user.role === 'admin'" 
                class="action-button demote-button" 
                @click="changeRole(user.id, 'user')"
                :disabled="updatingUsers[user.id] || user.email === this.$store.state.auth.user.email"
                :title="user.email === this.$store.state.auth.user.email ? 'You cannot change your own role' : ''"
              >

                <span v-if="updatingUsers[user.id]" class="button-spinner"></span>
                <span v-else>Set as User</span>
              </button>
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
          if (parts.length === 2) return parts.pop().split(';').shift();
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
        console.error('Error fetching users:', error);
      }
    },
    
    async changeRole(userId, newRole) {
      console.log('Changing role for user:', userId, 'to', newRole);
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
          if (parts.length === 2) return parts.pop().split(';').shift();
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
        console.error('Error updating user role:', error);
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
  max-width: var(--max-width-panel);
  margin: 0 auto;
  padding: var(--spacing-lg);
  background-color: var(--color-bg-panel);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-base);
}

.page-title {
  font-size: var(--font-size-xl);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-sm);
  border-bottom: 2px solid var(--color-bg-border);
}

.status-container {
  margin-bottom: var(--spacing-lg);
}

.loading-indicator {
  padding: var(--spacing-base);
  background-color: var(--color-bg-input);
  border-radius: calc(var(--radius-sm) + 1px);
  color: var(--color-text-tertiary);
}

.error-message {
  padding: var(--spacing-base);
  background-color: var(--color-error-bg);
  border-radius: calc(var(--radius-sm) + 1px);
  color: var(--color-error-text);
}

.table-responsive {
  overflow-x: auto;
  background-color: var(--color-bg-table);
  border-radius: calc(var(--radius-sm) + 1px);
  box-shadow: var(--shadow-sm);
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.users-table th {
  background-color: var(--color-bg-input);
  color: var(--color-text-tertiary);
  padding: var(--spacing-md) var(--spacing-base);
  font-weight: 600;
  text-transform: uppercase;
  font-size: calc(var(--font-size-sm) + 0.05rem);
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--color-bg-border);
}

.users-table td {
  padding: var(--spacing-md) var(--spacing-base);
  border-bottom: 1px solid var(--color-bg-input);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.users-table tr:hover {
  background-color: var(--color-bg-hover);
}

.users-table tr:last-child td {
  border-bottom: none;
}

.admin-row {
  /* light purple background for admin users */
  background-color: #4b2e833d;
}

.badge {
  width: 100px;
  padding: calc(var(--spacing-xs) + 2px) var(--spacing-md);
  border-radius: var(--radius-round);
  font-weight: 500;
  font-size: calc(var(--font-size-xs) + 0.05rem);
  display: inline-block;
  text-align: center;
}

.admin-badge {
  background-color: var(--color-admin);
  color: var(--color-text-primary);
}

.user-badge {
  background-color: var(--color-bg-input);
  color: var(--color-text-primary);
}

.active-badge {
  background-color: var(--color-bg-border);
  color: var(--color-text-primary);
}

.inactive-badge {
  background-color: var(--color-bg-input);
  color: var(--color-text-primary);
}

.action-button {
  width: 150px;
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: var(--radius-xs);
  font-weight: 500;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
  text-align: center;
}

.promote-button {
  background-color: var(--color-bg-border);
}

.promote-button:hover {
  background-color: var(--color-bg-disabled);
}

.demote-button {
  background-color: var(--color-bg-input);
}

.demote-button:hover {
  background-color: var(--color-bg-border);
}

.button-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: button-spin 1s linear infinite;
}

@keyframes button-spin {
  to {
    transform: rotate(360deg);
  }
}

button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>
