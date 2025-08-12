# Frontend State Management Guidelines

## Overview

This document defines when to use Vuex vs Composables in the Purplex frontend application. Following these guidelines ensures consistent state management patterns across the codebase.

## State Management Strategy

### Use Vuex For:
**Global Application State**
- User authentication state
- User profile data
- Application-wide settings
- Course enrollment data
- Data that needs to persist across route changes
- State that multiple unrelated components need to access

### Use Composables For:
**Local Component State & Shared Logic**
- Component-specific state that doesn't need global access
- Reusable business logic between components
- API call abstractions (e.g., `useSubmission`)
- Real-time connections (e.g., `useSSE`)
- UI state management (e.g., `useNotification`, `useModal`)
- Form handling and validation
- Component lifecycle management

## Decision Framework

Ask these questions to determine which pattern to use:

1. **Is the state needed by multiple unrelated components?**
   - Yes → Use Vuex
   - No → Use Composables

2. **Does the state need to persist across route changes?**
   - Yes → Use Vuex
   - No → Use Composables

3. **Is it primarily business logic or utilities?**
   - Yes → Use Composables
   - No → Consider Vuex for state

4. **Is it real-time or connection-based?**
   - Yes → Use Composables
   - No → Either, based on other factors

## Implementation Examples

### Vuex Example - User Authentication
```typescript
// store/modules/auth.ts
export const authModule = {
  state: {
    user: null,
    isAuthenticated: false,
    token: null
  },
  mutations: {
    SET_USER(state, user) {
      state.user = user
      state.isAuthenticated = !!user
    }
  },
  actions: {
    async login({ commit }, credentials) {
      const user = await authAPI.login(credentials)
      commit('SET_USER', user)
    }
  }
}

// Component usage
import { useStore } from 'vuex'

export default {
  setup() {
    const store = useStore()
    const user = computed(() => store.state.auth.user)
    return { user }
  }
}
```

### Composable Example - Problem Submission
```typescript
// composables/useSubmission.ts
export function useSubmission(problemSlug: string) {
  const submission = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  const submitCode = async (code: string) => {
    loading.value = true
    try {
      submission.value = await api.submitSolution(problemSlug, code)
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }
  
  return {
    submission: readonly(submission),
    loading: readonly(loading),
    error: readonly(error),
    submitCode
  }
}

// Component usage
import { useSubmission } from '@/composables/useSubmission'

export default {
  setup() {
    const { submission, loading, submitCode } = useSubmission('two-sum')
    return { submission, loading, submitCode }
  }
}
```

## Current Implementation Status

### Existing Vuex Modules
- `auth` - User authentication and session management
- `problems` - Problem data and metadata
- `progress` - User progress tracking

### Existing Composables
- `useSSE` - Server-sent events management
- `useNotification` - Toast notifications
- `useSubmission` - Code submission handling
- `useHints` - Hint system integration
- `useProblemSet` - Problem set navigation

## Migration Guidelines

When refactoring existing code:

1. **Keep Vuex for existing global state** - Don't migrate working Vuex modules unless there's a clear benefit
2. **Extract new features as composables** - New features should prefer composables unless they clearly need global state
3. **Gradually refactor view-specific logic** - Move component-specific Vuex modules to composables when refactoring those components

## Anti-Patterns to Avoid

❌ **Don't mix patterns in the same component**
```typescript
// BAD: Using both for the same concern
export default {
  setup() {
    const store = useStore()
    const problems = computed(() => store.state.problems.list)
    const { submitCode } = useSubmission() // Also deals with problems
  }
}
```

❌ **Don't use Vuex for temporary UI state**
```typescript
// BAD: Modal state in Vuex
store.commit('SET_MODAL_OPEN', true)

// GOOD: Modal state in composable
const { isOpen, openModal, closeModal } = useModal()
```

❌ **Don't create composables that just wrap Vuex**
```typescript
// BAD: Unnecessary abstraction
export function useAuth() {
  const store = useStore()
  return {
    user: computed(() => store.state.auth.user)
  }
}

// GOOD: Direct Vuex usage for global state
const user = computed(() => store.state.auth.user)
```

## Testing Considerations

### Testing Vuex
- Mock the entire store for component tests
- Test mutations and actions separately
- Use Vuex testing utilities

### Testing Composables
- Test composables in isolation
- Mock external dependencies
- Test return values and side effects

## Performance Considerations

- **Vuex**: Centralized reactivity can cause unnecessary re-renders
- **Composables**: More granular reactivity, better tree-shaking
- Use `shallowRef` and `shallowReactive` in composables for large data structures
- Consider `markRaw` for non-reactive data in both patterns

## Future Direction

The codebase is gradually moving towards more composable-based patterns as Vue 3's Composition API matures. New features should default to composables unless they explicitly need global state management.

## Questions?

If you're unsure which pattern to use, ask yourself:
1. Will multiple routes/pages need this data?
2. Does this data define the application's state?
3. Is this primarily logic or state?

When in doubt, start with a composable. It's easier to elevate local state to global than to extract global state to local.