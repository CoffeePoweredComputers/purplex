<template>
  <div class="hint-button-container">
    <button 
      class="hint-button"
      @click="toggleHintMenu"
      :disabled="loading || !hasUnlockedHints"
      :class="{ 'pulse': hasNewUnlockedHints }"
    >
      <span class="hint-icon">💡</span>
      <span class="hint-text">Hints</span>
      <span v-if="availableHintsCount > 0" class="hint-badge">{{ availableHintsCount }}</span>
    </button>
    
    <transition name="slide">
      <div v-if="showMenu && hasUnlockedHints" class="hint-menu">
        <div class="hint-menu-header">
          <h4>Available Hints</h4>
          <button class="close-btn" @click="showMenu = false">×</button>
        </div>
        
        <div class="hint-list">
          <div 
            v-for="hint in availableHints" 
            :key="hint.type"
            class="hint-item"
            :class="{ 
              'unlocked': hint.unlocked, 
              'used': isHintUsed(hint.type),
              'locked': !hint.unlocked 
            }"
          >
            <div 
              class="hint-header"
              @click="hint.unlocked && !isHintUsed(hint.type) ? requestHint(hint.type) : null"
              :class="{ 'clickable': hint.unlocked && !isHintUsed(hint.type) }"
            >
              <span class="hint-type-icon">{{ getHintIcon(hint.type) }}</span>
              <div class="hint-info">
                <h5>{{ hint.title }}</h5>
                <p class="hint-description">{{ hint.description }}</p>
              </div>
              <span class="hint-status">
                <span v-if="isHintUsed(hint.type)" class="status-icon used">✓</span>
                <span v-else-if="!hint.unlocked" class="status-icon locked">🔒</span>
                <span v-else class="status-icon available">→</span>
              </span>
            </div>
            
            <transition name="expand">
              <div v-if="expandedHint === hint.type && hintContent[hint.type]" class="hint-content">
                <div class="hint-content-body">
                  <p>{{ hintContent[hint.type].content }}</p>
                  <div v-if="hintContent[hint.type].example" class="hint-example">
                    <h6>Example:</h6>
                    <pre><code>{{ hintContent[hint.type].example }}</code></pre>
                  </div>
                </div>
              </div>
            </transition>
          </div>
        </div>
        
        <div class="hint-footer">
          <p class="hint-attempts">Attempts: {{ currentAttempts }}</p>
          <p class="hint-note">Hints unlock after {{ getMinAttemptsForNextHint() }} attempts</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import { problemService } from '@/services/problemService'
import { useNotification } from '@/composables/useNotification'

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
      lastAttemptCount: 0
    }
  },
  computed: {
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
    }
  },
  watch: {
    problemSlug: {
      immediate: true,
      handler() {
        this.loadHints()
      }
    },
    currentAttempts(newVal, oldVal) {
      if (newVal > oldVal) {
        this.lastAttemptCount = oldVal
        this.loadHints()
      }
    }
  },
  methods: {
    async loadHints() {
      try {
        const context = {
          courseId: this.courseId,
          problemSetSlug: this.problemSetSlug
        }
        
        const response = await problemService.getHints(this.problemSlug, context)
        this.availableHints = response.available_hints || []
        this.hintsUsed = response.hints_used || []
        
        // Load content for already used hints
        for (const hintType of this.hintsUsed) {
          if (!this.hintContent[hintType]) {
            await this.loadHintContent(hintType)
          }
        }
      } catch (error) {
        console.error('Error loading hints:', error)
        // Ensure we have safe defaults even on error
        this.availableHints = []
        this.hintsUsed = []
      }
    },
    
    async requestHint(hintType) {
      if (this.loading || this.isHintUsed(hintType)) return
      
      this.loading = true
      try {
        const response = await problemService.getHintContent(this.problemSlug, hintType)
        
        // Transform backend response to expected format
        this.hintContent[hintType] = {
          type: response.type,
          title: this.getHintTitle(response.type),
          content: typeof response.content === 'object' ? JSON.stringify(response.content, null, 2) : response.content
        }
        this.hintsUsed.push(hintType)
        this.expandedHint = hintType
        
        // Emit event for parent to track hint usage
        this.$emit('hint-used', {
          problemSlug: this.problemSlug,
          hintType: hintType,
          timestamp: new Date().toISOString()
        })
        
        this.notify.info('Hint Unlocked', 'Hint content has been revealed')
      } catch (error) {
        console.error('Error getting hint:', error)
        this.notify.error('Error', 'Failed to load hint content')
      } finally {
        this.loading = false
      }
    },
    
    async loadHintContent(hintType) {
      try {
        const response = await problemService.getHintContent(this.problemSlug, hintType)
        // Transform backend response to expected format
        this.hintContent[hintType] = {
          type: response.type,
          title: this.getHintTitle(response.type),
          content: typeof response.content === 'object' ? JSON.stringify(response.content, null, 2) : response.content
        }
      } catch (error) {
        console.error('Error loading hint content:', error)
      }
    },
    
    toggleHintMenu() {
      this.showMenu = !this.showMenu
    },
    
    isHintUsed(hintType) {
      return this.hintsUsed && Array.isArray(this.hintsUsed) && this.hintsUsed.includes(hintType)
    },
    
    getHintIcon(type) {
      const icons = {
        'variable_fade': '🔤',
        'subgoal_highlight': '🎯',
        'input_suggestion': '💡',
        'structural': '🏗️',
        'implementation': '⚙️',
        'edge_case': '⚠️'
      }
      return icons[type] || '💡'
    },
    
    getMinAttemptsForNextHint() {
      if (!this.availableHints || !Array.isArray(this.availableHints)) {
        return 2
      }
      const unlockedCount = this.availableHints.filter(h => h && h.unlocked).length
      if (unlockedCount === 0) return 2
      if (unlockedCount === 1) return 4
      return 6
    },
    
    getHintTitle(hintType) {
      const titles = {
        'variable_fade': 'Variable Fade',
        'subgoal_highlight': 'Subgoal Highlighting', 
        'input_suggestion': 'Input Suggestion',
        'structural': 'Structural',
        'implementation': 'Implementation',
        'edge_case': 'Edge Case'
      }
      return titles[hintType] || 'Hint'
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
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
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

.hint-header.clickable:hover {
  background: #f9fafb;
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

.hint-footer p {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.hint-attempts {
  font-weight: 600;
  margin-bottom: 4px !important;
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