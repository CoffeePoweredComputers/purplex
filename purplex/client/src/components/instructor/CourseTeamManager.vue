<template>
  <div class="course-team-manager">
    <div class="team-header">
      <h3>Course Team</h3>
      <button
        v-if="isPrimary"
        class="btn btn-sm btn-primary"
        @click="showAddForm = !showAddForm"
      >
        {{ showAddForm ? 'Cancel' : 'Add Member' }}
      </button>
    </div>

    <!-- Add member form -->
    <div v-if="showAddForm && isPrimary" class="add-member-form">
      <div class="form-row">
        <select v-model="newMember.userId" class="form-select">
          <option value="">Select a user...</option>
          <option
            v-for="user in availableUsers"
            :key="user.id"
            :value="user.id"
          >
            {{ user.full_name || user.username }} ({{ user.email }})
          </option>
        </select>
        <select v-model="newMember.role" class="form-select role-select">
          <option value="primary">Primary Instructor</option>
          <option value="ta">Teaching Assistant</option>
        </select>
        <button
          class="btn btn-sm btn-success"
          :disabled="!newMember.userId || adding"
          @click="addMember"
        >
          {{ adding ? 'Adding...' : 'Add' }}
        </button>
      </div>
      <p v-if="addError" class="error-text">{{ addError }}</p>
    </div>

    <!-- Team list -->
    <div v-if="loading" class="loading-state">Loading team...</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <table v-else class="team-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Role</th>
          <th>Added</th>
          <th v-if="isPrimary">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="member in team" :key="member.user_id">
          <td>{{ member.full_name }}</td>
          <td>{{ member.email }}</td>
          <td>
            <span :class="['role-badge', `role-${member.role}`]">
              {{ member.role === 'primary' ? 'Primary' : 'TA' }}
            </span>
          </td>
          <td>{{ formatDate(member.added_at) }}</td>
          <td v-if="isPrimary">
            <div class="action-buttons">
              <button
                v-if="member.role === 'ta'"
                class="btn btn-xs btn-outline"
                title="Promote to Primary"
                @click="changeRole(member, 'primary')"
              >
                Promote
              </button>
              <button
                v-if="member.role === 'primary' && team.filter(m => m.role === 'primary').length > 1"
                class="btn btn-xs btn-outline"
                title="Demote to TA"
                @click="changeRole(member, 'ta')"
              >
                Demote
              </button>
              <button
                v-if="canRemove(member)"
                class="btn btn-xs btn-danger"
                title="Remove from course"
                @click="removeMember(member)"
              >
                Remove
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { CourseInstructorMember, CourseInstructorRole, Instructor } from '@/types';
import { createContentService } from '@/services/contentService';

const props = defineProps<{
  courseId: string;
  myRole?: CourseInstructorRole;
}>();

const emit = defineEmits<{
  (e: 'team-updated'): void;
}>();

const api = createContentService('instructor');

const team = ref<CourseInstructorMember[]>([]);
const availableUsers = ref<Instructor[]>([]);
const loading = ref(true);
const error = ref('');
const showAddForm = ref(false);
const adding = ref(false);
const addError = ref('');

const isPrimary = computed(() => props.myRole === 'primary');

const newMember = ref<{ userId: number | ''; role: CourseInstructorRole }>({
  userId: '',
  role: 'ta',
});

async function loadTeam() {
  loading.value = true;
  error.value = '';
  try {
    team.value = await api.getCourseTeam(props.courseId);
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Failed to load team';
  } finally {
    loading.value = false;
  }
}

async function loadUsers() {
  try {
    // Use admin instructors list for user selection
    const adminApi = createContentService('admin');
    availableUsers.value = await adminApi.getInstructors();
  } catch {
    // Non-critical: user list may not be accessible for non-admins
    availableUsers.value = [];
  }
}

async function addMember() {
  if (!newMember.value.userId) return;
  adding.value = true;
  addError.value = '';
  try {
    await api.addCourseTeamMember(props.courseId, {
      user_id: newMember.value.userId as number,
      role: newMember.value.role,
    });
    newMember.value = { userId: '', role: 'ta' };
    showAddForm.value = false;
    await loadTeam();
    emit('team-updated');
  } catch (e: unknown) {
    addError.value = (e as Error).message || 'Failed to add member';
  } finally {
    adding.value = false;
  }
}

async function changeRole(member: CourseInstructorMember, newRole: CourseInstructorRole) {
  try {
    await api.updateCourseTeamMember(props.courseId, member.user_id, {
      role: newRole,
    });
    await loadTeam();
    emit('team-updated');
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Failed to update role';
  }
}

async function removeMember(member: CourseInstructorMember) {
  if (!confirm(`Remove ${member.full_name} from this course?`)) return;
  try {
    await api.removeCourseTeamMember(props.courseId, member.user_id);
    await loadTeam();
    emit('team-updated');
  } catch (e: unknown) {
    error.value = (e as Error).message || 'Failed to remove member';
  }
}

function canRemove(member: CourseInstructorMember): boolean {
  // Cannot remove the last primary
  if (member.role === 'primary') {
    return team.value.filter(m => m.role === 'primary').length > 1;
  }
  return true;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString();
}

onMounted(() => {
  loadTeam();
  if (isPrimary.value) {
    loadUsers();
  }
});
</script>

<style scoped>
.course-team-manager {
  margin-top: 1.5rem;
}

.team-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.team-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.add-member-form {
  padding: 1rem;
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: 8px;
  margin-bottom: 1rem;
  background: var(--color-surface, #fafafa);
}

.form-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.form-select {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-border, #ccc);
  border-radius: 4px;
  font-size: 0.9rem;
}

.role-select {
  max-width: 180px;
}

.team-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.team-table th,
.team-table td {
  padding: 0.6rem 0.8rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
}

.team-table th {
  font-weight: 600;
  color: var(--color-text-secondary, #666);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.role-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.role-primary {
  background: var(--color-primary-light, #e3f2fd);
  color: var(--color-primary, #1976d2);
}

.role-ta {
  background: var(--color-success-light, #e8f5e9);
  color: var(--color-success, #388e3c);
}

.action-buttons {
  display: flex;
  gap: 0.4rem;
}

.btn-xs {
  padding: 0.2rem 0.5rem;
  font-size: 0.75rem;
}

.error-text {
  color: var(--color-error, #d32f2f);
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

.loading-state,
.error-state {
  padding: 1rem;
  text-align: center;
  color: var(--color-text-secondary, #666);
}

.error-state {
  color: var(--color-error, #d32f2f);
}
</style>
