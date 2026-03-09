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

## 8. v-for requires unique :key

Always bind `:key` to a unique identifier (e.g., `item.id`). Never use array index.

```vue
<!-- WRONG -->
<div v-for="(course, index) in courses" :key="index">
<!-- RIGHT -->
<div v-for="course in courses" :key="course.id">
```
