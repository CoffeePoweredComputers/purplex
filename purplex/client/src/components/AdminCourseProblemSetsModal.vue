<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Manage Problem Sets for {{ course.name }}</h2>
        <button @click="$emit('close')" class="close-btn">×</button>
      </div>
      
      <div class="modal-body">
        <!-- Current Problem Sets Section -->
        <div class="section">
          <h3>Current Problem Sets</h3>
          
          <div v-if="loading.current" class="loading-container">
            <div class="loading-spinner"></div>
            <p>Loading problem sets...</p>
          </div>
          
          <div v-else-if="currentProblemSets.length === 0" class="empty-state">
            <p>No problem sets assigned to this course yet.</p>
          </div>
          
          <table v-else class="problem-sets-table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Problem Set</th>
                <th>Problems</th>
                <th>Required</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in currentProblemSets" :key="item.id">
                <td class="order-cell">
                  <div class="order-controls">
                    <button 
                      @click="moveUp(index)" 
                      :disabled="index === 0"
                      class="order-btn"
                      title="Move up"
                    >
                      ↑
                    </button>
                    <span>{{ item.order + 1 }}</span>
                    <button 
                      @click="moveDown(index)" 
                      :disabled="index === currentProblemSets.length - 1"
                      class="order-btn"
                      title="Move down"
                    >
                      ↓
                    </button>
                  </div>
                </td>
                <td>{{ item.problem_set.title }}</td>
                <td class="center">{{ item.problem_set.problems_count }}</td>
                <td class="center">
                  <input 
                    type="checkbox" 
                    v-model="item.is_required"
                    @change="updateRequired(item)"
                  />
                </td>
                <td>
                  <button 
                    @click="removeProblemSet(item)"
                    class="remove-btn"
                    title="Remove from course"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <hr class="divider" />
        
        <!-- Available Problem Sets Section -->
        <div class="section">
          <h3>Add Problem Sets</h3>
          
          <div v-if="loading.available" class="loading-container">
            <div class="loading-spinner"></div>
            <p>Loading available problem sets...</p>
          </div>
          
          <div v-else-if="availableProblemSets.length === 0" class="empty-state">
            <p>All problem sets have been added to this course.</p>
          </div>
          
          <div v-else class="available-grid">
            <div 
              v-for="ps in availableProblemSets" 
              :key="ps.slug"
              class="available-item"
            >
              <div class="item-info">
                <h4>{{ ps.title }}</h4>
                <p class="description">{{ ps.description || 'No description' }}</p>
                <span class="problems-count">{{ ps.problems_count }} problems</span>
              </div>
              <button 
                @click="addProblemSet(ps)"
                class="add-btn"
                :disabled="loading.adding"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="modal-footer">
        <button @click="$emit('close')" class="close-modal-btn">
          Done
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, watchEffect } from 'vue'
import axios from 'axios'
import { useNotification } from '@/composables/useNotification'

export default {
  name: 'AdminCourseProblemSetsModal',
  props: {
    visible: {
      type: Boolean,
      required: true
    },
    course: {
      type: Object,
      required: true
    }
  },
  emits: ['close', 'updated'],
  setup(props, { emit }) {
    const { notify } = useNotification()
    
    // Data
    const currentProblemSets = ref([])
    const availableProblemSets = ref([])
    const loading = ref({
      current: false,
      available: false,
      adding: false
    })
    
    // Methods
    const fetchCurrentProblemSets = async () => {
      loading.value.current = true
      try {
        const response = await axios.get(`/api/admin/courses/${props.course.course_id}/problem-sets/`)
        currentProblemSets.value = response.data
      } catch (error) {
        notify.error('Error', 'Failed to load current problem sets')
        console.error('Error fetching current problem sets:', error)
      } finally {
        loading.value.current = false
      }
    }
    
    const fetchAvailableProblemSets = async () => {
      loading.value.available = true
      try {
        const response = await axios.get('/api/admin/problem-sets/available/', {
          params: { exclude_course: props.course.course_id }
        })
        availableProblemSets.value = response.data
      } catch (error) {
        notify.error('Error', 'Failed to load available problem sets')
        console.error('Error fetching available problem sets:', error)
      } finally {
        loading.value.available = false
      }
    }
    
    const addProblemSet = async (problemSet) => {
      loading.value.adding = true
      try {
        const response = await axios.post(`/api/admin/courses/${props.course.course_id}/problem-sets/`, {
          problem_set_slug: problemSet.slug,
          is_required: false
        })
        
        // Add to current list
        currentProblemSets.value.push(response.data)
        
        // Remove from available list
        const index = availableProblemSets.value.findIndex(ps => ps.slug === problemSet.slug)
        if (index > -1) {
          availableProblemSets.value.splice(index, 1)
        }
        
        notify.success('Success', 'Problem set added to course')
        emit('updated')
      } catch (error) {
        const errorMsg = error.response?.data?.error || 'Failed to add problem set'
        notify.error('Error', errorMsg)
      } finally {
        loading.value.adding = false
      }
    }
    
    const removeProblemSet = async (item) => {
      if (!confirm(`Remove "${item.problem_set.title}" from this course?`)) {
        return
      }
      
      try {
        await axios.delete(`/api/admin/courses/${props.course.course_id}/problem-sets/${item.problem_set.slug}/`)
        
        // Remove from current list
        const index = currentProblemSets.value.findIndex(ps => ps.id === item.id)
        if (index > -1) {
          currentProblemSets.value.splice(index, 1)
        }
        
        // Add back to available list
        availableProblemSets.value.push({
          slug: item.problem_set.slug,
          title: item.problem_set.title,
          problems_count: item.problem_set.problems_count,
          description: '' // We don't have description in current data
        })
        
        // Sort available list by title
        availableProblemSets.value.sort((a, b) => a.title.localeCompare(b.title))
        
        notify.success('Success', 'Problem set removed from course')
        emit('updated')
      } catch (error) {
        notify.error('Error', 'Failed to remove problem set')
      }
    }
    
    const updateRequired = async (item) => {
      try {
        await axios.put(`/api/admin/courses/${props.course.course_id}/problem-sets/${item.problem_set.slug}/`, {
          is_required: item.is_required
        })
        notify.success('Success', 'Required status updated')
      } catch (error) {
        // Revert on error
        item.is_required = !item.is_required
        notify.error('Error', 'Failed to update required status')
      }
    }
    
    const moveUp = async (index) => {
      if (index === 0) return
      
      const current = currentProblemSets.value[index]
      const previous = currentProblemSets.value[index - 1]
      
      // Swap orders
      const currentOrder = current.order
      current.order = previous.order
      previous.order = currentOrder
      
      // Swap positions in array
      currentProblemSets.value.splice(index - 1, 2, current, previous)
      
      // Update both items
      await updateOrder(current)
      await updateOrder(previous)
    }
    
    const moveDown = async (index) => {
      if (index === currentProblemSets.value.length - 1) return
      
      const current = currentProblemSets.value[index]
      const next = currentProblemSets.value[index + 1]
      
      // Swap orders
      const currentOrder = current.order
      current.order = next.order
      next.order = currentOrder
      
      // Swap positions in array
      currentProblemSets.value.splice(index, 2, next, current)
      
      // Update both items
      await updateOrder(current)
      await updateOrder(next)
    }
    
    const updateOrder = async (item) => {
      try {
        await axios.put(`/api/admin/courses/${props.course.course_id}/problem-sets/${item.problem_set.slug}/`, {
          order: item.order
        })
      } catch (error) {
        notify.error('Error', 'Failed to update order')
        // Reload to get correct order
        fetchCurrentProblemSets()
      }
    }
    
    // Use watchEffect to reactively fetch data when both visible and course are available
    watchEffect(() => {
      if (props.visible && props.course && props.course.course_id) {
        fetchCurrentProblemSets()
        fetchAvailableProblemSets()
      }
    })
    
    return {
      currentProblemSets,
      availableProblemSets,
      loading,
      fetchCurrentProblemSets,
      fetchAvailableProblemSets,
      addProblemSet,
      removeProblemSet,
      updateRequired,
      moveUp,
      moveDown
    }
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--color-bg-panel);
  border-radius: var(--radius-lg);
  max-width: 900px;
  width: 90%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
  border: 2px solid var(--color-bg-input);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-bottom: 2px solid var(--color-bg-input);
  background: var(--color-bg-hover);
}

.modal-header h2 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-xl);
}

.close-btn {
  background: none;
  border: none;
  font-size: var(--font-size-xl);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-xs);
  transition: var(--transition-fast);
}

.close-btn:hover {
  background-color: var(--color-bg-input);
  color: var(--color-text-primary);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
}

.section {
  margin-bottom: var(--spacing-xl);
}

.section h3 {
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-lg);
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-bg-hover);
  border-top: 3px solid var(--color-primary-gradient-start);
  border-radius: var(--radius-circle);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-muted);
  background-color: var(--color-bg-hover);
  border-radius: var(--radius-base);
}

/* Current Problem Sets Table */
.problem-sets-table {
  width: 100%;
  border-collapse: collapse;
  background-color: var(--color-bg-hover);
  border-radius: var(--radius-base);
  overflow: hidden;
}

.problem-sets-table th {
  background-color: var(--color-bg-input);
  padding: var(--spacing-md) var(--spacing-lg);
  text-align: left;
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.problem-sets-table td {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-bg-input);
  color: var(--color-text-secondary);
}

.problem-sets-table tr:hover {
  background-color: var(--color-bg-hover);
  transition: background-color 0.15s ease;
}

.center {
  text-align: center;
}

.order-cell {
  width: 120px;
}

.order-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.order-btn {
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--color-bg-input);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
}

.order-btn:hover:not(:disabled) {
  border-color: var(--color-primary-gradient-start);
  color: var(--color-text-primary);
}

.order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.remove-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  background-color: transparent;
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  color: var(--color-text-muted);
  cursor: pointer;
  transition: var(--transition-fast);
  font-size: var(--font-size-sm);
}

.remove-btn:hover {
  color: var(--color-error);
  border-color: var(--color-error);
}

/* Divider */
.divider {
  border: none;
  border-top: 2px solid var(--color-bg-input);
  margin: var(--spacing-xl) 0;
}

/* Available Problem Sets Grid */
.available-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

.available-item {
  background-color: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  padding: var(--spacing-lg);
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: var(--spacing-lg);
  transition: var(--transition-fast);
}

.available-item:hover {
  background-color: var(--color-bg-hover);
  border-color: var(--color-primary-gradient-start);
}

.item-info {
  flex: 1;
}

.item-info h4 {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-sm) 0;
}

.description {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--spacing-sm) 0;
  line-height: 1.4;
}

.problems-count {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.add-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  background-color: var(--color-success);
  border: none;
  border-radius: var(--radius-xs);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: var(--transition-fast);
  font-weight: 600;
  white-space: nowrap;
}

.add-btn:hover:not(:disabled) {
  background-color: var(--color-success);
  opacity: 0.9;
}

.add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal Footer */
.modal-footer {
  padding: var(--spacing-lg) var(--spacing-xl);
  border-top: 2px solid var(--color-bg-input);
  background: var(--color-bg-hover);
  display: flex;
  justify-content: flex-end;
}

.close-modal-btn {
  padding: var(--spacing-md) var(--spacing-xl);
  background: linear-gradient(135deg, var(--color-primary-gradient-start) 0%, var(--color-primary-gradient-end) 100%);
  color: var(--color-text-primary);
  border: none;
  border-radius: var(--radius-base);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-fast);
}

.close-modal-btn:hover {
  opacity: 0.9;
}
</style>