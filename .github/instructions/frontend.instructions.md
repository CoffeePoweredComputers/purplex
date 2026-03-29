---
applyTo: "purplex/client/**"
---

# Frontend Review Rules

## 1. Use Composition API exclusively

All components must use `<script setup>` with TypeScript. No Options API (`data()`, `methods`, `computed`, `watch` as object properties).

```vue
<!-- WRONG -->
<script>
export default {
  data() { return { count: 0 } },
  methods: { increment() { this.count++ } }
}
</script>

<!-- RIGHT -->
<script setup lang="ts">
import { ref } from 'vue'
const count = ref(0)
const increment = () => count.value++
</script>
```

## 2. Component naming

Components use PascalCase filenames: `CourseTeamManager.vue`, `ProblemEditor.vue`. Flag `kebab-case.vue` or `camelCase.vue` names.

## 3. Composables use `use` prefix

Composable files and exported functions must start with `use`: `useSubmissions.ts`, `useTaskPolling.ts`.

```typescript
// WRONG
export function submissions() { ... }
// RIGHT
export function useSubmissions() { ... }
```

## 4. API calls go through service layer

Components never call `axios` or `fetch` directly. All HTTP calls go through service files (`contentService.ts`, `submissionService.ts`, etc.).

```typescript
// WRONG — direct axios in component
import axios from 'axios'
const res = await axios.get('/api/courses/')

// RIGHT — service layer
import { adminContentService } from '@/services/contentService'
const courses = await adminContentService.getCourses()
```

## 5. Service factory pattern

Content services use `createContentService(role)` to scope API paths by role:

```typescript
import { createContentService } from '@/services/contentService'
const adminApi = createContentService('admin')           // /api/admin/...
const instructorApi = createContentService('instructor') // /api/instructor/...
```

Pre-built instances are available: `adminContentService`, `instructorContentService`.

## 6. Types from @/types

Shared TypeScript types live in `purplex/client/src/types/`. Import from `@/types`.

```typescript
// WRONG — inline type or local definition
interface Course { id: number; title: string }
// RIGHT — shared type
import type { Course } from '@/types'
```

## 7. No `any` type

Use proper TypeScript types or `unknown` with type guards. Flag `any` in new code.

```typescript
// WRONG
function process(data: any) { return data.id }
// RIGHT
function process(data: unknown) {
  if (typeof data === 'object' && data !== null && 'id' in data) {
    return (data as { id: number }).id
  }
}
```

## 8. i18n: all user-facing strings must be translated

Never hardcode English strings in templates or scripts. Use `$t()` / `t()` with keys from the i18n locale files. When adding new i18n keys to `locales/en/`, you **must** add the corresponding key to `locales/es/` (and all other locale directories that exist). The `localeIntegrity.test.ts` enforces en/es parity — missing keys will fail CI.

```typescript
// WRONG — hardcoded string
actionError.value = 'Failed to update role'

// RIGHT — i18n key
actionError.value = t('admin.courseTeam.updateFailed')
```

When backend errors need user-facing messages, return an error `code` field and map it to an i18n key on the frontend:

```typescript
// Backend returns: {"error": "...", "code": "last_primary"}
// Frontend resolves: t(`admin.courseTeam.errors.${code}`)
```

## 9. v-for requires unique :key

Always bind `:key` to a unique identifier (e.g., `item.id`). Never use array index.

```vue
<!-- WRONG -->
<div v-for="(course, index) in courses" :key="index">
<!-- RIGHT -->
<div v-for="course in courses" :key="course.id">
```
