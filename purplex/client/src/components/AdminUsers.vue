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
import authHeader from '../services/auth-header';
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
        
        const headers = {
          ...authHeader(),
          'X-CSRFToken': getCookie('csrftoken')
        };
        
        const response = await axios.get('/api/admin/users/', { 
          headers: headers,
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
        
        // Prepare headers with auth token and CSRF token
        const headers = {
          ...authHeader(),
          'X-CSRFToken': getCookie('csrftoken')
        };
        
        // Send the request to the server
        await axios.post(`/api/admin/user/${userId}/`, {
          role: newRole
        }, { 
          headers: headers,
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
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
  background-color: #1e1e1e;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.page-title {
  font-size: 28px;
  color: #e0e0e0;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #444;
}

.status-container {
  margin-bottom: 20px;
}

.loading-indicator {
  padding: 15px;
  background-color: #333;
  border-radius: 6px;
  color: #ddd;
}

.error-message {
  padding: 15px;
  background-color: #442a2a;
  border-radius: 6px;
  color: #ffadb9;
}

.table-responsive {
  overflow-x: auto;
  background-color: #272727;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.users-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.users-table th {
  background-color: #333;
  color: #ddd;
  padding: 12px 15px;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.9rem;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #444;
}

.users-table td {
  padding: 12px 15px;
  border-bottom: 1px solid #333;
  color: #e0e0e0;
  vertical-align: middle;
}

.users-table tr:hover {
  background-color: #2a2a2a;
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
  padding: 6px 12px;
  border-radius: 30px;
  font-weight: 500;
  font-size: 0.8rem;
  display: inline-block;
  text-align: center;
}

.admin-badge {
  background-color: #673ab7;
  color: white;
}

.user-badge {
  background-color: #333;
  color: white;
}

.active-badge {
  background-color: #444;
  color: white;
}

.inactive-badge {
  background-color: #333;
  color: white;
}

.action-button {
  width: 150px;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.85rem;
  text-align: center;
}

.promote-button {
  background-color: #444;
}

.promote-button:hover {
  background-color: #555;
}

.demote-button {
  background-color: #333;
}

.demote-button:hover {
  background-color: #444;
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
