<template>
  <transition name="modal-fade">
    <div 
      v-if="isVisible" 
      class="modal-overlay" 
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-description"
      @click.self="closeModal"
    >
      <div
        ref="modalContent"
        class="modal-content"
        :style="modalStyle"
        @keydown.esc="closeModal"
      >
        <div class="modal-header">
          <div class="header-content">
            <h3
              id="modal-title"
              class="modal-title"
            >
              🔍 Understanding Analysis
            </h3>
            <div class="header-badges">
              <span class="badge-level" :class="levelBadgeClass">
                {{ formatLevel(segmentation.comprehension_level) }} Understanding
              </span>
            </div>
          </div>
          <div class="modal-actions">
            <div class="size-controls-group">
              <span class="size-label">Size</span>
              <div class="size-controls">
                <button 
                  v-for="size in sizePresets" 
                  :key="size.name"
                  :class="['size-btn', { active: currentSize === size.name }]"
                  :title="`${size.label} view`"
                  :aria-label="`Set ${size.label.toLowerCase()} window size`"
                  @click="setModalSize(size.name)"
                >
                  {{ size.icon }}
                </button>
              </div>
            </div>
            <button
              class="action-button"
              title="Open in new tab"
              aria-label="Open understanding analysis in new tab"
              @click="openInNewTab"
            >
              <span class="icon">⬈</span>
            </button>
            <button
              class="close-button"
              title="Close (ESC)"
              aria-label="Close modal"
              @click="closeModal"
            >
              &times;
            </button>
          </div>
        </div>
        
        <div class="modal-body">
          <div class="analysis-header">
            <div class="feedback-content">
              <span class="feedback-icon">{{ getFeedbackIcon() }}</span>
              <div class="feedback-text">
                <p class="feedback-message">{{ segmentation.feedback }}</p>
                <p class="feedback-explanation">{{ getExplanation() }}</p>
              </div>
            </div>
          </div>
          
          <div class="analysis-content">
            <SegmentMapping 
              :segments="segmentation.segments"
              :reference-code="referenceCode"
              class="segment-mapping-modal"
            />
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
import SegmentMapping from './SegmentMapping.vue';

export default {
  name: 'SegmentAnalysisModal',
  components: {
    SegmentMapping
  },
  props: {
    isVisible: {
      type: Boolean,
      required: true
    },
    segmentation: {
      type: Object,
      required: true,
      validator: (value) => {
        return value && 
               typeof value.segment_count === 'number' &&
               typeof value.comprehension_level === 'string' &&
               Array.isArray(value.segments);
      }
    },
    referenceCode: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      lastFocusedElement: null,
      escListenerAdded: false,
      currentSize: 'medium',
      sizePresets: [
        { name: 'small', label: 'Small', icon: '◻', width: '900px', height: '700px' },
        { name: 'medium', label: 'Medium', icon: '◼', width: '1400px', height: '900px' },
        { name: 'large', label: 'Large', icon: '⬛', width: '95%', height: '90vh' },
        { name: 'fullscreen', label: 'Fullscreen', icon: '⛶', width: '100%', height: '100vh' }
      ]
    };
  },

  computed: {
    modalStyle() {
      const preset = this.sizePresets.find(s => s.name === this.currentSize);
      if (!preset) return {};
      
      return {
        '--modal-width': preset.width,
        '--modal-height': preset.height,
        '--modal-max-width': preset.name === 'fullscreen' ? '100%' : preset.width,
        '--modal-max-height': preset.name === 'fullscreen' ? '100%' : preset.height,
      };
    },

    levelBadgeClass() {
      return `badge-${this.segmentation.comprehension_level.replace('_', '-')}`;
    }
  },

  watch: {
    isVisible(newVal) {
      if (newVal) {
        // Add ESC key listener only if not already added
        if (!this.escListenerAdded) {
          document.addEventListener('keydown', this.handleEscKey);
          this.escListenerAdded = true;
        }
        // Focus management
        this.$nextTick(() => {
          this.trapFocus();
          this.focusFirstElement();
        });
      } else {
        // Remove ESC key listener if it was added
        if (this.escListenerAdded) {
          document.removeEventListener('keydown', this.handleEscKey);
          this.escListenerAdded = false;
        }
        // Restore focus to trigger element
        if (this.lastFocusedElement) {
          this.lastFocusedElement.focus();
        }
      }
    }
  },

  created() {
    // Store the currently focused element before modal opens
    this.lastFocusedElement = document.activeElement;
    // Load size preference
    const savedSize = localStorage.getItem('segment-analysis-modal-size');
    if (savedSize && this.sizePresets.find(s => s.name === savedSize)) {
      this.currentSize = savedSize;
    }
  },

  beforeUnmount() {
    // Clean up ESC key listener if it was added
    if (this.escListenerAdded) {
      document.removeEventListener('keydown', this.handleEscKey);
      this.escListenerAdded = false;
    }
    // Clean up focus trap
    if (this._focusTrapHandler && this.$refs.modalContent) {
      this.$refs.modalContent.removeEventListener('keydown', this._focusTrapHandler);
    }
  },

  methods: {
    closeModal() {
      this.$emit('close');
    },

    handleEscKey(e) {
      if (e.key === 'Escape') {
        this.closeModal();
      }
    },

    openInNewTab() {
      // Create a new window with the segment analysis
      const newWindow = window.open('', '_blank', 'width=1200,height=800');
      if (newWindow) {
        newWindow.document.write(`
          <html>
            <head>
              <title>Understanding Analysis - ${this.formatLevel(this.segmentation.comprehension_level)}</title>
              <style>
                body { font-family: Inter, system-ui, sans-serif; margin: 20px; }
                .header { margin-bottom: 20px; }
                .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 8px; }
                .segments { margin: 20px 0; }
                .segment { margin: 10px 0; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
                .code { font-family: Monaco, monospace; background: #f5f5f5; padding: 10px; border-radius: 4px; }
              </style>
            </head>
            <body>
              <div class="header">
                <h1>🔍 Understanding Analysis</h1>
                <span class="badge">${this.formatLevel(this.segmentation.comprehension_level)} Understanding</span>
                <p><strong>Feedback:</strong> ${this.segmentation.feedback}</p>
                <p><strong>Explanation:</strong> ${this.getExplanation()}</p>
              </div>
              <div class="segments">
                <h2>Segments</h2>
                ${this.segmentation.segments.map(segment => `
                  <div class="segment">
                    <strong>Segment ${segment.id}:</strong> ${segment.text}
                    <br><small>Lines: ${segment.code_lines.join(', ')}</small>
                  </div>
                `).join('')}
              </div>
              <div class="code">
                <h2>Reference Code</h2>
                <pre>${this.referenceCode}</pre>
              </div>
            </body>
          </html>
        `);
      }
      this.closeModal();
    },

    focusFirstElement() {
      const modalContent = this.$refs.modalContent;
      if (!modalContent) return;
      
      // Find first focusable element
      const focusableElements = modalContent.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      
      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      }
    },

    trapFocus() {
      const modalContent = this.$refs.modalContent;
      if (!modalContent) return;
      
      const handleTabKey = (e) => {
        const focusableElements = modalContent.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        if (e.key === 'Tab') {
          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      };
      
      modalContent.addEventListener('keydown', handleTabKey);
      
      // Store the handler for cleanup
      this._focusTrapHandler = handleTabKey;
    },

    setModalSize(sizeName) {
      this.currentSize = sizeName;
      // Save preference
      localStorage.setItem('segment-analysis-modal-size', sizeName);
      
      // Handle fullscreen mode
      if (sizeName === 'fullscreen') {
        this.$refs.modalContent?.classList.add('fullscreen-mode');
        document.querySelector('.modal-overlay')?.classList.add('fullscreen-overlay');
      } else {
        this.$refs.modalContent?.classList.remove('fullscreen-mode');
        document.querySelector('.modal-overlay')?.classList.remove('fullscreen-overlay');
      }
    },

    getFeedbackIcon() {
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return '🎯';
        case 'transitional':
          return '👍';
        case 'multi_structural':
          return '🔍';
        default:
          return '📝';
      }
    },
    
    formatLevel(level) {
      switch (level) {
        case 'relational':
          return 'Excellent';
        case 'transitional':
          return 'Good';
        case 'multi_structural':
          return 'Detailed';
        default:
          return 'Unknown';
      }
    },
    
    getExplanation() {
      switch (this.segmentation.comprehension_level) {
        case 'relational':
          return `You focused on the overall purpose. This shows strong conceptual understanding.`;
        case 'transitional':
          return `You identified key steps. Good balance between detail and big picture.`;
        case 'multi_structural':
          return `You provided line-by-line detail. Try focusing on the main goal instead.`;
        default:
          return '';
      }
    }
  }
};
</script>

<style scoped>
/* Modal Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .modal-content {
  transition: transform 0.3s ease;
}

.modal-fade-enter-from .modal-content {
  transform: scale(0.9);
}

/* Modal Structure */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.modal-overlay.fullscreen-overlay {
  padding: 0;
}

.modal-content {
  background-color: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: var(--modal-width, 95%);
  height: var(--modal-height, 800px);
  max-width: var(--modal-max-width, 1400px);
  max-height: var(--modal-max-height, 90vh);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: var(--transition-base);
}

.modal-content.fullscreen-mode {
  border-radius: 0;
  width: 100% !important;
  height: 100% !important;
  max-width: 100% !important;
  max-height: 100% !important;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--color-bg-header);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 2px solid var(--color-bg-input);
}

.header-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.modal-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.header-badges {
  display: flex;
  gap: var(--spacing-sm);
}

.badge-count,
.badge-level {
  padding: 2px var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.badge-count {
  background: var(--color-bg-input);
  color: var(--color-text-muted);
}

.badge-level.badge-relational {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.badge-level.badge-transitional {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.badge-level.badge-multi-structural {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.modal-actions {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}

.size-controls-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  transition: var(--transition-fast);
}

.size-controls-group:hover .size-label {
  opacity: 1;
  color: var(--color-text-secondary);
}

.size-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  font-weight: 500;
  user-select: none;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  opacity: 0.8;
}

.size-controls {
  display: flex;
  gap: var(--spacing-xs);
  background: var(--color-bg-dark);
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
}

.size-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  width: 28px;
  height: 28px;
  border-radius: var(--radius-xs);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
  font-size: 14px;
  padding: 0;
}

.size-btn:hover {
  background: var(--color-bg-input);
  color: var(--color-text-secondary);
}

.size-btn.active {
  background: var(--color-primary);
  color: var(--color-text-primary);
}

.action-button {
  background: var(--color-bg-input);
  border: none;
  color: var(--color-text-secondary);
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
}

.action-button:hover {
  background: var(--color-primary);
  color: var(--color-text-primary);
  transform: translateY(-1px);
}

.icon {
  font-size: 18px;
}

.close-button {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  font-size: 24px;
  cursor: pointer;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);
}

.close-button:hover {
  background: var(--color-error-bg);
  color: var(--color-error);
}

.modal-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.analysis-header {
  padding: var(--spacing-lg);
  background: var(--color-bg-hover);
  border-bottom: 1px solid var(--color-bg-border);
}

.feedback-content {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-start;
}

.feedback-icon {
  font-size: var(--font-size-base);
  flex-shrink: 0;
}

.feedback-text {
  flex: 1;
}

.feedback-message {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
  line-height: 1.5;
}

.feedback-explanation {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.6;
}

.analysis-content {
  flex: 1;
  overflow: hidden;
}

.segment-mapping-modal {
  height: 100%;
}

/* Responsive */
@media (max-width: 1024px) {
  .modal-overlay {
    padding: var(--spacing-md);
  }
  
  .modal-content {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
  }
  
  .size-controls-group {
    display: none; /* Hide size controls on tablet */
  }
}

@media (max-width: 768px) {
  .modal-overlay {
    padding: 0;
  }
  
  .modal-content {
    border-radius: 0;
  }
  
  .modal-header {
    padding: var(--spacing-sm) var(--spacing-md);
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }
  
  .header-content {
    flex: 1;
    min-width: 0;
  }
  
  .header-badges {
    flex-wrap: wrap;
  }
  
  .modal-title {
    font-size: var(--font-size-base);
  }
  
  .modal-actions {
    gap: var(--spacing-sm);
  }
  
  .analysis-header {
    padding: var(--spacing-md);
  }
}
</style>