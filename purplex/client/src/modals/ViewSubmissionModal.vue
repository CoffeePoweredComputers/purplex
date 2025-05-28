<template>
  <div v-if="isVisible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2 class="modal-title">Submission Details</h2>
        <button class="modal-close-btn" @click="$emit('close')">&times;</button>
      </div>
      
      <div class="modal-body" v-if="submission">
        <div class="submission-info">
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">User:</span>
              <span class="info-value">{{ submission.user }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Problem:</span>
              <span class="info-value">{{ submission.problem }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Problem Set:</span>
              <span class="info-value">{{ submission.problem_set }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Score:</span>
              <div class="score-indicator" :class="getScoreClass(submission.score)">
                {{ submission.score }}%
              </div>
            </div>
            <div class="info-item">
              <span class="info-label">Status:</span>
              <span class="status-badge" :class="submissionStatusClass(submission.status)">
                {{ submission.status }}
              </span>
            </div>
            <div class="info-item">
              <span class="info-label">Submitted:</span>
              <span class="info-value">{{ formatDetailedDate(submission.created_at) }}</span>
            </div>
          </div>
        </div>
        
        <div class="code-section" v-if="submission.user_solution">
          <h3 class="section-title">User Solution</h3>
          <pre class="code-block"><code>{{ prettyPrintContent(submission.user_solution) }}</code></pre>
        </div>
        
        <div class="feedback-section" v-if="submission.feedback">
          <h3 class="section-title">Feedback</h3>
          <div class="feedback-content">{{ prettyPrintContent(submission.feedback) }}</div>
        </div>
        
        <div class="prompt-section" v-if="submission.prompt">
          <h3 class="section-title">Prompt</h3>
          <div class="prompt-content">{{ submission.prompt }}</div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button class="action-button download-button" @click="$emit('download', submission)">
          Download Data
        </button>
        <button class="action-button cancel-button" @click="$emit('close')">
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ViewSubmissionModal',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    submission: {
      type: Object,
      default: null
    }
  },
  emits: ['close', 'download'],
  methods: {
    getScoreClass(score) {
      if (score >= 80) return 'score-excellent';
      if (score >= 60) return 'score-good';
      if (score >= 40) return 'score-fair';
      return 'score-poor';
    },
    
    submissionStatusClass(status) {
      switch(status?.toLowerCase()) {
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
    
    formatDetailedDate(dateString) {
      if (!dateString) return 'Unknown';
      const date = new Date(dateString);
      return date.toLocaleString();
    },
    
    prettyPrintContent(content) {
      if (!content) return '';
      
      try {
        // Try to parse as JSON first
        const parsed = JSON.parse(content);
        return JSON.stringify(parsed, null, 2);
      } catch (e) {
        // If it's not JSON, check if it looks like a stringified JSON
        if (typeof content === 'string' && (content.trim().startsWith('{') || content.trim().startsWith('['))) {
          try {
            const parsed = JSON.parse(content);
            return JSON.stringify(parsed, null, 2);
          } catch (e2) {
            // Not valid JSON, return as-is
            return content;
          }
        }
        // Return content as-is if it's not JSON
        return content;
      }
    }
  }
}
</script>

<style scoped>
/* Modal Overlay */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 2px solid var(--color-bg-input);
  max-width: 90vw;
  max-height: 90vh;
  width: 800px;
  overflow: hidden;
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Modal Header */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-xl);
  background: var(--color-bg-hover);
  border-bottom: 2px solid var(--color-bg-input);
}

.modal-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.modal-close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-base);
  transition: var(--transition-base);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close-btn:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

/* Modal Body */
.modal-body {
  padding: var(--spacing-xl);
  max-height: 60vh;
  overflow-y: auto;
}

.submission-info {
  margin-bottom: var(--spacing-lg);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.info-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  font-weight: 500;
}

/* Score and Status Indicators */
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

.score-excellent {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.score-good {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}

.score-fair {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid var(--color-info);
}

.score-poor {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error);
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

/* Content Sections */
.section-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: var(--spacing-lg) 0 var(--spacing-md) 0;
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-bg-input);
}

.code-section {
  margin: var(--spacing-lg) 0;
}

.code-block {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
  text-align: left;
}

.feedback-section,
.prompt-section {
  margin: var(--spacing-lg) 0;
}

.feedback-content,
.prompt-content {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-wrap: break-word;
  text-align: left;
}

/* Modal Footer */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  background: var(--color-bg-hover);
  border-top: 1px solid var(--color-bg-input);
}

/* Action Buttons */
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

.download-button {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}

.download-button:hover {
  background: var(--color-success);
  color: var(--color-text-primary);
}

.cancel-button {
  background: var(--color-bg-input);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.cancel-button:hover {
  background: var(--color-bg-border);
  color: var(--color-text-primary);
}

/* Mobile Responsiveness */
@media (max-width: 768px) {
  .modal-content {
    width: 95vw;
    margin: var(--spacing-md);
  }
  
  .modal-header,
  .modal-footer {
    padding: var(--spacing-md);
  }
  
  .modal-body {
    padding: var(--spacing-md);
  }
  
  .info-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-footer {
    flex-direction: column;
  }
  
  .modal-footer .action-button {
    width: 100%;
    justify-content: center;
  }
}
</style>