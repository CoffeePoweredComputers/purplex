<template>
  <div>
    <AdminNavBar />
    <div class="admin-submissions container">
      <h1 class="page-title">
        Submissions Management
      </h1>
      
      <div class="status-container">
        <div
          v-if="loading"
          class="loading-indicator"
        >
          Loading submissions...
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
        <div class="search-container">
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Search users, problems, or problem sets..."
            class="search-input"
            @input="debounceSearch"
          >
        </div>
        <select
          v-model="statusFilter"
          class="filter-select"
          @change="onFilterChange"
        >
          <option value="">
            All Status
          </option>
          <option value="passed">
            Passed
          </option>
          <option value="partial">
            Partial
          </option>
          <option value="failed">
            Failed
          </option>
        </select>
        <select
          v-model="problemSetFilter"
          class="filter-select"
          @change="onFilterChange"
        >
          <option value="">
            All Problem Sets
          </option>
          <option
            v-for="set in uniqueProblemSets"
            :key="set"
            :value="set"
          >
            {{ set }}
          </option>
        </select>
        <button 
          class="action-button export-button" 
          :disabled="totalCount === 0" 
          title="Export filtered submissions to CSV"
          @click="exportToCSV"
        >
          Export CSV ({{ totalCount }})
        </button>
      </div>
      
      <div
        v-if="!loading && !error"
        class="table-responsive"
      >
        <table class="submissions-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Problem</th>
              <th>Problem Set</th>
              <th>Score</th>
              <th>Comprehension</th>
              <th>Status</th>
              <th>Submitted</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="submission in submissions"
              :key="submission.id"
            >
              <td>
                <div class="user-info">
                  <div class="user-avatar-small">
                    {{ submission.user.charAt(0).toUpperCase() }}
                  </div>
                  <span class="username">{{ submission.user }}</span>
                </div>
              </td>
              <td>{{ submission.problem }}</td>
              <td>
                <span class="problem-set-tag">{{ submission.problem_set }}</span>
              </td>
              <td>
                <div
                  class="score-indicator"
                  :class="getScoreClass(submission.score)"
                >
                  {{ submission.score }}%
                </div>
              </td>
              <td>
                <span
                  class="comprehension-badge"
                  :class="comprehensionLevelClass(submission.comprehension_level)"
                >
                  {{ formatComprehensionLevel(submission.comprehension_level) }}
                </span>
              </td>
              <td>
                <span
                  class="status-badge"
                  :class="submissionStatusClass(submission.status)"
                >
                  {{ submission.status }}
                </span>
              </td>
              <td>
                <span class="time-stamp">{{ formatISODate(submission.submitted_at) }}</span>
              </td>
              <td class="actions-cell">
                <button
                  class="action-button view-button"
                  title="View Details"
                  @click="viewSubmission(submission.id)"
                >
                  View
                </button>
                <button
                  class="action-button download-button"
                  title="Download Data"
                  @click="downloadSubmissionData(submission)"
                >
                  Download
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        
        <div
          v-if="submissions.length === 0 && !loading"
          class="empty-state"
        >
          <div class="empty-icon">
            📝
          </div>
          <div class="empty-title">
            No submissions found
          </div>
          <div class="empty-subtitle">
            Try adjusting your search or filter criteria
          </div>
        </div>
        
        <!-- Pagination Controls -->
        <div
          v-if="totalPages > 1 && !loading && !error"
          class="pagination-container"
        >
          <div class="pagination-info">
            Showing {{ paginationInfo.start }}-{{ paginationInfo.end }} of {{ paginationInfo.total }} results
          </div>
          
          <div class="pagination-controls">
            <button 
              class="pagination-btn" 
              :disabled="!hasPrevious" 
              title="First page"
              @click="goToPage(1)"
            >
              ⟪
            </button>
            
            <button 
              class="pagination-btn" 
              :disabled="!hasPrevious" 
              title="Previous page"
              @click="goToPage(currentPage - 1)"
            >
              ⟨
            </button>
            
            <button 
              v-for="page in pageNumbers" 
              :key="page"
              class="pagination-btn page-number" 
              :class="{ active: page === currentPage }"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
            
            <button 
              class="pagination-btn" 
              :disabled="!hasNext" 
              title="Next page"
              @click="goToPage(currentPage + 1)"
            >
              ⟩
            </button>
            
            <button 
              class="pagination-btn" 
              :disabled="!hasNext" 
              title="Last page"
              @click="goToPage(totalPages)"
            >
              ⟫
            </button>
          </div>
          
          <div class="page-size-selector">
            <label for="pageSize">Per page:</label>
            <select
              id="pageSize"
              v-model="pageSize"
              class="page-size-select"
              @change="changePageSize"
            >
              <option value="25">
                25
              </option>
              <option value="50">
                50
              </option>
              <option value="100">
                100
              </option>
            </select>
          </div>
        </div>
      </div>
      
      <!-- View Submission Modal -->
      <ViewSubmissionModal 
        :is-visible="showViewModal" 
        :submission="selectedSubmission"
        @close="closeViewModal"
        @download="downloadSubmissionData"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { mapGetters } from 'vuex';
import axios, { AxiosError } from 'axios';
import AdminNavBar from './AdminNavBar.vue';
import ViewSubmissionModal from '../modals/ViewSubmissionModal.vue';
import { log } from '@/utils/logger';
import { useNotification } from '@/composables/useNotification';
import type { SubmissionDetailed } from '@/types';

interface ComponentData {
  submissions: SubmissionDetailed[];
  loading: boolean;
  error: string | null;
  searchQuery: string;
  statusFilter: string;
  problemSetFilter: string;
  showViewModal: boolean;
  selectedSubmission: SubmissionDetailed | null;
  currentPage: number;
  totalCount: number;
  totalPages: number;
  pageSize: number;
  hasNext: boolean;
  hasPrevious: boolean;
  searchTimeout: NodeJS.Timeout | null;
  notify: ReturnType<typeof useNotification>['notify'];
}

export default defineComponent({
  name: 'AdminSubmissions',
  components: {
    AdminNavBar,
    ViewSubmissionModal
  },
  data(): ComponentData {
    return {
      submissions: [],
      loading: true,
      error: null,
      searchQuery: '',
      statusFilter: '',
      problemSetFilter: '',
      showViewModal: false,
      selectedSubmission: null,
      // Pagination data
      currentPage: 1,
      totalCount: 0,
      totalPages: 0,
      pageSize: 25,
      hasNext: false,
      hasPrevious: false,
      searchTimeout: null,
      notify: null as any // Will be set in created()
    };
  },
  computed: {
    ...mapGetters('auth', ['isAdmin']),
    
    uniqueProblemSets(): string[] {
      const sets = new Set<string>();
      this.submissions.forEach(submission => {
        if (submission.problem_set && submission.problem_set !== 'Unknown') {
          sets.add(submission.problem_set);
        }
      });
      return Array.from(sets).sort();
    },
    
    paginationInfo(): { start: number; end: number; total: number } {
      const start = (this.currentPage - 1) * this.pageSize + 1;
      const end = Math.min(this.currentPage * this.pageSize, this.totalCount);
      return { start, end, total: this.totalCount };
    },
    
    pageNumbers(): number[] {
      const pages: number[] = [];
      const maxVisible = 5;
      const half = Math.floor(maxVisible / 2);
      
      let start = Math.max(1, this.currentPage - half);
      const end = Math.min(this.totalPages, start + maxVisible - 1);
      
      if (end - start + 1 < maxVisible) {
        start = Math.max(1, end - maxVisible + 1);
      }
      
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      
      return pages;
    },
    
    // Removed groupedSubmissions - no longer needed for simple table
  },
  created() {
    // Set up notification
    const { notify } = useNotification();
    this.notify = notify;
    
    // Redirect non-admin users
    if (!this.isAdmin) {
      this.$router.push('/');
      return;
    }
    
    this.fetchSubmissions();
  },
  methods: {
    async fetchSubmissions(): Promise<void> {
      try {
        this.loading = true;
        
        // Build query parameters
        const params = new URLSearchParams();
        params.append('page', this.currentPage);
        params.append('page_size', this.pageSize);
        
        if (this.searchQuery.trim()) {
          params.append('search', this.searchQuery.trim());
        }
        if (this.statusFilter) {
          params.append('status', this.statusFilter);
        }
        if (this.problemSetFilter) {
          params.append('problem_set', this.problemSetFilter);
        }
        
        const response = await axios.get(`/api/admin/submissions/?${params.toString()}`);
        
        // Handle paginated response
        this.submissions = response.data.results;
        this.totalCount = response.data.count;
        this.totalPages = Math.ceil(this.totalCount / this.pageSize);
        this.hasNext = !!response.data.next;
        this.hasPrevious = !!response.data.previous;
        
        this.loading = false;
      } catch (error) {
        this.error = 'Failed to load submissions. Please try again.';
        this.loading = false;
        log.error('Error fetching submissions', { error });
      }
    },
    
    goToPage(page: number): void {
      if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
        this.currentPage = page;
        this.fetchSubmissions();
      }
    },
    
    changePageSize(): void {
      this.currentPage = 1; // Reset to first page
      this.fetchSubmissions();
    },
    
    debounceSearch(): void {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.currentPage = 1; // Reset to first page
        this.fetchSubmissions();
      }, 500);
    },
    
    onFilterChange(): void {
      this.currentPage = 1; // Reset to first page
      this.fetchSubmissions();
    },
    
    // Removed toggleUserGroup and calculateAverageScore - no longer needed
    
    getScoreClass(score: number): string {
      if (score >= 80) {return 'score-excellent';}
      if (score >= 60) {return 'score-good';}
      if (score >= 40) {return 'score-fair';}
      return 'score-poor';
    },
    
    async viewSubmission(submissionId: number): Promise<void> {
      try {
        this.loading = true;
        const response = await axios.get(`/api/admin/submissions/${submissionId}/`);
        this.selectedSubmission = response.data;
        this.showViewModal = true;
        this.loading = false;
      } catch (error) {
        log.error('Error fetching submission details', { error, submissionId });
        this.notify.error('Failed to load submission details. Please try again.');
        this.loading = false;
      }
    },
    
    closeViewModal(): void {
      this.showViewModal = false;
      this.selectedSubmission = null;
    },
    
    submissionStatusClass(status: string): string {
      switch(status.toLowerCase()) {
        case 'passed':
          return 'success-badge';
        case 'partial':
          return 'pending-badge';
        case 'failed':
          return 'error-badge';
        case 'pending':
          return 'pending-badge';
        default:
          return 'default-badge';
      }
    },

    comprehensionLevelClass(level: string): string {
      if (!level) {return 'comprehension-not-evaluated';}

      switch(level.toLowerCase()) {
        case 'high-level':
        case 'relational':
          return 'comprehension-high';
        case 'low-level':
        case 'multi_structural':
        case 'multistructural':
          return 'comprehension-low';
        case 'not_evaluated':
        default:
          return 'comprehension-not-evaluated';
      }
    },

    formatComprehensionLevel(level: string): string {
      if (!level) {return 'Not Evaluated';}

      switch(level.toLowerCase()) {
        case 'high-level':
        case 'relational':
          return 'High-level';
        case 'low-level':
        case 'multi_structural':
        case 'multistructural':
          return 'Low-level';
        case 'not_evaluated':
        default:
          return 'Not Evaluated';
      }
    },
    
    formatISODate(dateString: string | null): string {
      if (!dateString) {return 'Unknown';}
      const date = new Date(dateString);
      return date.toISOString();
    },
    
    async exportToCSV(): Promise<void> {
      try {
        const response = await axios.post('/api/admin/submissions/', {
          filters: {
            search: this.searchQuery.trim() || undefined,
            status: this.statusFilter || undefined,
            problem_set: this.problemSetFilter || undefined
          },
          format: 'csv'  // Request CSV format
        }, {
          responseType: 'blob'  // Important: tell axios to expect binary data
        });

        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;

        // Generate filename with timestamp and filters
        let filename = 'submissions_export';
        if (this.searchQuery) {filename += `_search-${this.searchQuery.replace(/[^a-zA-Z0-9]/g, '_')}`;}
        if (this.statusFilter) {filename += `_status-${this.statusFilter}`;}
        if (this.problemSetFilter) {filename += `_set-${this.problemSetFilter.replace(/[^a-zA-Z0-9]/g, '_')}`;}
        filename += `_${new Date().toISOString().split('T')[0]}.csv`;

        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);

        log.info('✅ Export successful');
      } catch (error) {
        log.error('❌ Export failed', { error });
        this.notify.error('Failed to export CSV. Please try again.');
      }
    },
    
    async downloadSubmissionData(submission: SubmissionDetailed): Promise<void> {
      // Guard against undefined or missing submission
      if (!submission || !submission.id) {
        log.error('Cannot download submission: invalid or missing submission data', { submission });
        this.notify.error('Unable to download submission data. Submission information is missing.');
        return;
      }

      try {
        // Fetch full submission details
        const response = await axios.get(`/api/admin/submissions/${submission.id}/`);
        const fullSubmission = response.data;
        
        // Create JSON content with full submission data (new field structure)
        const jsonContent = JSON.stringify({
          id: fullSubmission.id,
          user: fullSubmission.user,
          problem: fullSubmission.problem,
          problem_set: fullSubmission.problem_set,
          course: fullSubmission.course,
          score: fullSubmission.score,
          status: fullSubmission.status,
          submitted_at: fullSubmission.submitted_at,
          prompt: fullSubmission.prompt || null,

          // New submission fields
          code_variations: fullSubmission.code_variations || [],
          test_results: fullSubmission.test_results || [],
          passing_variations: fullSubmission.passing_variations || 0,
          total_variations: fullSubmission.total_variations || 0,
          execution_time: fullSubmission.execution_time || null,
          time_spent: fullSubmission.time_spent || null,

          // Segmentation analysis
          segmentation: fullSubmission.segmentation || null,
          comprehension_level: fullSubmission.comprehension_level || null,

          // Hint activations
          hints_activated: fullSubmission.hints_activated || [],
          hint_details: fullSubmission.hint_details || [],

          // Computed fields for convenience
          success_rate: fullSubmission.total_variations ?
            Math.round((fullSubmission.passing_variations || 0) / fullSubmission.total_variations * 100) : 0
        }, null, 2);
        
        // Create and download file
        const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `submission_${submission.id}_${submission.user}_${new Date().toISOString().split('T')[0]}.json`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
      } catch (error) {
        log.error('Error downloading submission data', { error, submissionId: submission.id });
        this.notify.error('Failed to download submission data. Please try again.');
      }
    },
    
    // Helper methods for CSV formatting
    formatCodeVariationsForCSV(codeVariations: any): string {
      if (!codeVariations || !Array.isArray(codeVariations)) {return '[]';}
      
      // Return as pretty-printed JSON string for easy analysis
      try {
        return JSON.stringify(codeVariations, null, 2).replace(/"/g, '""');
      } catch (error) {
        log.error('Error formatting code variations', { error });
        return '[]';
      }
    },
    
    formatTestResultsForCSV(testResults: any): string {
      if (!testResults || !Array.isArray(testResults)) {return '[]';}

      // Return as pretty-printed JSON string for easy analysis
      try {
        return JSON.stringify(testResults, null, 2).replace(/"/g, '""');
      } catch (error) {
        log.error('Error formatting test results', { error });
        return '[]';
      }
    },

    formatSegmentationForCSV(segmentation: any): string {
      if (!segmentation) {return 'N/A';}

      try {
        // Create a clean segmentation object without overwhelming detail
        const cleanSegmentation = {
          comprehension_level: segmentation.comprehension_level,
          confidence_score: segmentation.confidence_score,
          segment_count: segmentation.segment_count || segmentation.segments?.length,
          has_feedback: !!segmentation.feedback_message,
          improvements_count: segmentation.suggested_improvements?.length || 0,
          segments: segmentation.segments || []
        };
        return JSON.stringify(cleanSegmentation, null, 2).replace(/"/g, '""');
      } catch (error) {
        log.error('Error formatting segmentation data', { error });
        return 'Error';
      }
    },

    getBestVariationScore(submission: any): number | string {
      if (!submission.code_variations || !Array.isArray(submission.code_variations)) {
        return 'N/A';
      }

      const scores = submission.code_variations
        .map(cv => cv.tests_passed && cv.tests_total ? Math.round((cv.tests_passed / cv.tests_total) * 100) : 0)
        .filter(score => score !== undefined);

      return scores.length > 0 ? Math.max(...scores) : 'N/A';
    },

    getWorstVariationScore(submission: any): number | string {
      if (!submission.code_variations || !Array.isArray(submission.code_variations)) {
        return 'N/A';
      }

      const scores = submission.code_variations
        .map(cv => cv.tests_passed && cv.tests_total ? Math.round((cv.tests_passed / cv.tests_total) * 100) : 0)
        .filter(score => score !== undefined);

      return scores.length > 0 ? Math.min(...scores) : 'N/A';
    }
  }
})
</script>

<style scoped>
.admin-submissions {
  max-width: var(--max-width-content);
  margin: 0 auto;
  padding: var(--spacing-lg);
}

/* Page Title (matches other admin components) */
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

/* Controls Container */
.controls-container {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
}

.search-container {
  position: relative;
}

.search-input {
  width: 300px;
  padding: var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.filter-select {
  padding: var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

/* Status Container */
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

/* Table Styling (matches other admin components) */
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
  font-size: var(--font-size-sm);
}

.submissions-table th {
  background: var(--color-bg-hover);
  padding: var(--spacing-lg);
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary);
  border-bottom: 2px solid var(--color-bg-input);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-size: var(--font-size-xs);
}

.submissions-table td {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-input);
  color: var(--color-text-primary);
  vertical-align: middle;
}

.submissions-table tbody tr:hover {
  background: var(--color-bg-hover);
}

.submissions-table tbody tr:last-child td {
  border-bottom: none;
}

/* User info in table */
.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.user-avatar-small {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-circle);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-primary);
  font-weight: 600;
  font-size: var(--font-size-xs);
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.username {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Actions Cell */
.actions-cell {
  text-align: center;
}

.actions-cell .action-button {
  margin-right: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: var(--font-size-xs);
}

.actions-cell .action-button:last-child {
  margin-right: 0;
}

.view-button {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.view-button:hover {
  background: var(--color-info);
  color: var(--color-text-primary);
}

.download-button {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.download-button:hover {
  background: var(--color-success);
  color: var(--color-text-primary);
}

/* Action Button (matches other admin components) */
.action-button {
  padding: var(--spacing-md) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-base);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.export-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-colored);
}

.export-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.export-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* Table Content Styling */
.problem-set-tag {
  display: inline-block;
  padding: 2px var(--spacing-xs);
  background: var(--color-info-bg);
  color: var(--color-info);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.score-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 24px;
  border-radius: var(--radius-base);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.status-badge {
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-base);
  font-weight: 500;
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  text-align: center;
  white-space: nowrap;
  min-width: 60px;
}

.time-stamp {
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  font-weight: 400;
  white-space: nowrap;
}

/* Submission Card - Legacy (keeping for reference) */
.submission-card {
  background: var(--color-bg-hover);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-bg-input);
  transition: var(--transition-base);
  overflow: hidden;
}

.submission-card:hover {
  border-color: var(--color-primary-gradient-start);
  box-shadow: var(--shadow-colored);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  background: var(--color-bg-panel-light);
  border-bottom: 1px solid var(--color-bg-input);
}

.problem-info {
  flex: 1;
}

.problem-title {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-xs);
}

.problem-meta {
  display: flex;
  gap: var(--spacing-sm);
}

.problem-set-badge {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-info-bg);
  color: var(--color-info);
  border-radius: var(--radius-base);
  font-size: var(--font-size-xs);
  font-weight: 500;
  border: 1px solid var(--color-info);
}

.submission-score {
  display: flex;
  align-items: center;
}

.score-circle {
  width: 60px;
  height: 60px;
  border-radius: var(--radius-circle);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: var(--font-size-sm);
  border: 3px solid;
  transition: var(--transition-base);
}

.score-excellent {
  background: var(--color-success-bg);
  color: var(--color-success);
  border-color: var(--color-success);
}

.score-good {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border-color: var(--color-warning);
}

.score-fair {
  background: var(--color-info-bg);
  color: var(--color-info);
  border-color: var(--color-info);
}

.score-poor {
  background: var(--color-error-bg);
  color: var(--color-error);
  border-color: var(--color-error);
}

.score-value {
  white-space: nowrap;
}

.card-body {
  padding: var(--spacing-lg);
}

.submission-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
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

/* Comprehension Level Badge Styles */
.comprehension-badge {
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-base);
  font-weight: 500;
  font-size: var(--font-size-xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  text-align: center;
  white-space: nowrap;
  min-width: 80px;
  display: inline-block;
}

.comprehension-high {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.comprehension-low {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.comprehension-not-evaluated {
  background: var(--color-bg-hover);
  color: var(--color-text-muted);
  border: 1px solid var(--color-bg-input);
}

.submission-time {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

.card-actions {
  display: flex;
  gap: var(--spacing-sm);
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

.action-icon {
  font-size: var(--font-size-sm);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xxl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-lg);
  opacity: 0.5;
}

.empty-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.empty-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-muted);
}

/* Pagination Controls */
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-xl);
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.pagination-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.pagination-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition-base);
  min-width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pagination-btn:hover:not(:disabled) {
  border-color: var(--color-primary-gradient-start);
  background: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.pagination-btn.active {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
  font-weight: 600;
  box-shadow: var(--shadow-colored);
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
}

.page-size-select {
  padding: var(--spacing-sm);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: var(--transition-base);
}

.page-size-select:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
}

/* Responsive Design */
@media (max-width: 768px) {
  .pagination-container {
    flex-direction: column;
    align-items: stretch;
    text-align: center;
  }
  
  .pagination-controls {
    justify-content: center;
    flex-wrap: wrap;
  }
  
  .pagination-info,
  .page-size-selector {
    justify-content: center;
  }
  
  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }
  
  .header-controls {
    flex-direction: column;
    gap: var(--spacing-sm);
  }
  
  .search-input {
    width: 100%;
  }
  
  .user-header {
    padding: var(--spacing-md);
  }
  
  .user-avatar {
    width: 40px;
    height: 40px;
    font-size: var(--font-size-base);
  }
  
  .username {
    font-size: var(--font-size-base);
  }
  
  .table-header {
    grid-template-columns: 1fr;
    gap: 0;
  }
  
  .header-cell {
    display: none;
  }
  
  .header-cell:first-child {
    display: flex;
  }
  
  .header-cell:first-child::after {
    content: ' / Problem / Set / Score / Status / Time / Actions';
    font-size: var(--font-size-xs);
    opacity: 0.7;
  }
  
  .submission-row {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
  }
  
  .table-cell {
    padding: var(--spacing-xs) 0;
  }
  
  .table-cell::before {
    content: attr(data-label);
    font-weight: 600;
    font-size: var(--font-size-xs);
    color: var(--color-text-secondary);
    text-transform: uppercase;
    margin-right: var(--spacing-sm);
    min-width: 80px;
    display: inline-block;
  }
}

@media (max-width: 480px) {
  .admin-submissions {
    padding: var(--spacing-md);
  }
  
  .submissions-list {
    padding: var(--spacing-md);
  }
  
  .card-header,
  .card-body {
    padding: var(--spacing-md);
  }
  
  .header-controls {
    flex-wrap: wrap;
  }
  
  .search-input {
    min-width: 200px;
  }
  
  .export-button {
    width: 100%;
    justify-content: center;
  }
  
  .table-header {
    padding: var(--spacing-md);
  }
  
  .submission-row {
    padding: var(--spacing-md);
  }
  
  .mini-action-btn {
    width: 32px;
    height: 32px;
    font-size: 14px;
  }
}
</style>