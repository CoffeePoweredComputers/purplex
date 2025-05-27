<template>
  <div class="modal-overlay" @click="closeModal">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h2>Add New Problem Set</h2>
        <button class="modal-close" @click="closeModal">&times;</button>
      </div>
      
      <div class="modal-body">
        <form @submit.prevent="submitProblemSet">
          <div class="form-group">
            <label for="problemSetTitle">Title *</label>
            <input 
              type="text" 
              id="problemSetTitle" 
              v-model="problemSet.title" 
              class="form-input"
              placeholder="e.g., Advanced String Algorithms"
              required
              @input="generateSlug"
            >
          </div>

          <div class="form-group">
            <label for="problemSetSlug">URL Slug *</label>
            <input 
              type="text" 
              id="problemSetSlug" 
              v-model="problemSet.slug" 
              class="form-input"
              placeholder="e.g., advanced-string-algorithms"
              pattern="[a-z0-9-]+"
              title="Only lowercase letters, numbers, and hyphens allowed"
              required
            >
            <small class="form-help">Used in URLs. Will be auto-generated from title if left empty.</small>
          </div>

          <div class="form-group">
            <label for="problemSetDescription">Description *</label>
            <textarea 
              id="problemSetDescription" 
              v-model="problemSet.description" 
              class="form-textarea"
              rows="4"
              placeholder="Describe what this problem set covers and what students will learn..."
              required
            ></textarea>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input 
                type="checkbox" 
                v-model="problemSet.is_public"
                class="form-checkbox"
              >
              <span class="checkbox-text">Make this problem set public</span>
            </label>
            <small class="form-help">Public problem sets are visible to all students</small>
          </div>

          <div class="form-group">
            <label for="problemSetIcon">Icon (optional)</label>
            <input 
              type="file" 
              id="problemSetIcon" 
              @change="handleIconUpload"
              class="form-file"
              accept="image/*"
            >
            <small class="form-help">Upload an icon for the problem set (PNG, JPG, or GIF)</small>
            
            <!-- Icon preview -->
            <div v-if="iconPreview" class="icon-preview">
              <img :src="iconPreview" alt="Icon preview" class="preview-image">
              <button type="button" @click="removeIcon" class="remove-icon-btn">&times;</button>
            </div>
          </div>

          <!-- Error display -->
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <!-- Validation errors -->
          <div v-if="validationErrors.length > 0" class="validation-errors">
            <h4>Please fix the following errors:</h4>
            <ul>
              <li v-for="error in validationErrors" :key="error">{{ error }}</li>
            </ul>
          </div>
        </form>
      </div>
      
      <div class="modal-footer">
        <button type="button" class="action-button cancel-button" @click="closeModal">
          Cancel
        </button>
        <button 
          type="button" 
          class="action-button submit-button" 
          @click="submitProblemSet"
          :disabled="isSubmitting"
        >
          {{ isSubmitting ? 'Creating...' : 'Create Problem Set' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'AddProblemSetModal',
  data() {
    return {
      problemSet: {
        title: '',
        slug: '',
        description: '',
        is_public: true,
        icon: null
      },
      iconPreview: null,
      isSubmitting: false,
      error: null,
      validationErrors: []
    };
  },
  methods: {
    closeModal() {
      this.resetForm();
      this.$emit('close');
    },

    resetForm() {
      this.problemSet = {
        title: '',
        slug: '',
        description: '',
        is_public: true,
        icon: null
      };
      this.iconPreview = null;
      this.isSubmitting = false;
      this.error = null;
      this.validationErrors = [];
    },

    generateSlug() {
      if (!this.problemSet.slug) {
        // Auto-generate slug from title
        this.problemSet.slug = this.problemSet.title
          .toLowerCase()
          .replace(/[^a-z0-9\s-]/g, '') // Remove special characters
          .replace(/\s+/g, '-') // Replace spaces with hyphens
          .replace(/-+/g, '-') // Replace multiple hyphens with single
          .trim();
      }
    },

    handleIconUpload(event) {
      const file = event.target.files[0];
      if (file) {
        // Validate file type
        const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
          this.error = 'Please upload a valid image file (PNG, JPG, or GIF)';
          return;
        }

        // Validate file size (5MB max)
        const maxSize = 5 * 1024 * 1024; // 5MB in bytes
        if (file.size > maxSize) {
          this.error = 'Image file must be smaller than 5MB';
          return;
        }

        this.problemSet.icon = file;
        this.error = null;

        // Create preview
        const reader = new FileReader();
        reader.onload = (e) => {
          this.iconPreview = e.target.result;
        };
        reader.readAsDataURL(file);
      }
    },

    removeIcon() {
      this.problemSet.icon = null;
      this.iconPreview = null;
      // Clear the file input
      const fileInput = document.getElementById('problemSetIcon');
      if (fileInput) {
        fileInput.value = '';
      }
    },

    validateForm() {
      this.validationErrors = [];

      if (!this.problemSet.title.trim()) {
        this.validationErrors.push('Title is required');
      }

      if (!this.problemSet.slug.trim()) {
        this.validationErrors.push('URL slug is required');
      } else if (!/^[a-z0-9-]+$/.test(this.problemSet.slug)) {
        this.validationErrors.push('URL slug can only contain lowercase letters, numbers, and hyphens');
      }

      if (!this.problemSet.description.trim()) {
        this.validationErrors.push('Description is required');
      }

      return this.validationErrors.length === 0;
    },

    async submitProblemSet() {
      if (this.isSubmitting) return;

      // Clear previous errors
      this.error = null;
      this.validationErrors = [];

      // Validate form
      if (!this.validateForm()) {
        return;
      }

      try {
        this.isSubmitting = true;

        // Create FormData for file upload
        const formData = new FormData();
        formData.append('title', this.problemSet.title.trim());
        formData.append('slug', this.problemSet.slug.trim());
        formData.append('description', this.problemSet.description.trim());
        formData.append('is_public', this.problemSet.is_public ? 'true' : 'false');
        
        if (this.problemSet.icon) {
          formData.append('icon', this.problemSet.icon);
        }

        const response = await axios.post('/api/admin/problem-sets/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        this.$emit('problem-set-added', response.data);
        this.closeModal();
      } catch (error) {
        console.error('Error creating problem set:', error);
        
        if (error.response && error.response.data) {
          // Handle validation errors from backend
          const errorData = error.response.data;
          if (errorData.details || errorData.errors) {
            this.handleBackendErrors(errorData.details || errorData.errors);
          } else if (errorData.error) {
            this.error = errorData.error;
          } else {
            this.error = 'Failed to create problem set. Please try again.';
          }
        } else {
          this.error = 'Network error. Please check your connection and try again.';
        }
      } finally {
        this.isSubmitting = false;
      }
    },

    handleBackendErrors(errors) {
      this.validationErrors = [];
      
      if (typeof errors === 'object') {
        for (const [field, messages] of Object.entries(errors)) {
          if (Array.isArray(messages)) {
            messages.forEach(msg => {
              this.validationErrors.push(`${field}: ${msg}`);
            });
          } else {
            this.validationErrors.push(`${field}: ${messages}`);
          }
        }
      } else {
        this.error = errors;
      }
    },

    handleEscape(event) {
      if (event.key === 'Escape') {
        this.closeModal();
      }
    }
  },

  mounted() {
    // Add ESC key listener
    document.addEventListener('keydown', this.handleEscape);
  },

  beforeUnmount() {
    // Remove ESC key listener
    document.removeEventListener('keydown', this.handleEscape);
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  border: 2px solid var(--color-bg-input);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xl);
  border-bottom: 2px solid var(--color-bg-input);
}

.modal-header h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-base);
  transition: var(--transition-base);
}

.modal-close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.modal-body {
  padding: var(--spacing-xl);
}

.modal-footer {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  padding: var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
}

.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-primary);
  font-weight: 600;
}

.form-input, .form-textarea {
  width: 100%;
  padding: var(--spacing-md);
  border: 2px solid var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.form-input:focus, .form-textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.form-textarea {
  resize: vertical;
  min-height: 100px;
}

.form-file {
  width: 100%;
  padding: var(--spacing-sm);
  border: 2px dashed var(--color-bg-input);
  border-radius: var(--radius-base);
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-base);
}

.form-file:hover {
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.form-help {
  display: block;
  margin-top: var(--spacing-xs);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  font-weight: normal !important;
}

.form-checkbox {
  margin: 0;
}

.checkbox-text {
  color: var(--color-text-primary);
}

.icon-preview {
  position: relative;
  display: inline-block;
  margin-top: var(--spacing-md);
}

.preview-image {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: var(--radius-base);
  border: 2px solid var(--color-bg-input);
}

.remove-icon-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: var(--color-error);
  color: white;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.remove-icon-btn:hover {
  background: var(--color-error);
  transform: scale(1.1);
}

.error-message {
  padding: var(--spacing-md);
  background: var(--color-error-bg);
  border-radius: var(--radius-base);
  color: var(--color-error-text);
  border: 1px solid var(--color-error);
  margin-bottom: var(--spacing-md);
}

.validation-errors {
  padding: var(--spacing-md);
  background: var(--color-error-bg);
  border-radius: var(--radius-base);
  color: var(--color-error-text);
  border: 1px solid var(--color-error);
  margin-bottom: var(--spacing-md);
}

.validation-errors h4 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: var(--font-size-base);
}

.validation-errors ul {
  margin: 0;
  padding-left: var(--spacing-lg);
}

.validation-errors li {
  margin-bottom: var(--spacing-xs);
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

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}

.submit-button {
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  box-shadow: var(--shadow-colored);
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.cancel-button {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-bg-border);
}

.cancel-button:hover {
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

/* Responsive Design */
@media (max-width: 768px) {
  .modal-content {
    width: 95%;
    margin: var(--spacing-md);
  }

  .modal-footer {
    flex-direction: column;
  }

  .action-button {
    width: 100%;
    justify-content: center;
  }
}
</style>