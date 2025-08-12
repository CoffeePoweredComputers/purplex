<template>
  <div
    v-if="hasAnyHints"
    class="hint-button-container"
  >
    <button 
      class="hint-button"
      :disabled="loading || !hasUnlockedHints"
      :class="{ 'pulse': hasNewUnlockedHints }"
      @click="toggleHintMenu"
    >
      <span class="hint-icon">💡</span>
      <span class="hint-text">Hints</span>
      <span
        v-if="availableHintsCount > 0"
        class="hint-badge"
      >{{ availableHintsCount }}</span>
    </button>
    
    <transition name="slide">
      <div
        v-if="showMenu && hasUnlockedHints" 
        class="hint-menu"
        :style="{ top: menuPosition.top, left: menuPosition.left }"
      >
        <div class="hint-menu-header">
          <h4>Available Hints</h4>
          <button
            class="close-btn"
            @click="showMenu = false"
          >
            ×
          </button>
        </div>
        
        <div class="hint-list">
          <div
            v-if="availableHints.length === 0"
            class="no-hints-message"
          >
            <p>No hints are configured for this problem.</p>
          </div>
          <div 
            v-for="hint in availableHints"
            v-else 
            :key="hint.type"
            class="hint-item"
            :class="{ 
              'unlocked': hint.unlocked, 
              'used': isHintUsed(hint.type),
              'active': isHintActive(hint.type),
              'locked': !hint.unlocked 
            }"
          >
            <div class="hint-header">
              <span class="hint-type-icon">{{ getHintIcon(hint.type) }}</span>
              <div class="hint-info">
                <h5>{{ hint.title }}</h5>
                <p class="hint-description">
                  {{ hint.description }}
                </p>
                <p
                  v-if="!hint.unlocked"
                  class="hint-requirement"
                >
                  Requires {{ getMinAttemptsForHint(hint.type) }} attempts ({{ currentAttempts }}/{{ getMinAttemptsForHint(hint.type) }})
                </p>
              </div>
              <div class="hint-controls">
                <label
                  v-if="hint.unlocked"
                  class="hint-toggle"
                >
                  <input 
                    type="checkbox" 
                    :checked="isHintActive(hint.type)"
                    class="hint-checkbox"
                    @change="toggleHint(hint.type)"
                  >
                  <span class="toggle-slider" />
                </label>
                <span
                  v-else
                  class="status-icon locked"
                >🔒</span>
              </div>
            </div>
            
            <transition name="expand">
              <div
                v-if="expandedHint === hint.type && hintContent[hint.type]"
                class="hint-content"
              >
                <div class="hint-content-body">
                  <p>{{ hintContent[hint.type].content }}</p>
                  <div
                    v-if="hintContent[hint.type].example"
                    class="hint-example"
                  >
                    <h6>Example:</h6>
                    <pre><code>{{ hintContent[hint.type].example }}</code></pre>
                  </div>
                </div>
              </div>
            </transition>
          </div>
        </div>
        
        <div class="hint-footer">
          <div class="hint-stats">
            <p class="hint-attempts">
              Attempts: {{ currentAttempts }}
            </p>
            <p class="hint-note">
              Next hint unlocks after {{ getMinAttemptsForNextHint() }} attempts
            </p>
          </div>
          <div
            v-if="hasAnyActiveHints"
            class="hint-actions"
          >
            <button 
              class="action-btn secondary" 
              :disabled="!hasAnyActiveHints"
              @click="showOriginalCode"
            >
              Show Original
            </button>
            <button 
              class="action-btn danger" 
              :disabled="!hasAnyActiveHints"
              @click="removeAllHints"
            >
              Clear All Hints
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script lang="ts">
import { problemService } from '@/services/problemService'
import { useNotification } from '@/composables/useNotification'
import { log } from '@/utils/logger'

export default {
  name: 'HintButton',
  props: {
    problemSlug: {
      type: String,
      required: true
    },
    courseId: {
      type: String,
      default: null
    },
    problemSetSlug: {
      type: String,
      default: null
    },
    currentAttempts: {
      type: Number,
      default: 0,
      validator: (value) => value >= 0
    }
  },
  setup() {
    const { notify } = useNotification()
    return { notify }
  },
  data() {
    return {
      showMenu: false,
      loading: false,
      availableHints: [],
      hintsUsed: [],
      hintContent: {},
      expandedHint: null,
      lastAttemptCount: 0,
      activeHints: new Set(), // Track which hints are currently applied to editor
      menuPosition: { top: 0, left: 0 } // Position for fixed positioning
    }
  },
  computed: {
    hasAnyHints() {
      return this.availableHints && this.availableHints.length > 0
    },
    hasUnlockedHints() {
      return this.availableHints && this.availableHints.some(hint => hint.unlocked)
    },
    availableHintsCount() {
      if (!this.availableHints || !Array.isArray(this.availableHints)) {
        return 0
      }
      return this.availableHints.filter(hint => hint.unlocked && !this.isHintUsed(hint.type)).length
    },
    hasNewUnlockedHints() {
      return this.currentAttempts > this.lastAttemptCount && this.availableHintsCount > 0
    },
    hasAnyActiveHints() {
      return this.activeHints.size > 0
    }
  },
  watch: {
    problemSlug: {
      immediate: true,
      handler(newSlug, oldSlug) {
        // Clear hint state when navigating to a new problem
        if (oldSlug && newSlug !== oldSlug) {
          this.clearHintState()
        }
        this.loadHints()
      }
    },
    currentAttempts(newVal, oldVal) {
      if (newVal > oldVal) {
        this.lastAttemptCount = oldVal
        this.loadHints()
      }
    },
    showMenu(isOpen) {
      if (isOpen) {
        // Add resize listener when menu opens
        window.addEventListener('resize', this.handleResize)
        window.addEventListener('scroll', this.handleScroll)
      } else {
        // Remove listeners when menu closes
        window.removeEventListener('resize', this.handleResize)
        window.removeEventListener('scroll', this.handleScroll)
      }
    }
  },
  
  beforeUnmount() {
    // Clean up event listeners
    window.removeEventListener('resize', this.handleResize)
    window.removeEventListener('scroll', this.handleScroll)
  },
  methods: {
    async loadHints() {
      try {
        // Store the current problem slug to validate against
        const loadingProblemSlug = this.problemSlug
        
        const context = {
          courseId: this.courseId,
          problemSetSlug: this.problemSetSlug
        }
        
        const response = await problemService.getHints(this.problemSlug, context)
        
        // Validate that we're still on the same problem after async operation
        if (this.problemSlug !== loadingProblemSlug) {
          log.debug('Problem changed during hint loading, discarding stale data')
          return
        }
        
        this.availableHints = response.available_hints || []
        this.hintsUsed = response.hints_used || []
        
        // Load content for already used hints
        for (const hintType of this.hintsUsed) {
          if (!this.hintContent[hintType]) {
            await this.loadHintContent(hintType)
          }
        }
      } catch (error: any) {
        log.error('Error loading hints', error)
        // Ensure we have safe defaults even on error
        this.availableHints = []
        this.hintsUsed = []
      }
    },
    
    async toggleHint(hintType) {
      if (this.loading) {return}
      
      const isActive = this.isHintActive(hintType)
      
      if (isActive) {
        // Remove hint
        this.activeHints.delete(hintType)
        this.$emit('hint-toggled', {
          hintType,
          isActive: false,
          hintData: null
        })
      } else {
        // Apply hint - first get the content if we don't have it
        if (!this.hintContent[hintType]) {
          await this.requestHintContent(hintType)
        }
        
        if (this.hintContent[hintType]) {
          this.activeHints.add(hintType)
          const transformedData = this.transformHintDataForProcessor(hintType)
          this.$emit('hint-toggled', {
            hintType,
            isActive: true,
            hintData: transformedData
          })
        }
      }
    },

    async requestHintContent(hintType) {
      if (this.loading || this.hintContent[hintType]) {return}
      
      // Store the current problem slug to validate against
      const requestProblemSlug = this.problemSlug
      
      this.loading = true
      try {
        const response = await problemService.getHintContent(this.problemSlug, hintType)
        
        // Validate that we're still on the same problem after async operation
        if (this.problemSlug !== requestProblemSlug) {
          log.debug('Problem changed during hint content loading, discarding stale data')
          return
        }
        
        // Store the original response for processing
        this.hintContent[hintType] = {
          type: response.type,
          title: this.getHintTitle(response.type),
          content: typeof response.content === 'object' ? JSON.stringify(response.content, null, 2) : response.content,
          originalData: response, // Keep original for hint processors
          problemSlug: requestProblemSlug // Track which problem this hint belongs to
        }
        
        if (!this.hintsUsed.includes(hintType)) {
          this.hintsUsed.push(hintType)
        }
        
        // Emit event for parent to track hint usage
        this.$emit('hint-used', {
          problemSlug: this.problemSlug,
          hintType: hintType,
          timestamp: new Date().toISOString()
        })
        
        this.notify.info('Hint Unlocked', 'Hint content has been revealed')
      } catch (error: any) {
        log.error('Error getting hint', error)
        
        // Handle 403 errors specially - these are expected when hints aren't unlocked yet
        if (error.status === 403 && error.error) {
          this.notify.info('Hint Locked', error.error)
        } else {
          this.notify.error('Error', error.error || 'Failed to load hint content')
        }
      } finally {
        this.loading = false
      }
    },
    
    async loadHintContent(hintType) {
      try {
        // Store the current problem slug to validate against
        const loadProblemSlug = this.problemSlug
        
        const response = await problemService.getHintContent(this.problemSlug, hintType)
        
        // Validate that we're still on the same problem after async operation
        if (this.problemSlug !== loadProblemSlug) {
          log.debug('Problem changed during hint content preload, discarding stale data')
          return
        }
        
        // Transform backend response to expected format
        this.hintContent[hintType] = {
          type: response.type,
          title: this.getHintTitle(response.type),
          content: typeof response.content === 'object' ? JSON.stringify(response.content, null, 2) : response.content,
          originalData: response,
          problemSlug: loadProblemSlug
        }
      } catch (error: any) {
        log.error('Error loading hint content', error)
        
        // Handle 403 errors silently during initial load - hints may be locked
        if (error.status !== 403) {
          this.notify.error('Error', error.error || 'Failed to load hint content')
        }
      }
    },
    
    toggleHintMenu() {
      if (!this.showMenu) {
        // Calculate position before showing menu
        this.calculateMenuPosition()
      }
      this.showMenu = !this.showMenu
    },
    
    calculateMenuPosition() {
      this.$nextTick(() => {
        const button = this.$el.querySelector('.hint-button')
        if (button) {
          const rect = button.getBoundingClientRect()
          const menuWidth = 400 // Approximate menu width
          const viewportWidth = window.innerWidth
          const viewportHeight = window.innerHeight
          
          // Calculate initial position below the button
          let top = rect.bottom + 8
          let left = rect.left
          
          // Adjust if menu would go off the right edge
          if (left + menuWidth > viewportWidth - 20) {
            left = viewportWidth - menuWidth - 20
          }
          
          // Adjust if menu would go off the left edge
          if (left < 20) {
            left = 20
          }
          
          // If menu would go off bottom, show above button instead
          if (top + 300 > viewportHeight - 20) { // Approximate menu height
            top = rect.top - 300 - 8
          }
          
          // Ensure menu doesn't go above viewport
          if (top < 20) {
            top = 20
          }
          
          this.menuPosition = { top: `${top}px`, left: `${left}px` }
        }
      })
    },
    
    isHintUsed(hintType) {
      return this.hintsUsed && Array.isArray(this.hintsUsed) && this.hintsUsed.includes(hintType)
    },
    
    getHintIcon(type) {
      const icons = {
        'variable_fade': '🔤',
        'subgoal_highlight': '🎯',
        'suggested_trace': '🔍',
        'structural': '🏗️',
        'implementation': '⚙️',
        'edge_case': '⚠️'
      }
      return icons[type] || '💡'
    },
    
    getMinAttemptsForNextHint() {
      if (!this.availableHints || !Array.isArray(this.availableHints)) {
        return 1
      }
      
      // Find the next locked hint with the lowest min_attempts requirement
      const lockedHints = this.availableHints.filter(h => h && !h.unlocked)
      if (lockedHints.length === 0) {return 0}
      
      // Get min attempts from hint data or use defaults
      const nextRequiredAttempts = Math.min(...lockedHints.map(h => this.getMinAttemptsForHint(h.type)))
      return Math.max(nextRequiredAttempts - this.currentAttempts, 0)
    },

    getMinAttemptsForHint(hintType) {
      // Try to get from hint content first if available
      if (this.hintContent[hintType]?.originalData?.min_attempts !== undefined) {
        return this.hintContent[hintType].originalData.min_attempts
      }
      
      // Default requirements based on hint type
      const defaults = {
        'subgoal_highlight': 0,
        'variable_fade': 1, 
        'suggested_trace': 2
      }
      return defaults[hintType] || 1
    },
    
    getHintTitle(hintType) {
      const titles = {
        'variable_fade': 'Variable Fade',
        'subgoal_highlight': 'Subgoal Highlighting', 
        'suggested_trace': 'Suggested Trace',
        'structural': 'Structural',
        'implementation': 'Implementation',
        'edge_case': 'Edge Case'
      }
      return titles[hintType] || 'Hint'
    },

    isHintActive(hintType) {
      return this.activeHints.has(hintType)
    },

    getOriginalHintData(hintType) {
      const hintContent = this.hintContent[hintType]
      return hintContent?.originalData || null
    },

    transformHintDataForProcessor(hintType) {
      const hintData = this.hintContent[hintType]
      const originalData = hintData?.originalData
      
      if (!originalData) {
        log.error(`No original data found for hint type: ${hintType}`)
        return null
      }
      
      // Validate hint belongs to current problem
      const currentSlug = this.problemSlug
      if (!currentSlug) {
        log.error('No current problem slug for hint validation')
        return null
      }
      
      // Check if the hint data is for the current problem
      if (hintData.problemSlug && hintData.problemSlug !== currentSlug) {
        log.warn(`Hint data is for problem ${hintData.problemSlug} but current problem is ${currentSlug}`)
        return null
      }

      // Parse content if it's a JSON string
      let content = originalData.content
      if (typeof content === 'string') {
        try {
          content = JSON.parse(content)
        } catch (e) {
          log.error(`Failed to parse content for ${hintType}`, e)
          return null
        }
      }
      
      // Transform field names based on hint type
      if (hintType === 'variable_fade' && content.mappings) {
        // Map backend's 'mappings' to processor's expected 'variable_mappings'
        content = {
          ...content,
          variable_mappings: content.mappings
        }
        delete content.mappings
      }
      
      // Return in the format expected by processors
      const result = {
        content: content
      }
      return result
    },

    showOriginalCode() {
      this.$emit('show-original')
    },

    removeAllHints() {
      this.activeHints.clear()
      this.$emit('remove-all-hints')
    },
    
    handleResize() {
      if (this.showMenu) {
        this.calculateMenuPosition()
      }
    },
    
    handleScroll() {
      if (this.showMenu) {
        this.calculateMenuPosition()
      }
    },
    
    clearHintState() {
      // Clear all hint-related state when switching problems
      this.hintContent = {}
      this.activeHints.clear()
      this.hintsUsed = []
      this.expandedHint = null
      this.showMenu = false
      
      // Emit event to clear any applied hints in the editor
      this.$emit('clear-all-hints')
      
      // Log for debugging
      log.debug('Cleared hint state for problem navigation')
    }
  }
}
</script>

<style scoped>
.hint-button-container {
  position: relative;
  display: inline-block;
}

.hint-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #4a5568;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.hint-button:hover:not(:disabled) {
  background: #2d3748;
  transform: translateY(-1px);
}

.hint-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hint-button.pulse {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(251, 191, 36, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(251, 191, 36, 0);
  }
}

.hint-icon {
  font-size: 18px;
}

.hint-badge {
  background: #f59e0b;
  color: white;
  border-radius: 10px;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: bold;
}

.hint-menu {
  position: fixed;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 350px;
  max-width: 450px;
  z-index: 1000;
  overflow: hidden;
}

.hint-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.hint-menu-header h4 {
  margin: 0;
  font-size: 16px;
  color: #1f2937;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #6b7280;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
}

.hint-list {
  max-height: 400px;
  overflow-y: auto;
}

.hint-item {
  border-bottom: 1px solid #f3f4f6;
}

.hint-item:last-child {
  border-bottom: none;
}

.hint-header {
  display: flex;
  align-items: center;
  padding: 16px;
  gap: 12px;
  transition: background 0.2s;
}

.hint-header.clickable {
  cursor: pointer;
}

.hint-item.active .hint-header {
  background: rgba(102, 126, 234, 0.1);
  border-left: 3px solid #667eea;
}

.hint-type-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.hint-info {
  flex: 1;
}

.hint-info h5 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.hint-description {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.hint-requirement {
  margin: 4px 0 0 0;
  font-size: 11px;
  color: #f59e0b;
  font-weight: 500;
}

.hint-status {
  flex-shrink: 0;
}

.status-icon {
  font-size: 16px;
}

.status-icon.used {
  color: #10b981;
}

.status-icon.locked {
  color: #9ca3af;
}

.status-icon.available {
  color: #3b82f6;
}

.hint-content {
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
}

.hint-content-body {
  padding: 16px;
}

.hint-content-body p {
  margin: 0 0 12px 0;
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
}

.hint-example {
  margin-top: 12px;
}

.hint-example h6 {
  margin: 0 0 8px 0;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
}

.hint-example pre {
  margin: 0;
  background: #1f2937;
  color: #f3f4f6;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 13px;
}

.hint-footer {
  padding: 12px 16px;
  background: #f9fafb;
  border-top: 1px solid #e5e7eb;
}

.hint-footer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hint-stats p {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.hint-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.secondary {
  background: #6b7280;
  color: white;
}

.action-btn.secondary:hover:not(:disabled) {
  background: #4b5563;
}

.action-btn.danger {
  background: #dc2626;
  color: white;
}

.action-btn.danger:hover:not(:disabled) {
  background: #b91c1c;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Toggle Switch Styles */
.hint-controls {
  display: flex;
  align-items: center;
}

.hint-toggle {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  cursor: pointer;
}

.hint-checkbox {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e0;
  transition: 0.3s;
  border-radius: 24px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.hint-checkbox:checked + .toggle-slider {
  background-color: #667eea;
}

.hint-checkbox:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.hint-toggle:hover .toggle-slider {
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
}

.hint-attempts {
  font-weight: 600;
  margin-bottom: 4px !important;
}

.no-hints-message {
  padding: 24px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
}

/* Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
  opacity: 1;
}

/* Dark theme adjustments if needed */
@media (prefers-color-scheme: dark) {
  .hint-menu {
    background: #1f2937;
    color: #f3f4f6;
  }
  
  .hint-menu-header {
    border-bottom-color: #374151;
  }
  
  .hint-menu-header h4 {
    color: #f3f4f6;
  }
  
  .close-btn {
    color: #9ca3af;
  }
  
  .close-btn:hover {
    background: #374151;
  }
  
  .hint-header.clickable:hover {
    background: #374151;
  }
  
  .hint-info h5 {
    color: #f3f4f6;
  }
  
  .hint-description {
    color: #9ca3af;
  }
  
  .hint-content {
    background: #374151;
    border-top-color: #4b5563;
  }
  
  .hint-content-body p {
    color: #e5e7eb;
  }
  
  .hint-footer {
    background: #374151;
    border-top-color: #4b5563;
  }
  
  .hint-footer p {
    color: #9ca3af;
  }
}
</style>