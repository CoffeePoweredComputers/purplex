# Admin Panel Guide for Problem Types

This guide documents how to create admin configuration panels for new problem types in Purplex.

## Overview

Purplex uses a modular admin interface where each problem type has its own editor component. The architecture follows these principles:

1. **Component Registry Pattern**: Editors are lazy-loaded based on problem type
2. **Orchestrator Composable**: A central `useProblemEditor()` composable manages all state
3. **Shared Components**: Common UI elements are extracted into reusable components
4. **Backend-Driven Config**: Activity type metadata comes from `/api/activity-types/`

## Architecture

### Directory Structure

```
purplex/client/src/
├── components/admin/
│   ├── AdminProblemEditorShell.vue    # Main shell/orchestrator
│   └── editors/
│       ├── index.ts                    # Component registry
│       ├── types.ts                    # TypeScript interfaces
│       ├── EiplProblemEditor.vue       # EiPL editor
│       ├── McqProblemEditor.vue        # MCQ editor
│       ├── PromptProblemEditor.vue     # Prompt editor
│       ├── DebugFixProblemEditor.vue   # Debug Fix editor
│       ├── ProbeableCodeProblemEditor.vue  # Probeable Code editor
│       ├── ProbeableSpecProblemEditor.vue  # Probeable Spec editor
│       ├── RefuteProblemEditor.vue     # Refute editor
│       └── shared/
│           ├── BasicInfoSection.vue    # Title, description, tags
│           ├── TestCasesSection.vue    # Test case management
│           ├── EditorToolbar.vue       # Editor toolbar controls
│           ├── SegmentationConfigSection.vue  # Segmentation config
│           └── ProbeSettingsSection.vue      # Probe mode settings
└── composables/admin/
    ├── index.ts                        # Public exports
    ├── useProblemEditor.ts             # Orchestrator
    ├── useProblemForm.ts               # Form state
    ├── useUIState.ts                   # Loading, errors
    ├── useFunctionSignature.ts         # Signature parsing
    ├── useTestCases.ts                 # Test case state
    ├── useHintsConfig.ts               # Hints config
    ├── useMcqOptions.ts                # MCQ options
    ├── useSegmentation.ts              # Segmentation config
    ├── usePromptConfig.ts              # Prompt/image config
    ├── useCategoryManager.ts           # Categories
    ├── useEditorSettings.ts            # Editor theme/font
    ├── useRefuteConfig.ts              # Refute problem config
    ├── useDebugFixConfig.ts            # Debug Fix problem config
    ├── useProbeConfig.ts               # Base probe settings
    ├── useProbeableCodeConfig.ts       # Probeable Code config
    ├── useProbeableSpecConfig.ts       # Probeable Spec config
    └── problemTypeHandlers.ts          # Type-specific handlers
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   AdminProblemEditorShell.vue                    │
│  - Problem type selector                                         │
│  - Save/Test buttons                                             │
│  - Dynamic editor loading                                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ props.editor
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      {Type}ProblemEditor.vue                     │
│  - Type-specific UI sections                                     │
│  - Validation logic                                              │
│  - Emits: validation-change, save, test                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ uses
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       useProblemEditor()                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                │
│  │ useProblemForm │ useTestCases  │ useHintsConfig │   ...       │
│  └─────────────┘ └─────────────┘ └─────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

## Component Registry

### Registration (editors/index.ts)

The `PROBLEM_EDITORS` registry maps problem types to their editor definitions:

```typescript
import type { ProblemEditorRegistry, ProblemEditorDefinition } from './types'

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

### Helper Functions

```typescript
// Get the lazy loader for a problem type
getProblemEditor(type: string): EditorComponentLoader | undefined

// Get full definition including label/description
getProblemEditorDefinition(type: string): ProblemEditorDefinition | undefined

// Get the full registry object
getProblemEditorRegistry(): ProblemEditorRegistry

// List all registered types
getRegisteredProblemTypes(): string[]

// Check if a type is registered
isProblemTypeRegistered(type: string): boolean
```

## Type Interfaces (editors/types.ts)

### ProblemEditorProps

Every editor component receives these props:

```typescript
export interface ProblemEditorProps {
  /** The orchestrating composable - provides ALL state and methods */
  editor: UseProblemEditorReturn
  /** Current problem slug (null for new problems) */
  slug: string | null
  /** Whether currently editing vs creating */
  isEditing: boolean
}
```

### ProblemEditorEmits

Every editor must emit these events:

```typescript
export interface ProblemEditorEmits {
  (e: 'save'): void
  (e: 'test'): void
  (e: 'validation-change', isValid: boolean): void
}
```

### ProblemEditorDefinition

Registry entry structure:

```typescript
export interface ProblemEditorDefinition {
  /** Lazy loader for the editor component */
  editor: EditorComponentLoader
  /** Display label for the problem type */
  label: string
  /** Optional description shown in UI */
  description?: string
}
```

## Creating a New Admin Editor

### Step 1: Create the Editor Component

Create `purplex/client/src/components/admin/editors/{Type}ProblemEditor.vue`:

```vue
<template>
  <div class="{type}-problem-editor">
    <!-- Basic Information (always include) -->
    <BasicInfoSection :editor="editor" />

    <!-- Type-specific sections go here -->
    <div class="form-section rounded-lg border-default">
      <h3>Type-Specific Configuration</h3>
      <!-- Your type-specific form fields -->
    </div>

    <!-- Include TestCasesSection if type supports test cases -->
    <TestCasesSection
      v-if="supportsTestCases"
      :editor="editor"
      @test="$emit('test')"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { ProblemEditorProps, ProblemEditorEmits } from './types'
import BasicInfoSection from './shared/BasicInfoSection.vue'
import TestCasesSection from './shared/TestCasesSection.vue'

// Props and emits - ALWAYS define these
const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// Access editor from props (provides all state/methods)
const editor = computed(() => props.editor)

// Validation - REQUIRED
const isValid = computed(() => {
  const title = (editor.value.form.form.title || '').toString().trim()
  if (!title) return false

  // Add type-specific validation
  // ...

  return true
})

// Emit validation state changes - REQUIRED
watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })

// Expose validate method for parent - REQUIRED
defineExpose({
  validate: () => isValid.value,
})
</script>

<style scoped>
/* Use CSS variables for consistency */
.form-section {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
  margin-bottom: var(--spacing-xxl);
}

.form-section h3 {
  margin: 0 0 var(--spacing-xl) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-border);
}

/* Common utility classes */
.rounded-lg { border-radius: var(--radius-lg); }
.border-default { border: 2px solid var(--color-bg-border); }
</style>
```

### Step 2: Register the Editor

Add to `purplex/client/src/components/admin/editors/index.ts`:

```typescript
const PROBLEM_EDITORS: ProblemEditorRegistry = {
  // ... existing entries

  your_type: {
    editor: () => import('./YourTypeProblemEditor.vue'),
    label: 'Your Problem Type',
    description: 'Description of what this type does',
  },
}
```

### Step 3: Create Composable (if needed)

If your type needs state management beyond what exists, create a composable:

```typescript
// purplex/client/src/composables/admin/useYourTypeConfig.ts
import { ref, computed, type Ref, type ComputedRef } from 'vue'

export interface YourTypeConfig {
  // Your config fields
  customField: string
  someFlag: boolean
}

export interface UseYourTypeConfigReturn {
  // State
  config: YourTypeConfig

  // Computed
  isValid: ComputedRef<boolean>

  // Methods
  setCustomField: (value: string) => void
  loadConfig: (data: Partial<YourTypeConfig>) => void
  getConfigForApi: () => YourTypeConfig
  reset: () => void
}

const createDefaultConfig = (): YourTypeConfig => ({
  customField: '',
  someFlag: false,
})

export const useYourTypeConfig = (): UseYourTypeConfigReturn => {
  const config = ref<YourTypeConfig>(createDefaultConfig())

  const isValid = computed(() => {
    return config.value.customField.trim().length > 0
  })

  const setCustomField = (value: string) => {
    config.value.customField = value
  }

  const loadConfig = (data: Partial<YourTypeConfig>) => {
    config.value = { ...createDefaultConfig(), ...data }
  }

  const getConfigForApi = (): YourTypeConfig => {
    return { ...config.value }
  }

  const reset = () => {
    config.value = createDefaultConfig()
  }

  return {
    config,
    isValid,
    setCustomField,
    loadConfig,
    getConfigForApi,
    reset,
  }
}
```

Then integrate in `useProblemEditor.ts`:
- Import the composable
- Initialize it
- Add to return object
- Handle in `loadProblem()` and `saveProblem()`

### Step 4: Backend Handler Integration

Your backend handler's `get_admin_config()` method should return:

```python
def get_admin_config(self) -> Dict:
    return {
        'hidden_sections': [],  # Sections to hide: 'hints', 'segmentation', etc.
        'required_fields': ['title', 'your_required_field'],
        'optional_fields': ['description'],
        'type_specific_section': 'your_config_key',  # Or None
        'supports': {
            'hints': True,          # Show hints config
            'segmentation': True,   # Show segmentation config
            'test_cases': True,     # Show test cases section
        }
    }
```

## Type-Specific Configuration Reference

### EiPL (Explain in Plain Language)

**Required Fields:**
- `title`: Problem title
- `function_signature`: Python function signature with type hints
- `reference_solution`: Complete Python solution
- `test_cases`: At least one test case

**Optional Fields:**
- `description`: Problem description
- `tags`: Array of string tags
- `category_ids`: Array of category IDs

**Hints Configuration:**
- Variable Fade: `{ is_enabled, min_attempts, content: { mappings: [{ from, to }] } }`
- Subgoal Highlight: `{ is_enabled, min_attempts, content: { subgoals: [{ title, explanation, line_start, line_end }] } }`
- Suggested Trace: `{ is_enabled, min_attempts, content: { suggested_call } }`

**Segmentation Configuration:**
```typescript
{
  is_enabled: boolean
  threshold: number  // Default 3
  examples: {
    relational: {
      prompt: string
      segments: Array<{ text: string, code_lines: number[] }>
    }
    multi_structural: {
      prompt: string
      segments: Array<{ text: string, code_lines: number[] }>
    }
  }
}
```

### MCQ (Multiple Choice Question)

**Required Fields:**
- `title`: Problem title (used as question)
- `options`: Array of 2-6 options

**Options Structure:**
```typescript
interface McqOption {
  id: string           // UUID
  text: string         // Option text
  is_correct: boolean  // True for correct answer
  explanation?: string // Shown when selected
}
```

**Validation:**
- Minimum 2 options, maximum 6
- At least one option must be marked correct
- All options must have non-empty text

### Prompt (Image-based)

**Required Fields:**
- `title`: Problem title
- `prompt_config.image_url`: Valid URL to image
- `function_signature`: Function signature
- `reference_solution`: Code solution
- `test_cases`: At least one test case

**Prompt Config Structure:**
```typescript
interface PromptConfig {
  image_url: string
  alt_text?: string
}
```

### Refute (Counterexample Challenge)

**Required Fields:**
- `title`: Problem title
- `claim_text`: The claim to refute
- `reference_solution`: Code implementing the claim
- `function_signature`: Function signature
- `expected_counterexample`: Example input that breaks the claim

**Config Structure:**
```typescript
interface RefuteConfig {
  claim_text: string
  expected_counterexample: {
    inputs: any[]
    why_it_fails: string
  }
}
```

### Debug Fix

**Required Fields:**
- `title`: Problem title
- `buggy_code`: Code containing bugs
- `reference_solution`: Correct version
- `function_signature`: Function signature
- `test_cases`: Tests that expose the bugs

**Config Structure:**
```typescript
interface DebugFixConfig {
  buggy_code: string
  bug_hints?: string[]       // Hints about the bugs
  allow_complete_rewrite: boolean  // Allow full replacement vs minimal fix
}
```

### Probeable Code

**Required Fields:**
- `title`: Problem title
- `reference_solution`: Hidden code to probe
- `function_signature`: Function signature
- `test_cases`: Expected behavior tests

**Config Structure:**
```typescript
interface ProbeableCodeConfig {
  probe_mode: 'function' | 'expression'
  max_probes: number         // -1 for unlimited
  cooldown_seconds: number   // Between probes
}
```

### Probeable Spec

**Required Fields:**
- `title`: Problem title
- `specification`: Natural language spec
- `function_signature`: Function signature
- `reference_solution`: Reference implementation

**Config Structure:**
```typescript
interface ProbeableSpecConfig {
  specification: string
  probe_mode: 'function' | 'expression'
  max_probes: number
  cooldown_seconds: number
  segmentation_config?: SegmentationConfig
}
```

## Shared Components

### BasicInfoSection

Handles title, description, and tags. Always include this:

```vue
<BasicInfoSection :editor="editor" />
```

### TestCasesSection

Test case management with smart parameter inputs:

```vue
<TestCasesSection
  :editor="editor"
  @test="$emit('test')"
/>
```

The component:
- Parses function signature for parameter types
- Validates input types against expected types
- Shows test results with pass/fail status
- Supports add/remove operations

### EditorToolbar

Provides common editor toolbar controls for code editors.

```vue
<EditorToolbar :editor="editor" />
```

### SegmentationConfigSection

Configures segmentation examples for SOLO taxonomy levels:

```vue
<SegmentationConfigSection :editor="editor" />
```

The component:
- Manages relational and multi-structural examples
- Configures prompt text and segment mappings
- Validates segment code line references

### ProbeSettingsSection

Configures probe mode settings for probeable problem types:

```vue
<ProbeSettingsSection :editor="editor" />
```

The component:
- Selects probe mode (function vs expression)
- Configures max probes and cooldown
- Shared between ProbeableCode and ProbeableSpec editors

## Validation Patterns

### Basic Pattern

```typescript
const isValid = computed(() => {
  const form = editor.value.form.form

  // Title always required
  const title = (form.title || '').toString().trim()
  if (!title) return false

  // Type-specific validation
  if (!someRequiredField) return false
  if (!anotherCheck()) return false

  return true
})

// Emit changes
watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })

// Expose for parent
defineExpose({
  validate: () => isValid.value,
})
```

### Complex Validation with Error Messages

```typescript
const validationErrors = computed(() => {
  const errors: string[] = []

  if (!editor.value.form.form.title?.trim()) {
    errors.push('Title is required')
  }

  if (someSpecificCheck()) {
    errors.push('Specific field validation failed')
  }

  return errors
})

const isValid = computed(() => validationErrors.value.length === 0)
```

## Best Practices

### 1. Keep Components Modular

- Extract reusable sections into shared components
- Use composables for complex state management
- Keep editor components focused on UI

### 2. Use the Orchestrator

Always access state through `props.editor`:

```typescript
// Good
const editor = computed(() => props.editor)
const title = editor.value.form.form.title

// Avoid - don't create separate state
const localTitle = ref('')  // Don't do this
```

### 3. Handle Loading States

```vue
<div v-if="editor.ui.ui.loading" class="loading-overlay">
  <div class="spinner" />
</div>
```

### 4. Emit Validation Changes

The shell disables save when validation fails:

```typescript
watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })
```

### 5. Use CSS Variables

For consistent styling:

```css
.form-section {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-bg-border);
}
```

### 6. Preview Functionality

If your type has visual output, add a preview:

```vue
<div v-if="hasPreviewableContent" class="preview-section">
  <label>Preview</label>
  <div class="preview-container">
    <!-- Render preview -->
  </div>
</div>
```

## Complete Template

Here's a complete template for a new problem type editor:

```vue
<template>
  <div class="new-type-problem-editor">
    <!-- Basic Information -->
    <BasicInfoSection :editor="editor" />

    <!-- Type-Specific Configuration -->
    <div class="form-section rounded-lg border-default">
      <h3>Configuration Section</h3>
      <p class="section-description">
        Instructions for this section.
      </p>

      <div class="form-group">
        <label for="custom_field">Custom Field *</label>
        <input
          id="custom_field"
          type="text"
          :value="customFieldValue"
          :class="{ 'input-error': !isCustomFieldValid }"
          placeholder="Enter value"
          @input="updateCustomField"
        >
        <p v-if="!isCustomFieldValid" class="field-error">
          Please enter a valid value
        </p>
      </div>

      <!-- Toggle option -->
      <div class="form-group">
        <label class="toggle-label">
          <input
            type="checkbox"
            :checked="someToggle"
            @change="handleToggle"
          >
          <span>Enable some feature</span>
        </label>
        <p class="field-hint">
          Explanation of what this toggle does
        </p>
      </div>
    </div>

    <!-- Code Solution (if applicable) -->
    <div class="form-section rounded-lg border-default">
      <h3>Code Solution</h3>

      <div class="form-group">
        <label for="function_signature">Function Signature *</label>
        <input
          id="function_signature"
          type="text"
          :value="editor.form.form.function_signature"
          placeholder="def example(x: int) -> int:"
          @input="updateField('function_signature', $event)"
        >
      </div>

      <div class="form-group">
        <label>Reference Solution *</label>
        <div class="code-editor">
          <Editor
            :value="String(editor.form.form.reference_solution || '')"
            :height="'300px'"
            :theme="editor.editorSettings.theme.value"
            :mode="'python'"
            @update:value="editor.form.updateReferenceSolution($event)"
          />
        </div>
      </div>
    </div>

    <!-- Test Cases (if applicable) -->
    <TestCasesSection
      :editor="editor"
      @test="$emit('test')"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { ProblemEditorProps, ProblemEditorEmits } from './types'
import { log } from '@/utils/logger'
import Editor from '@/features/editor/Editor.vue'
import BasicInfoSection from './shared/BasicInfoSection.vue'
import TestCasesSection from './shared/TestCasesSection.vue'

// ===== Props & Emits =====
const props = defineProps<ProblemEditorProps>()
const emit = defineEmits<ProblemEditorEmits>()

// ===== Editor Access =====
const editor = computed(() => props.editor)

// ===== Local State (if needed) =====
const customFieldValue = ref('')
const someToggle = ref(false)

// ===== Computed Validation =====
const isCustomFieldValid = computed(() => {
  return customFieldValue.value.trim().length > 0
})

const isValid = computed(() => {
  const form = editor.value.form.form

  // Title required
  const title = (form.title || '').toString().trim()
  if (!title) return false

  // Custom field required
  if (!isCustomFieldValid.value) return false

  // Code fields (if applicable)
  const signature = (form.function_signature || '').toString().trim()
  if (!signature) return false

  const solution = (form.reference_solution || '').toString().trim()
  if (!solution) return false

  // Test cases (if applicable)
  if (editor.value.testCases.testCases.value.length === 0) return false

  return true
})

// ===== Emit Validation =====
watch(isValid, (valid) => {
  emit('validation-change', valid)
}, { immediate: true })

// ===== Methods =====
function updateField(field: string, event: Event) {
  const value = (event.target as HTMLInputElement).value
  editor.value.form.updateField(field as any, value)
}

function updateCustomField(event: Event) {
  customFieldValue.value = (event.target as HTMLInputElement).value
  // If using a composable, update it here
  // editor.value.newTypeConfig.setCustomField(customFieldValue.value)
}

function handleToggle(event: Event) {
  someToggle.value = (event.target as HTMLInputElement).checked
}

// ===== Lifecycle =====
onMounted(() => {
  log.info('NewTypeProblemEditor mounted', { isEditing: props.isEditing })

  // Load existing values if editing
  if (props.isEditing) {
    // customFieldValue.value = editor.value.newTypeConfig.customField
  }
})

// ===== Expose Validate =====
defineExpose({
  validate: () => isValid.value,
})
</script>

<style scoped>
/* Utility Classes */
.rounded-lg { border-radius: var(--radius-lg); }
.border-default { border: 2px solid var(--color-bg-border); }

/* Layout */
.new-type-problem-editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xxl);
}

/* Form Sections */
.form-section {
  background: var(--color-bg-panel);
  padding: var(--spacing-xl);
  box-shadow: var(--shadow-base);
}

.form-section h3 {
  margin: 0 0 var(--spacing-xl) 0;
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
  font-weight: 600;
  padding-bottom: var(--spacing-base);
  border-bottom: 2px solid var(--color-bg-border);
}

.section-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin-bottom: var(--spacing-lg);
}

/* Form Groups */
.form-group {
  margin-bottom: var(--spacing-lg);
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
  font-size: var(--font-size-sm);
}

/* Inputs */
.form-group input[type="text"],
.form-group input[type="url"],
.form-group textarea {
  width: 100%;
  padding: var(--spacing-md);
  background: var(--color-bg-input);
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  transition: var(--transition-base);
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary-gradient-start);
  background: var(--color-bg-panel);
}

.input-error {
  border-color: var(--color-error) !important;
}

/* Hints and Errors */
.field-error {
  color: var(--color-error);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

.field-hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
  margin-top: var(--spacing-xs);
}

/* Toggles */
.toggle-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.toggle-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

/* Code Editor */
.code-editor {
  border: 2px solid var(--color-bg-border);
  border-radius: var(--radius-base);
  overflow: hidden;
}
</style>
```

## Troubleshooting

### Editor Not Loading

1. Check registration in `editors/index.ts`
2. Verify the file path in the lazy import
3. Check browser console for import errors

### Validation Not Working

1. Ensure `watch(isValid, ...)` is set up with `{ immediate: true }`
2. Verify `emit('validation-change', valid)` is called
3. Check that `defineExpose({ validate })` is present

### State Not Persisting

1. Use the orchestrator's composables, not local state
2. If using local state, sync with composable on mount/change
3. Check `loadProblem()` and `saveProblem()` in `useProblemEditor.ts`

### Test Cases Not Appearing

1. Ensure `TestCasesSection` is included in template
2. Check that backend handler's `get_admin_config()` has `supports.test_cases: true`
3. Verify function signature is being parsed correctly

## Related Documentation

- [New Problem Type Guide](./NEW_PROBLEM_TYPE_GUIDE.md)
- [Handler Implementation Details](../frontend/HANDLER_IMPLEMENTATION_DETAILS.md)
- [Problem Types Architecture](../architecture/PROBLEM_TYPES.md)
- [Frontend Component Structure](../frontend/FRONTEND_COMPONENT_STRUCTURE.md)
