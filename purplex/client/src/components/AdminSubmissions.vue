<template>
  <div>
    <AdminNavBar />
    <div class="admin-submissions container">
      <h1 class="page-title">Submissions Management</h1>
      
      <div class="status-container">
        <div class="loading-indicator" v-if="loading">
          Loading submissions...
        </div>
        
        <div class="error-message" v-if="error">
          {{ error }}
        </div>
      </div>
      
      <div class="table-responsive" v-if="!loading && !error">
        <table class="submissions-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Problem</th>
              <th>Status</th>
              <th>Submitted</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="submission in submissions" :key="submission.id">
              <td>{{ submission.user }}</td>
              <td>{{ submission.problem }}</td>
              <td>
                <span class="badge" :class="submissionStatusClass(submission.status)">
                  {{ submission.status }}
                </span>
              </td>
              <td>{{ formatDate(submission.created_at) }}</td>
              <td>
                <button class="action-button view-button" @click="viewSubmission(submission.id)">
                  View Details
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

export default {
  name: 'AdminSubmissions',
  components: {
    AdminNavBar
  },
  data() {
    return {
      submissions: [],
      loading: true,
      error: null
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
    
    this.fetchSubmissions();
  },
  methods: {
    async fetchSubmissions() {
      try {
        this.loading = true;
        const response = await axios.get('/api/admin/submissions/', { headers: authHeader() });
        this.submissions = response.data;
        this.loading = false;
      } catch (error) {
        this.error = 'Failed to load submissions. Please try again.';
        this.loading = false;
        console.error('Error fetching submissions:', error);
      }
    },
    
    viewSubmission(submissionId) {
      // Navigate to submission details page
      this.$router.push(`/admin/submissions/${submissionId}`);
    },
    
    submissionStatusClass(status) {
      switch(status.toLowerCase()) {
        case 'passed':
          return 'success-badge';
        case 'failed':
          return 'error-badge';
        case 'pending':
          return 'pending-badge';
        default:
          return 'default-badge';
      }
    },
    
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleString();
    }
  }
}
</script>

<style scoped>
.admin-submissions {
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

.submissions-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.submissions-table th {
  background-color: #333;
  color: #ddd;
  padding: 12px 15px;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.9rem;
  letter-spacing: 0.5px;
  border-bottom: 2px solid #444;
}

.submissions-table td {
  padding: 12px 15px;
  border-bottom: 1px solid #333;
  color: #e0e0e0;
  vertical-align: middle;
}

.submissions-table tr:hover {
  background-color: #2a2a2a;
}

.submissions-table tr:last-child td {
  border-bottom: none;
}

.badge {
  padding: 6px 12px;
  border-radius: 30px;
  font-weight: 500;
  font-size: 0.8rem;
  display: inline-block;
  text-align: center;
}

.success-badge {
  background-color: #2d4d3a;
  color: #a3e9c1;
}

.error-badge {
  background-color: #4d2d2d;
  color: #e9a3a3;
}

.pending-badge {
  background-color: #4d4c2d;
  color: #e9e4a3;
}

.default-badge {
  background-color: #2d3a4d;
  color: #a3c9e9;
}

.action-button {
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  font-weight: 500;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.85rem;
}

.view-button {
  background-color: #2d4d3a;
}

.view-button:hover {
  background-color: #3a6349;
}
</style>