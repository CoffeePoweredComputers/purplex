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
        const response = await axios.get('/api/admin/submissions/');
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

.submissions-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.submissions-table th {
  background-color: var(--color-bg-input);
  color: var(--color-text-tertiary);
  padding: var(--spacing-md) var(--spacing-base);
  font-weight: 600;
  text-transform: uppercase;
  font-size: calc(var(--font-size-sm) + 0.05rem);
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--color-bg-border);
}

.submissions-table td {
  padding: var(--spacing-md) var(--spacing-base);
  border-bottom: 1px solid var(--color-bg-input);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.submissions-table tr:hover {
  background-color: var(--color-bg-hover);
}

.submissions-table tr:last-child td {
  border-bottom: none;
}

.badge {
  padding: calc(var(--spacing-xs) + 2px) var(--spacing-md);
  border-radius: var(--radius-round);
  font-weight: 500;
  font-size: calc(var(--font-size-xs) + 0.05rem);
  display: inline-block;
  text-align: center;
}

.success-badge {
  background-color: var(--color-success-bg);
  color: var(--color-success-text);
}

.error-badge {
  background-color: var(--color-error-bg);
  color: var(--color-error-text);
}

.pending-badge {
  background-color: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.default-badge {
  background-color: var(--color-info-bg);
  color: var(--color-info-text);
}

.action-button {
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: var(--radius-xs);
  font-weight: 500;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
}

.view-button {
  background-color: var(--color-success-bg);
}

.view-button:hover {
  background-color: #3a6349;
}
</style>