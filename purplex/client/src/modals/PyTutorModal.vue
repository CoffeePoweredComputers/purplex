<template>
  <transition name="modal-fade">
    <div 
      class="modal-overlay" 
      v-if="isVisible" 
      @click.self="closeModal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-description"
    >
      <div class="modal-content" ref="modalContent" @keydown.esc="closeModal" :style="modalStyle">
        <div class="modal-header">
          <h3 id="modal-title" class="modal-title">🔍 Step-by-Step Debugger</h3>
          <span id="modal-description" class="sr-only">Interactive Python code debugger powered by Python Tutor</span>
          <div class="modal-actions">
            <div class="size-controls-group">
              <span class="size-label">Size</span>
              <div class="size-controls">
                <button 
                  v-for="size in sizePresets" 
                  :key="size.name"
                  @click="setModalSize(size.name)"
                  :class="['size-btn', { active: currentSize === size.name }]"
                  :title="`${size.label} view`"
                  :aria-label="`Set ${size.label.toLowerCase()} window size`"
                >
                  {{ size.icon }}
                </button>
              </div>
            </div>
            <button class="action-button" @click="openInNewTab" title="Open in new tab" aria-label="Open Python Tutor in new tab">
              <span class="icon">⬈</span>
            </button>
            <button class="close-button" @click="closeModal" title="Close (ESC)" aria-label="Close modal">&times;</button>
          </div>
        </div>
        <div class="modal-body">
          <div v-if="loading" class="loading-container">
            <div class="loading-spinner"></div>
            <p>Loading debugger...</p>
          </div>
          <div v-show="!loading && !urlTooLong" v-if="pythonTutorUrl && !urlTooLong" class="iframe-wrapper">
            <div class="iframe-header">
              <span class="iframe-info">Python Tutor Visualizer</span>
              <button 
                @click="toggleTheme" 
                class="theme-toggle"
                :title="`Switch to ${isDarkWrapper ? 'light' : 'dark'} background`"
              >
                <span v-if="isDarkWrapper">🌞</span>
                <span v-else>🌙</span>
              </button>
            </div>
            <iframe
              :src="pythonTutorUrl"
              :title="iframeTitle"
              width="100%"
              height="100%"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              referrerpolicy="no-referrer"
              @load="onIframeLoad"
              @error="onIframeError"
              class="debugger-iframe"
              :class="{ 'dark-wrapper': isDarkWrapper }"
            ></iframe>
          </div>
          <div v-if="urlTooLong" class="url-warning">
            <p>⚠️ Code is too large for direct debugging</p>
            <p class="warning-details">The code exceeds the URL length limit ({{ urlLength }} characters)</p>
            <div class="warning-actions">
              <button @click="copyAndOpen" class="action-btn primary">
                <span>📋</span> Copy Code & Open Python Tutor
              </button>
              <button @click="closeModal" class="action-btn secondary">
                Cancel
              </button>
            </div>
          </div>
          <div v-if="error" class="error-message">
            <p class="error-icon">❌</p>
            <h4 class="error-title">{{ getErrorTitle() }}</h4>
            <p class="error-description">{{ errorMessage }}</p>
            <div class="error-actions">
              <button @click="retry" class="retry-button">
                <span>🔄</span> Try Again
              </button>
              <a 
                v-if="errorType === 'TIMEOUT' || errorType === 'NETWORK'"
                href="https://pythontutor.com"
                target="_blank"
                class="error-link"
              >
                Open Python Tutor directly
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script>
export default {
  name: 'PyTutorModal',
  props: {
    isVisible: {
      type: Boolean,
      required: true,
    },
    pythonTutorUrl: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      loading: true,
      error: false,
      errorType: null,
      errorMessage: '',
      urlTooLong: false,
      urlLength: 0,
      iframeTitle: 'Python Tutor Code Visualizer',
      URL_LIMIT: 2000, // Safe URL length limit
      lastFocusedElement: null,
      loadingTimeout: null,
      TIMEOUT_DURATION: 10000, // 10 seconds
      escListenerAdded: false,
      isDarkWrapper: false,
      currentSize: 'medium',
      sizePresets: [
        { name: 'small', label: 'Small', icon: '◻', width: '800px', height: '600px' },
        { name: 'medium', label: 'Medium', icon: '◼', width: '1200px', height: '800px' },
        { name: 'large', label: 'Large', icon: '⬛', width: '95%', height: '90vh' },
        { name: 'fullscreen', label: 'Fullscreen', icon: '⛶', width: '100%', height: '100vh' }
      ],
    };
  },
  created() {
    // Store the currently focused element before modal opens
    this.lastFocusedElement = document.activeElement;
    // Load theme preference
    const savedTheme = localStorage.getItem('pytutor-dark-wrapper');
    if (savedTheme !== null) {
      this.isDarkWrapper = savedTheme === 'true';
    }
    // Load size preference
    const savedSize = localStorage.getItem('pytutor-modal-size');
    if (savedSize && this.sizePresets.find(s => s.name === savedSize)) {
      this.currentSize = savedSize;
    }
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
  },
  watch: {
    isVisible(newVal) {
      if (newVal) {
        this.loading = true;
        this.error = false;
        this.errorType = null;
        this.errorMessage = '';
        this.checkUrlLength();
        
        // Start loading timeout
        if (!this.urlTooLong) {
          this.startLoadingTimeout();
        }
        
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
        this.clearLoadingTimeout();
        // Restore focus to trigger element
        if (this.lastFocusedElement) {
          this.lastFocusedElement.focus();
        }
      }
    },
    pythonTutorUrl(newVal) {
      if (newVal) {
        this.checkUrlLength();
      }
    },
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
    onIframeLoad() {
      this.clearLoadingTimeout();
      this.loading = false;
      this.error = false;
      this.$emit('debugger-loaded');
    },
    onIframeError(event) {
      this.clearLoadingTimeout();
      this.loading = false;
      this.error = true;
      this.errorType = 'NETWORK';
      this.errorMessage = 'Unable to connect to Python Tutor. Please check your internet connection.';
      this.$emit('debugger-error', { type: this.errorType, message: this.errorMessage });
    },
    retry() {
      this.loading = true;
      this.error = false;
      this.errorType = null;
      this.errorMessage = '';
      this.startLoadingTimeout();
      // Force iframe reload
      const iframe = this.$el.querySelector('.debugger-iframe');
      if (iframe) {
        iframe.src = iframe.src;
      }
    },
    openInNewTab() {
      // Convert embed URL to regular URL for better experience in new tab
      const regularUrl = this.pythonTutorUrl.replace('/iframe-embed.html', '/visualize.html');
      window.open(regularUrl, '_blank');
      this.closeModal();
    },
    checkUrlLength() {
      this.urlLength = this.pythonTutorUrl.length;
      this.urlTooLong = this.urlLength > this.URL_LIMIT;
      if (this.urlTooLong) {
        this.loading = false;
      }
    },
    copyAndOpen() {
      // Extract code from URL
      const urlParams = new URL(this.pythonTutorUrl).hash.substring(1);
      const params = new URLSearchParams(urlParams);
      const code = params.get('code');
      
      if (code) {
        // Copy to clipboard
        navigator.clipboard.writeText(code).then(() => {
          // Open Python Tutor in new tab
          window.open('https://pythontutor.com/visualize.html#mode=edit', '_blank');
          this.closeModal();
        }).catch(err => {
          console.error('Failed to copy code:', err);
          // Fallback: just open Python Tutor
          window.open('https://pythontutor.com/visualize.html#mode=edit', '_blank');
        });
      }
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
    startLoadingTimeout() {
      this.clearLoadingTimeout();
      this.loadingTimeout = setTimeout(() => {
        if (this.loading) {
          this.loading = false;
          this.error = true;
          this.errorType = 'TIMEOUT';
          this.errorMessage = 'Python Tutor is taking too long to load. This might be due to slow internet or service issues.';
          this.$emit('debugger-error', { type: this.errorType, message: this.errorMessage });
        }
      }, this.TIMEOUT_DURATION);
    },
    clearLoadingTimeout() {
      if (this.loadingTimeout) {
        clearTimeout(this.loadingTimeout);
        this.loadingTimeout = null;
      }
    },
    getErrorTitle() {
      switch (this.errorType) {
        case 'TIMEOUT':
          return 'Loading Timeout';
        case 'NETWORK':
          return 'Connection Error';
        default:
          return 'Failed to Load Debugger';
      }
    },
    toggleTheme() {
      this.isDarkWrapper = !this.isDarkWrapper;
      // Save preference to localStorage
      localStorage.setItem('pytutor-dark-wrapper', this.isDarkWrapper);
    },
    setModalSize(sizeName) {
      this.currentSize = sizeName;
      // Save preference
      localStorage.setItem('pytutor-modal-size', sizeName);
      
      // Handle fullscreen mode
      if (sizeName === 'fullscreen') {
        this.$refs.modalContent?.classList.add('fullscreen-mode');
        document.querySelector('.modal-overlay')?.classList.add('fullscreen-overlay');
      } else {
        this.$refs.modalContent?.classList.remove('fullscreen-mode');
        document.querySelector('.modal-overlay')?.classList.remove('fullscreen-overlay');
      }
    },
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
    // Clear any pending timeouts
    this.clearLoadingTimeout();
  },
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

/* Accessibility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
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

.modal-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
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
  position: relative;
  background: var(--color-bg-dark);
  overflow: hidden;
}

/* Loading State */
.loading-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: var(--color-text-secondary);
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 3px solid var(--color-bg-input);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-circle);
  animation: spin 1s linear infinite;
  margin: 0 auto var(--spacing-md);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  max-width: 400px;
  padding: var(--spacing-xl);
}

.error-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-md);
}

.error-title {
  color: var(--color-error);
  font-size: var(--font-size-md);
  margin-bottom: var(--spacing-sm);
}

.error-description {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
  line-height: 1.5;
}

.error-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}

.retry-button {
  background: var(--color-primary);
  color: var(--color-text-primary);
  border: none;
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition-fast);
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.retry-button:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.error-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: var(--font-size-sm);
  transition: var(--transition-fast);
}

.error-link:hover {
  color: var(--color-primary-hover);
  text-decoration: underline;
}

/* Iframe Wrapper */
.iframe-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: white;
  overflow: hidden;
}

.iframe-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-panel);
  border-bottom: 1px solid var(--color-bg-border);
}

.iframe-info {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.theme-toggle {
  background: var(--color-bg-input);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-fast);
  font-size: 16px;
}

.theme-toggle:hover {
  background: var(--color-bg-hover);
  transform: scale(1.05);
}

/* Iframe */
.debugger-iframe {
  width: 100%;
  height: 100%;
  background: white;
  border: 0;
  transition: filter var(--transition-base);
}

.debugger-iframe.dark-wrapper {
  filter: invert(0.88) hue-rotate(180deg);
  background: var(--color-bg-dark);
}

/* URL Warning */
.url-warning {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  padding: var(--spacing-xl);
  background: var(--color-bg-panel);
  border-radius: var(--radius-base);
  box-shadow: var(--shadow-base);
  max-width: 500px;
}

.url-warning p {
  color: var(--color-warning);
  margin-bottom: var(--spacing-md);
  font-size: var(--font-size-md);
}

.warning-details {
  color: var(--color-text-secondary) !important;
  font-size: var(--font-size-sm) !important;
}

.warning-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: center;
  margin-top: var(--spacing-lg);
}

.action-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition-fast);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.action-btn.primary {
  background: var(--color-primary);
  color: var(--color-text-primary);
}

.action-btn.primary:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: var(--color-bg-input);
  color: var(--color-text-secondary);
  border-color: var(--color-bg-border);
}

.action-btn.secondary:hover {
  background: var(--color-bg-hover);
}

/* Responsive */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 0;
  }
  
  .modal-content {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    border-radius: 0;
  }
  
  .modal-header {
    padding: var(--spacing-sm) var(--spacing-md);
  }
  
  .modal-title {
    font-size: var(--font-size-base);
  }
  
  .size-controls-group {
    display: none; /* Hide size controls on mobile */
  }
  
  .modal-actions {
    gap: var(--spacing-sm);
  }
}
</style>
