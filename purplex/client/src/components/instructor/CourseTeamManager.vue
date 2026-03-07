<template>
  <div class="team-manager">
    <h3>Course Team</h3>

    <!-- Loading -->
    <div v-if="loading" class="team-loading">
      <div class="loading-spinner" />
      <span>Loading team...</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="team-error" role="alert">
      <p>{{ error }}</p>
      <button class="btn-retry" @click="fetchTeam">Retry</button>
    </div>

    <!-- Team List -->
    <template v-else>
      <table class="team-table">
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
              <select
                :value="member.role"
                class="role-select"
                @change="changeRole(member, ($event.target as HTMLSelectElement).value)"
              >
                <option value="primary">Primary</option>
                <option value="ta">TA</option>
              </select>
              <button
                class="btn-remove"
                @click="confirmRemove(member)"
              >
                Remove
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Add Member (primary only) -->
      <div v-if="isPrimary" class="add-member">
        <h4>Add Team Member</h4>
        <div class="add-form">
          <input
            v-model.trim="newEmail"
            type="email"
            placeholder="Email address"
            class="input-email"
          />
          <select v-model="newRole" class="role-select">
            <option value="ta">TA</option>
            <option value="primary">Primary</option>
          </select>
          <button
            class="btn-add"
            :disabled="!newEmail || addingMember"
            @click="addMember"
          >
            {{ addingMember ? 'Adding...' : 'Add' }}
          </button>
        </div>
        <p v-if="actionError" class="action-error" role="alert">{{ actionError }}</p>
        <p v-if="actionSuccess" class="action-success">{{ actionSuccess }}</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { createContentService } from '@/services/contentService';
import { log } from '@/utils/logger';
import type { CourseInstructorMember, CourseInstructorRole } from '@/types';

const props = defineProps<{
  courseId: string;
  myRole?: CourseInstructorRole;
}>();

const api = createContentService('instructor');

const team = ref<CourseInstructorMember[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const actionError = ref<string | null>(null);
const actionSuccess = ref<string | null>(null);
const addingMember = ref(false);

const newEmail = ref('');
const newRole = ref<CourseInstructorRole>('ta');

// Reactive: re-evaluates when prop changes (e.g., after analytics API returns)
const isPrimary = computed(() => !props.myRole || props.myRole === 'primary');

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

async function fetchTeam(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    team.value = await api.getCourseTeam(props.courseId);
  } catch (err: any) {
    log.error('Failed to load course team', { courseId: props.courseId, error: err });
    error.value = 'Failed to load team members.';
  } finally {
    loading.value = false;
  }
}

async function addMember(): Promise<void> {
  if (!newEmail.value) return;
  addingMember.value = true;
  actionError.value = null;
  actionSuccess.value = null;
  try {
    const member = await api.addCourseTeamMember(props.courseId, {
      email: newEmail.value,
      role: newRole.value,
    });
    team.value.push(member);
    actionSuccess.value = `Added ${member.full_name} as ${member.role}.`;
    newEmail.value = '';
    newRole.value = 'ta';
  } catch (err: any) {
    const msg = err.response?.data?.error || 'Failed to add team member.';
    actionError.value = msg;
  } finally {
    addingMember.value = false;
  }
}

async function changeRole(member: CourseInstructorMember, role: string): Promise<void> {
  if (role === member.role) return;
  actionError.value = null;
  actionSuccess.value = null;
  try {
    const updated = await api.updateCourseTeamMember(props.courseId, member.user_id, {
      role: role as CourseInstructorRole,
    });
    const idx = team.value.findIndex((m) => m.user_id === member.user_id);
    if (idx !== -1) team.value[idx] = updated;
    actionSuccess.value = `Changed ${updated.full_name} to ${updated.role}.`;
  } catch (err: any) {
    const msg = err.response?.data?.error || 'Failed to update role.';
    actionError.value = msg;
    // Revert select in UI by re-fetching
    await fetchTeam();
  }
}

async function confirmRemove(member: CourseInstructorMember): Promise<void> {
  if (!confirm(`Remove ${member.full_name} from this course?`)) return;
  actionError.value = null;
  actionSuccess.value = null;
  try {
    await api.removeCourseTeamMember(props.courseId, member.user_id);
    team.value = team.value.filter((m) => m.user_id !== member.user_id);
    actionSuccess.value = `Removed ${member.full_name}.`;
  } catch (err: any) {
    const msg = err.response?.data?.error || 'Failed to remove team member.';
    actionError.value = msg;
  }
}

onMounted(fetchTeam);
</script>

<style scoped>
.team-manager {
  margin-top: var(--spacing-xl);
}

.team-manager h3 {
  font-size: var(--font-size-lg);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-lg);
}

.team-loading {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--color-text-muted);
}

.team-error {
  color: var(--color-error);
  padding: var(--spacing-md);
  background: var(--color-error-bg);
  border-radius: var(--radius-base);
}

.team-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: var(--spacing-lg);
}

.team-table th,
.team-table td {
  padding: var(--spacing-sm) var(--spacing-md);
  text-align: left;
  border-bottom: 1px solid var(--color-bg-border);
}

.team-table th {
  font-weight: 600;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.role-badge {
  display: inline-block;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-xs);
  font-size: var(--font-size-xs);
  font-weight: 600;
}

.role-primary {
  background: rgba(102, 126, 234, 0.15);
  color: var(--color-primary-gradient-start);
}

.role-ta {
  background: rgba(234, 179, 8, 0.15);
  color: #ca8a04;
}

.role-select {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
  margin-right: var(--spacing-sm);
}

.btn-remove {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: transparent;
  color: var(--color-error);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-size: var(--font-size-xs);
  transition: var(--transition-base);
}

.btn-remove:hover {
  background: var(--color-error-bg);
}

.btn-retry {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  cursor: pointer;
  color: var(--color-text-primary);
}

.add-member {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-lg);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-base);
}

.add-member h4 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: var(--font-size-md);
  color: var(--color-text-primary);
}

.add-form {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}

.input-email {
  width: 260px;
  padding: var(--spacing-sm);
  border: 1px solid var(--color-bg-border);
  border-radius: var(--radius-xs);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
}

.btn-add {
  padding: var(--spacing-sm) var(--spacing-md);
  background: linear-gradient(135deg, var(--color-primary-gradient-start), var(--color-primary-gradient-end));
  color: white;
  border: none;
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-weight: 600;
  transition: var(--transition-base);
}

.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-error {
  color: var(--color-error);
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
}

.action-success {
  color: var(--color-success);
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
}
</style>
