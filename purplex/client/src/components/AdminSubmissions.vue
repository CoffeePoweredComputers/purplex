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

.submissions-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.submissions-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.submissions-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.submissions-table tr:hover {
  background: var(--color-bg-hover);
}

.submissions-table tr:last-child td {
  border-bottom: none;
}

.badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-weight: 600;
  font-size: var(--font-size-xs);
  display: inline-block;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.success-badge {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.error-badge {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.pending-badge {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.default-badge {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.action-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-base);
}

.view-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  box-shadow: var(--shadow-colored);
}

.view-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}


/* Responsive Design */
@media (max-width: 768px) {
  .submissions-table {
    font-size: var(--font-size-sm);
  }
  
  .submissions-table th,
  .submissions-table td {
    padding: var(--spacing-md);
  }
  
  .action-button {
    width: 100%;
    justify-content: center;
  }
}
</style>