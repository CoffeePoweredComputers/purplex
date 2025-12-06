<template>
  <div>
    <AdminNavBar />
    <div class="admin-problems container">
      <h1 class="page-title">
        Problems Management
      </h1>
      
      <div class="status-container">
        <div
          v-if="loading"
          class="loading-indicator"
        >
          Loading problems...
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
        class="controls-container"
      >
        <button
          class="action-button add-button"
          @click="createNewProblem"
        >
          Add New Problem
        </button>
      </div>
      
      <div
        v-if="!loading && !error"
        class="table-responsive"
      >
        <table class="problems-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Title</th>
              <th>Difficulty</th>
              <th>Problem Sets</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="problem in problems"
              :key="problem.slug"
            >
              <td>
                <span
                  class="type-badge"
                  :class="problemTypeClass(problem.problem_type)"
                >
                  {{ getProblemTypeLabel(problem.problem_type) }}
                </span>
              </td>
              <td>{{ problem.title }}</td>
              <td>
                <span
                  class="badge"
                  :class="difficultyClass(problem.difficulty)"
                >
                  {{ problem.difficulty }}
                </span>
              </td>
              <td>{{ getProblemSetNames(problem) }}</td>
              <td class="actions-cell">
                <button
                  class="action-button edit-button"
                  @click="editProblem(problem.slug)"
                >
                  Edit
                </button>
                <button
                  class="action-button delete-button"
                  @click="confirmDelete(problem)"
                >
                  Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { mapGetters } from 'vuex';
import axios, { AxiosError } from 'axios';
import AdminNavBar from './AdminNavBar.vue';
import { log } from '@/utils/logger';
import { useNotification } from '@/composables/useNotification';
import type { ProblemDetailed } from '@/types';

interface ProblemSet {
  id: number;
  title: string;
  slug: string;
}

export default defineComponent({
  name: 'AdminProblems',
  components: {
    AdminNavBar
  },
  setup() {
    const { notify } = useNotification();
    return { notify };
  },
  data(): {
    problems: ProblemDetailed[];
    problemSets: ProblemSet[];
    loading: boolean;
    error: string | null;
  } {
    return {
      problems: [],
      problemSets: [], // Add this to store problem sets for the modal
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
    
    this.fetchProblems();
    this.fetchProblemSets();
  },
  methods: {
    async fetchProblems(): Promise<void> {
      try {
        this.loading = true;
        log.debug('Fetching problems from /api/admin/problems/');
        const response = await axios.get('/api/admin/problems/');
        log.debug('Problems fetched successfully', { count: response.data.length });
        this.problems = response.data;
        this.loading = false;
      } catch (error) {
        const axiosError = error as AxiosError<{ error?: string }>;
        log.error('Failed to fetch problems', {
          error,
          response: axiosError.response,
          status: axiosError.response?.status,
          data: axiosError.response?.data
        });
        
        let errorMessage = 'Failed to load problems. ';
        if (axiosError.response) {
          if (axiosError.response.status === 401) {
            errorMessage += 'Authentication required. Please log in again.';
          } else if (axiosError.response.status === 403) {
            errorMessage += 'Access denied. Admin privileges required.';
          } else if (axiosError.response.status === 404) {
            errorMessage += 'API endpoint not found.';
          } else if (axiosError.response.status === 500) {
            errorMessage += 'Server error. Please try again later.';
          } else {
            errorMessage += `Error: ${axiosError.response.data?.detail || axiosError.message}`;
          }
        } else if (axiosError.request) {
          errorMessage += 'No response from server. Check if backend is running.';
        } else {
          errorMessage += axiosError.message;
        }
        
        this.error = errorMessage;
        this.loading = false;
      }
    },
    
    async fetchProblemSets(): Promise<void> {
      try {
        const response = await axios.get('/api/admin/problem-sets/');
        this.problemSets = response.data;
      } catch (error) {
        log.error('Error fetching problem sets', { error });
        // Don't set error state here as it's not critical for the page to load
      }
    },
    
    
    getCategoryNames(problem: ProblemDetailed): string {
      if (!problem.categories || problem.categories.length === 0) {
        return 'None';
      }
      return problem.categories.map(cat => cat.name).join(', ');
    },
    
    getProblemSetNames(problem: ProblemDetailed): string {
      // The problem_sets field contains the actual problem sets this problem belongs to
      if (!problem.problem_sets || problem.problem_sets.length === 0) {
        return 'None';
      }
      
      // problem_sets is a list of problem set objects with their data
      return problem.problem_sets.map(ps => ps.title || 'Unknown').join(', ');
    },
    
    difficultyClass(difficulty: string): string {
      switch(difficulty.toLowerCase()) {
        case 'easy':
          return 'easy-badge';
        case 'beginner':
          return 'easy-badge';
        case 'intermediate':
          return 'medium-badge';
        case 'advanced':
          return 'hard-badge';
        default:
          return 'default-badge';
      }
    },
    
    problemTypeClass(type: string): string {
      switch(type) {
        case 'eipl':
          return 'eipl-badge';
        default:
          return 'default-type-badge';
      }
    },

    getProblemTypeLabel(type: string): string {
      switch(type) {
        case 'eipl':
          return 'EiPL';
        case 'mcq':
          return 'MCQ';
        case 'prompt':
          return 'Prompt';
        default:
          return type || 'Unknown';
      }
    },
    
    createNewProblem(): void {
      this.$router.push('/admin/problems/new');
    },
    
    editProblem(problemSlug: string): void {
      this.$router.push(`/admin/problems/${problemSlug}/edit`);
    },
    
    confirmDelete(problem: ProblemDetailed): void {
      if (confirm(`Are you sure you want to delete the problem "${problem.title}"? This action cannot be undone.`)) {
        this.deleteProblem(problem);
      }
    },
    
    async deleteProblem(problem: ProblemDetailed): Promise<void> {
      try {
        await axios.delete(`/api/admin/problems/${problem.slug}/`);
        this.problems = this.problems.filter(p => p.slug !== problem.slug);
        this.notify.success('Problem deleted', `"${problem.title}" has been removed.`);
      } catch (error) {
        const axiosError = error as AxiosError<{ error?: string }>;
        const backendError = axiosError.response?.data?.error;

        // Check if it's a submissions-related error
        if (backendError?.includes('submission')) {
          this.notify.error(
            `"${problem.title}" has existing submissions`,
            'Deactivate the problem instead to hide it from students.'
          );
        } else {
          this.notify.error('Delete failed', backendError || 'Please try again.');
        }
        log.error('Error deleting problem', { error });
      }
    },



    handleError(errorMessage: string): void {
      this.error = errorMessage;
      // Clear error after 5 seconds
      setTimeout(() => {
        this.error = null;
      }, 5000);
    }
  }
})
</script>

<style scoped>
.admin-problems {
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

.controls-container {
  display: flex;
  gap: var(--spacing-lg);
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

.problems-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.problems-table th {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  padding: var(--spacing-lg) var(--spacing-xl);
  font-weight: 600;
  font-size: var(--font-size-base);
  border-bottom: 2px solid var(--color-bg-input);
}

.problems-table td {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 1px solid var(--color-bg-hover);
  color: var(--color-text-secondary);
  vertical-align: middle;
}

.problems-table tr:hover {
  background: var(--color-bg-hover);
}

.problems-table tr:last-child td {
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

.easy-badge {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.medium-badge {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.hard-badge {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.default-badge {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.type-badge {
  padding: var(--spacing-xs) var(--spacing-md);
  border-radius: var(--radius-xl);
  font-weight: 600;
  font-size: var(--font-size-xs);
  display: inline-block;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.eipl-badge {
  background: var(--color-info-bg);
  color: var(--color-info-text);
  border: 1px solid var(--color-info);
}

.function-badge {
  background: var(--color-admin);
  color: var(--color-text-primary);
  border: 1px solid var(--color-admin);
  opacity: 0.9;
}

.default-type-badge {
  background: var(--color-bg-hover);
  color: var(--color-text-muted);
  border: 1px solid var(--color-bg-border);
}

.actions-cell {
  display: flex;
  gap: var(--spacing-md);
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

.add-button, .manage-sets-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  box-shadow: var(--shadow-colored);
}

.add-button:hover, .manage-sets-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.add-button::before {
  content: "+";
  font-size: 18px;
  font-weight: bold;
}

.edit-button {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  border: 1px solid var(--color-bg-border);
}

.edit-button:hover {
  background: var(--color-bg-input);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.delete-button {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
}

.delete-button:hover {
  background: var(--color-error);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

/* Responsive Design */
@media (max-width: 768px) {
  .controls-container {
    flex-direction: column;
  }
  
  .action-button {
    width: 100%;
    justify-content: center;
  }
  
  .problems-table {
    font-size: var(--font-size-sm);
  }
  
  .problems-table th,
  .problems-table td {
    padding: var(--spacing-md);
  }
  
  .actions-cell {
    flex-direction: column;
  }
}
</style>
