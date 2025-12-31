# Frontend Activity Component Structure

This document explains the frontend component architecture for activity types in Purplex.

## Overview

The frontend uses a **registry-based component loading pattern** to dynamically load activity-specific components. This allows new activity types to be added without modifying existing component code.

## Directory Structure

```
client/src/components/activities/
├── index.ts                    # Registry and exports
├── types.ts                    # Shared TypeScript types
├── InputSelector.vue           # Dynamic input component loader
├── FeedbackSelector.vue        # Dynamic feedback component loader
├── inputs/
│   ├── EiplInput.vue           # EiPL input component
│   ├── McqInput.vue            # MCQ input component
│   ├── PromptInput.vue         # Prompt input component
│   ├── RefuteInput.vue         # Refute input component
│   ├── DebugFixInput.vue       # Debug Fix input component
│   ├── ProbeableCodeInput.vue  # Probeable Code input component
│   ├── ProbeableSpecInput.vue  # Probeable Spec input component
│   ├── DescriptionInput.vue    # Shared description input
│   └── shared/
│       ├── ProbePanel.vue      # Shared probe panel for probeable types
│       └── useProbeState.ts    # Shared probe state composable
└── feedback/
    ├── EiplFeedback.vue        # EiPL feedback component
    ├── McqFeedback.vue         # MCQ feedback component
    ├── PromptFeedback.vue      # Prompt feedback component
    ├── RefuteFeedback.vue      # Refute feedback component
    ├── DebugFixFeedback.vue    # Debug Fix feedback component
    ├── ProbeableCodeFeedback.vue   # Probeable Code feedback component
    ├── ProbeableSpecFeedback.vue   # Probeable Spec feedback component
    └── CodeSubmissionFeedback.vue  # Shared code submission feedback
```

## Component Registry

### Registry Definition (`index.ts`)

```typescript
import { type Component, defineAsyncComponent } from 'vue'
import type { ActivityComponentRegistry } from './types'
import AsyncLoader from '@/components/ui/AsyncLoader.vue'
import AsyncError from '@/components/ui/AsyncError.vue'
import { log } from '@/utils/logger'

// Activity component registry
const ACTIVITY_COMPONENTS: ActivityComponentRegistry = {
  eipl: {
    input: () => import('./inputs/EiplInput.vue'),
    feedback: () => import('./feedback/EiplFeedback.vue'),
  },
  mcq: {
    input: () => import('./inputs/McqInput.vue'),
    feedback: () => import('./feedback/McqFeedback.vue'),
  },
  prompt: {
    input: () => import('./inputs/PromptInput.vue'),
    feedback: () => import('./feedback/PromptFeedback.vue'),
  },
  refute: {
    input: () => import('./inputs/RefuteInput.vue'),
    feedback: () => import('./feedback/RefuteFeedback.vue'),
  },
  debug_fix: {
    input: () => import('./inputs/DebugFixInput.vue'),
    feedback: () => import('./feedback/DebugFixFeedback.vue'),
  },
  probeable_code: {
    input: () => import('./inputs/ProbeableCodeInput.vue'),
    feedback: () => import('./feedback/ProbeableCodeFeedback.vue'),
  },
  probeable_spec: {
    input: () => import('./inputs/ProbeableSpecInput.vue'),
    feedback: () => import('./feedback/ProbeableSpecFeedback.vue'),
  },
}

// Helper functions
export function isActivityTypeRegistered(activityType: string): boolean {
  return activityType in ACTIVITY_COMPONENTS
}

export function getActivityInput(activityType: string): Component | undefined {
  const definition = ACTIVITY_COMPONENTS[activityType]
  if (!definition) {
    log.warn(`No input component registered for activity type: ${activityType}`)
    return undefined
  }

  return defineAsyncComponent({
    loader: definition.input,
    loadingComponent: AsyncLoader,
    errorComponent: AsyncError,
    delay: 200,
    timeout: 10000,
  })
}

export function getActivityFeedback(activityType: string): Component | undefined {
  const definition = ACTIVITY_COMPONENTS[activityType]
  if (!definition) {
    log.warn(`No feedback component registered for activity type: ${activityType}`)
    return undefined
  }

  return defineAsyncComponent({
    loader: definition.feedback,
    loadingComponent: AsyncLoader,
    errorComponent: AsyncError,
    delay: 200,
    timeout: 10000,
  })
}
```

### Lazy Loading

Components are loaded using `defineAsyncComponent` with dynamic imports, which:
- Reduces initial bundle size
- Only loads components when needed
- Provides error boundaries for failed loads

## Selector Components

### InputSelector

The `InputSelector.vue` component dynamically loads the appropriate input component:

```vue
<template>
  <component
    :is="InputComponent"
    v-if="InputComponent"
    v-bind="$props"
    @submit="$emit('submit', $event)"
  />
  <div v-else class="fallback">
    No input component for: {{ activityType }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getActivityInput, isActivityTypeRegistered } from './index'

const props = defineProps<{
  activityType: string
  // ... other props
}>()

const InputComponent = computed(() => {
  if (!isActivityTypeRegistered(props.activityType)) return null
  return getActivityInput(props.activityType)
})
</script>
```

### FeedbackSelector

The `FeedbackSelector.vue` component follows the same pattern for feedback display.

## Component Props Contract

### Input Components

All input components should accept these common props (defined as `ActivityInputProps`):

```typescript
interface ActivityInputProps {
  /** The user's current input value (v-model) */
  modelValue: string
  /** Current problem data including type-specific config */
  problem: ActivityProblem
  /** Currently active hints applied to the problem */
  activeHints?: HintConfig[]
  /** Whether the input should be disabled (during submission) */
  disabled?: boolean
  /** Editor theme name */
  theme?: string
  /** Whether a draft has been saved */
  draftSaved?: boolean
}
```

And emit:

```typescript
defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()
```

### Feedback Components

All feedback components should accept these common props (defined as `ActivityFeedbackProps`):

```typescript
interface ActivityFeedbackProps {
  /** Overall correctness score (0-100 scale) */
  progress: number
  /** Number of notches for progress visualization */
  notches: number
  /** Code variation results */
  codeResults: CodeResult[]
  /** Test execution results */
  testResults: TestResultDisplay[]
  /** Comprehension analysis results */
  comprehensionResults: string
  /** User's original prompt/input */
  userPrompt: string
  /** Segmentation analysis data (EiPL-specific) */
  segmentation: SegmentationData | null
  /** Reference solution code */
  referenceCode: string
  /** Problem type identifier */
  problemType: string
  /** Whether segmentation is enabled for this problem */
  segmentationEnabled: boolean
  /** Loading state */
  isLoading: boolean
  /** Navigation state */
  isNavigating: boolean
  /** Historical submission data */
  submissionHistory: SubmissionHistoryItem[]
  /** Title for the feedback section */
  title: string
}
```

And emit:

```typescript
defineEmits<{
  (e: 'load-attempt', attemptId: string): void
}>()
```

Type-specific props are passed through but only used by relevant components.

## Usage in Parent Components

### ProblemSet.vue

The `ProblemSet.vue` component uses the selectors:

```vue
<template>
  <!-- Input section -->
  <InputSelector
    :activity-type="currentProblem?.problem_type"
    :input-config="currentProblem?.input_config"
    :value="draftValue"
    @submit="handleSubmit"
  />

  <!-- Feedback section -->
  <FeedbackSelector
    :activity-type="currentProblem?.problem_type"
    :progress="feedback.progress"
    :segmentation-enabled="currentProblem?.feedback_config?.show_segmentation"
    :code-results="feedback.codeResults"
    :test-results="feedback.testResults"
  />
</template>
```

## Configuration Flow

1. **Backend Handler** provides `get_problem_config()` with type-specific config
2. **API Response** includes `input_config`, `feedback_config`, etc.
3. **Parent Component** passes config to selector components
4. **Selector** loads appropriate child component via registry
5. **Child Component** uses config to render type-specific UI

```
Backend Handler
    ↓
API Response (with configs)
    ↓
ProblemSet.vue (parent)
    ↓
InputSelector / FeedbackSelector
    ↓
EiplInput / McqInput / PromptInput
```

## Admin Editor Components

Admin editors follow a similar pattern in `components/admin/editors/`:

```typescript
// Admin editor registry (see ADMIN_PANEL_GUIDE.md for details)
const PROBLEM_EDITORS: ProblemEditorRegistry = {
  mcq: {
    editor: () => import('./McqProblemEditor.vue'),
    label: 'Multiple Choice Question',
    description: 'Multiple choice questions with explanations',
  },
  eipl: {
    editor: () => import('./EiplProblemEditor.vue'),
    label: 'Explain in Plain Language',
    description: 'Code explanation problems with test cases and hints',
  },
  prompt: {
    editor: () => import('./PromptProblemEditor.vue'),
    label: 'Prompt Problem',
    description: 'Image-based explanation problems',
  },
  debug_fix: {
    editor: () => import('./DebugFixProblemEditor.vue'),
    label: 'Debug and Fix Code',
    description: 'Student fixes buggy code to pass test cases',
  },
  probeable_code: {
    editor: () => import('./ProbeableCodeProblemEditor.vue'),
    label: 'Probeable Problem (Code)',
    description: 'Student discovers behavior via oracle, writes code',
  },
  probeable_spec: {
    editor: () => import('./ProbeableSpecProblemEditor.vue'),
    label: 'Probeable Problem (Explanation)',
    description: 'Student probes oracle, writes NL explanation',
  },
  refute: {
    editor: () => import('./RefuteProblemEditor.vue'),
    label: 'Refute: Find Counterexample',
    description: 'Student finds input that disproves a claim about a function',
  },
}
```

The admin editor registry also provides helper functions:
- `getProblemEditor(type)` - Get the editor component loader
- `getProblemEditorDefinition(type)` - Get the full definition (editor, label, description)
- `isProblemTypeRegistered(type)` - Check if a type has a registered editor
- `getRegisteredProblemTypes()` - Get all registered type names
- `getProblemEditorRegistry()` - Get a copy of the full registry

See [ADMIN_PANEL_GUIDE.md](../development/ADMIN_PANEL_GUIDE.md) for detailed admin editor documentation.

## Adding a New Activity Type

1. **Create Input Component**: `inputs/NewTypeInput.vue`
2. **Create Feedback Component**: `feedback/NewTypeFeedback.vue`
3. **Register in index.ts**:
   ```typescript
   ACTIVITY_COMPONENTS['new_type'] = {
     input: () => import('./inputs/NewTypeInput.vue'),
     feedback: () => import('./feedback/NewTypeFeedback.vue'),
   }
   ```
4. **Create Admin Editor** (if needed): `admin/editors/NewTypeEditor.vue`

## Types

Shared types are defined in `types.ts`:

```typescript
// Component Registry Types
export type ComponentLoader = () => Promise<{ default: Component | DefineComponent }>

export interface ActivityComponentDefinition {
  input: ComponentLoader
  feedback: ComponentLoader
}

export type ActivityComponentRegistry = Record<string, ActivityComponentDefinition>

// Activity Input/Feedback Props
export interface ActivityInputProps {
  modelValue: string
  problem: ActivityProblem
  activeHints?: HintConfig[]
  disabled?: boolean
  theme?: string
  draftSaved?: boolean
}

export interface ActivityFeedbackProps {
  progress: number
  notches: number
  codeResults: CodeResult[]
  testResults: TestResultDisplay[]
  comprehensionResults: string
  userPrompt: string
  segmentation: SegmentationData | null
  referenceCode: string
  problemType: string
  segmentationEnabled: boolean
  isLoading: boolean
  isNavigating: boolean
  submissionHistory: SubmissionHistoryItem[]
  title: string
}

// Supporting Types
export interface CodeResult {
  code: string
  variation_number: number
  passed_all_tests: boolean
  tests_passed: number
  total_tests: number
}

export interface TestResultDisplay {
  test_case_id?: number
  passed: boolean
  expected: string
  actual: string
  error_message?: string
  inputs: Record<string, unknown>
}

export interface McqResult {
  is_correct: boolean
  score?: number
  submission_id?: string
  selected_option?: { id: string; text: string }
  correct_option?: { id: string; text: string; explanation?: string }
  completion_status?: string
}

export interface SegmentationData {
  segments: Segment[]
  segment_count: number
  comprehension_level: 'relational' | 'multi_structural'
  feedback_message?: string
  passed?: boolean
  threshold?: number
  confidence_score?: number
  suggested_improvements?: string[]
  code_mappings?: unknown
}

// Probe Types (for probeable problem types)
export interface ProbeConfig {
  enabled?: boolean
  mode?: 'explore' | 'cooldown'
  max_probes?: number
  cooldown_attempts?: number
  cooldown_refill?: number
  function_signature?: string
  function_name?: string
  parameters?: ProbeParameter[]
}

export interface ProbeStatus {
  mode: 'block' | 'cooldown' | 'explore'
  remaining: number | null
  used: number
  can_probe: boolean
  message: string
  submissions_to_next_refill?: number
}
```

## Best Practices

1. **Use config over type checks**: Prefer `feedback_config.show_segmentation` over `problemType === 'eipl'`
2. **Lazy load components**: Use dynamic imports for activity components
3. **Provide fallbacks**: Handle unregistered types gracefully
4. **Keep components focused**: Each component handles one activity type
5. **Share common logic**: Use composables for shared functionality
