<template>
  <VAceEditor
    ref="vAceRef"
    :lang="lang"
    :theme="theme"
    :mode="mode"
    :style="editorStyle"
    :value="value"
    :options="{ readOnly: readOnly }"
    @init="editorInit"
    @update:value="handleInput"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { VAceEditor } from 'vue3-ace-editor'
import ace from 'ace-builds'
import 'ace-builds/src-noconflict/mode-python'
import 'ace-builds/src-noconflict/theme-clouds_midnight'
import 'ace-builds/src-noconflict/theme-chrome'
import 'ace-builds/src-noconflict/theme-monokai'
import 'ace-builds/src-noconflict/theme-github'
import 'ace-builds/src-noconflict/theme-solarized_dark'
import 'ace-builds/src-noconflict/theme-solarized_light'
import 'ace-builds/src-noconflict/theme-dracula'
import 'ace-builds/src-noconflict/theme-tomorrow_night'

// Marker definition for line highlighting
interface EditorMarker {
  row: number
  className: string
}

// Ace Editor instance type - minimal interface for what we use
interface AceEditor {
  setOptions(options: Record<string, unknown>): void
  container: HTMLElement
  renderer: {
    $cursorLayer: { element: { style: { display: string } } }
    container: { style: { pointerEvents: string; userSelect: string } }
  }
  session: {
    addMarker(range: unknown, className: string, type: string, inFront: boolean): number
    removeMarker(id: number): void
  }
  setOption(name: string, value: unknown): void
  getOption(name: string): unknown
  getValue(): string
  setValue(value: string, cursorPos?: number): void
  resize(force?: boolean): void
  commands: { addCommand(command: { name: string; bindKey: { win: string; mac: string }; exec: (editor: AceEditor) => void }): void }
  blur(): void
}

const props = withDefaults(defineProps<{
  lang?: string
  theme?: string
  mode?: string
  height?: string
  width?: string
  showGutter?: boolean
  characterLimit?: number | null
  minLines?: number | null
  maxLines?: number | null
  extraLines?: number
  value?: string
  readOnly?: boolean
  markers?: EditorMarker[]
  tabTargetId?: string | null
  focusScopeSelector?: string | null
}>(), {
  lang: 'python',
  theme: 'tomorrow_night',
  mode: 'python',
  height: '300px',
  width: '500px',
  showGutter: true,
  characterLimit: null,
  minLines: null,
  maxLines: null,
  extraLines: 0,
  value: '',
  readOnly: false,
  markers: () => [],
  tabTargetId: null,
  focusScopeSelector: null
})

const emit = defineEmits<{
  (e: 'update:value', value: string): void
}>()

const editor = ref<AceEditor | null>(null)
const vAceRef = ref<{ _contentBackup?: string } | null>(null)
let lastMinLines: number | null = null
const activeMarkerIds: number[] = []

/** Clear all managed markers from the ACE session */
function clearMarkers(): void {
  if (!editor.value) {return}
  for (const id of activeMarkerIds) {
    editor.value.session.removeMarker(id)
  }
  activeMarkerIds.length = 0
}

/** Apply marker definitions to the ACE session as fullLine markers */
function applyMarkers(): void {
  clearMarkers()
  if (!editor.value || !props.markers?.length) {return}

  const { Range } = ace.require('ace/range')
  for (const marker of props.markers) {
    const range = new Range(marker.row, 0, marker.row, 1)
    const id = editor.value.session.addMarker(range, marker.className, 'fullLine', false)
    activeMarkerIds.push(id)
  }
}

// When using minLines/maxLines, OMIT the height key entirely so Vue's
// patchStyle never touches el.style.height — ACE's $autosize manages it.
// Including `height: undefined` would cause Vue to clear it to "" on every re-render.
const editorStyle = computed(() => {
  const useAutoHeight = props.minLines !== null || props.maxLines !== null
  if (useAutoHeight) {
    return { width: props.width }
  }
  return { height: props.height, width: props.width }
})

/* Simple editor initialization */
function editorInit(editorInstance: AceEditor): void {
  editor.value = editorInstance
  const baseMaxLines = props.maxLines ?? props.characterLimit ?? undefined

  // Calculate minLines: use prop value, but if extraLines is set and content
  // exceeds minLines, add buffer lines
  let effectiveMinLines = props.minLines ?? undefined
  if (props.extraLines > 0 && effectiveMinLines !== undefined) {
    const contentLines = (props.value?.split('\n').length ?? 0)
    if (contentLines > effectiveMinLines) {
      effectiveMinLines = contentLines + props.extraLines
    }
  }

  editorInstance.setOptions({
    showGutter: props.showGutter,
    showFoldWidgets: !props.readOnly,
    minLines: effectiveMinLines,
    maxLines: baseMaxLines ? baseMaxLines + props.extraLines : undefined,
    readOnly: props.readOnly,
    highlightActiveLine: false,
    highlightGutterLine: false,
    showPrintMargin: false,
    wrap: true,
    indentedSoftWrap: false
  })

  // Make editor container tabbable
  editorInstance.container.setAttribute('tabindex', '0')

  // Disable cursor visibility when read-only
  if (props.readOnly) {
    editorInstance.renderer.$cursorLayer.element.style.display = 'none'
    editorInstance.setOption('showCursor', false)
    editorInstance.renderer.container.style.pointerEvents = 'none'
    editorInstance.renderer.container.style.userSelect = 'text'
  }

  // CRITICAL ACCESSIBILITY FIX: Override Tab key behavior to allow tabbing out
  // By default, ACE captures Tab for indentation, creating a keyboard trap

  // Resolve the focus scope once: dialog ancestor or the whole document
  const focusScope: Element | Document = (() => {
    if (props.focusScopeSelector) {
      return editorInstance.container.closest(props.focusScopeSelector) ?? document
    }
    return editorInstance.container.closest('[role="dialog"]') ?? document
  })()
  const isInDialog = focusScope !== document

  // Helper function to get all focusable elements (excluding ACE editor internals)
  // Scopes to nearest dialog to avoid escaping modal focus traps
  const getFocusableElements = () => {
    return Array.from(focusScope.querySelectorAll(
      'button:not([disabled]):not([tabindex="-1"]), ' +
      '[href]:not([tabindex="-1"]), ' +
      'input:not([disabled]):not([tabindex="-1"]), ' +
      'select:not([disabled]):not([tabindex="-1"]), ' +
      'textarea:not([disabled]):not([tabindex="-1"]), ' +
      '[tabindex]:not([tabindex="-1"])'
    )).filter((el) => {
      // Filter out hidden elements and ACE editor internal elements
      const htmlEl = el as HTMLElement
      const isVisible = htmlEl.offsetParent !== null &&
             getComputedStyle(htmlEl).visibility !== 'hidden' &&
             getComputedStyle(htmlEl).display !== 'none'

      // Exclude elements inside ACE editor (except the container itself)
      const isAceInternal = htmlEl.classList.contains('ace_text-input') ||
                           htmlEl.classList.contains('ace_content')

      return isVisible && !isAceInternal
    })
  }

  editorInstance.commands.addCommand({
    name: 'overrideTab',
    bindKey: { win: 'Tab', mac: 'Tab' },
    exec: function(aceEditor: AceEditor) {
      // Temporarily remove tabindex to prevent re-focusing
      const container = aceEditor.container
      const originalTabIndex = container.getAttribute('tabindex')
      container.setAttribute('tabindex', '-1')

      aceEditor.blur()

      setTimeout(() => {
        // Restore tabindex
        container.setAttribute('tabindex', originalTabIndex || '0')

        const focusableElements = getFocusableElements()
        const currentIndex = focusableElements.indexOf(container)

        if (currentIndex !== -1 && currentIndex < focusableElements.length - 1) {
          const nextElement = focusableElements[currentIndex + 1] as HTMLElement
          nextElement.focus()
        } else if (isInDialog && focusableElements.length > 0) {
          // Inside a dialog: wrap to first focusable element
          (focusableElements[0] as HTMLElement).focus()
        } else {
          // Main page: use custom tab target or fall back to submit button
          const targetId = props.tabTargetId || 'submitButton'
          const targetElement = document.getElementById(targetId)
          if (targetElement) {
            const innerEditor = targetElement.querySelector('.ace_text-input')
            if (innerEditor) {
              (innerEditor as HTMLElement).focus()
            } else {
              targetElement.focus()
            }
          }
        }
      }, 10)
    }
  })

  // Shift+Tab to move focus backward
  editorInstance.commands.addCommand({
    name: 'overrideShiftTab',
    bindKey: { win: 'Shift-Tab', mac: 'Shift-Tab' },
    exec: function(aceEditor: AceEditor) {
      // Temporarily remove tabindex to prevent re-focusing
      const container = aceEditor.container
      const originalTabIndex = container.getAttribute('tabindex')
      container.setAttribute('tabindex', '-1')

      aceEditor.blur()

      setTimeout(() => {
        // Restore tabindex
        container.setAttribute('tabindex', originalTabIndex || '0')

        const focusableElements = getFocusableElements()
        const currentIndex = focusableElements.indexOf(container)

        if (currentIndex > 0) {
          const prevElement = focusableElements[currentIndex - 1] as HTMLElement
          prevElement.focus()
        } else if (isInDialog && focusableElements.length > 0) {
          // Inside a dialog: wrap to last focusable element
          (focusableElements[focusableElements.length - 1] as HTMLElement).focus()
        }
      }, 10)
    }
  })

  // Keep Escape key handler as alternative exit method
  editorInstance.commands.addCommand({
    name: 'exitEditor',
    bindKey: { win: 'Esc', mac: 'Esc' },
    exec: function(aceEditor: AceEditor) {
      aceEditor.blur()

      setTimeout(() => {
        // Try tabTargetId prop first
        if (props.tabTargetId) {
          const target = document.getElementById(props.tabTargetId)
          if (target) { target.focus(); return }
        }
        // Try close button in nearest dialog
        const dialog = aceEditor.container.closest('[role="dialog"]')
        if (dialog) {
          const closeBtn = dialog.querySelector('[aria-label="Close modal"]') as HTMLElement
          if (closeBtn) { closeBtn.focus(); return }
        }
        // Final fallback: submit button
        const submitBtn = document.getElementById('submitButton')
        if (submitBtn) {
          submitBtn.focus()
        }
      }, 10)
    }
  })
}

/* Handle input changes */
function handleInput(value: string): void {
  emit('update:value', value)
}

/* Simple value update - just replace the entire content */
watch(() => props.value, (newValue) => {
  if (editor.value && newValue !== undefined) {
    const currentValue = editor.value.getValue()
    if (currentValue !== newValue) {
      // Without freeze, setValue() and applyMarkers() merely schedule render
      // changes via ACE's $loop.schedule() — no immediate repaint occurs
      // because JS is single-threaded. The final resize(true) forces a
      // synchronous flush of ALL pending changes including $autosize,
      // producing correct layout in one pass with no flicker.
      editor.value.setValue(newValue, 1)
      applyMarkers()
      // Sync VAceEditor's internal backup so its own value watcher
      // sees the content is already current and skips its unprotected setValue
      if (vAceRef.value) {
        vAceRef.value._contentBackup = newValue
      }
    }

    // Update minLines if extraLines is set - only when value actually changes
    // Placed before resize so it's included in the same synchronous render pass
    if (props.extraLines > 0 && props.minLines !== null) {
      const contentLines = newValue.split('\n').length
      const effectiveMinLines = contentLines > props.minLines
        ? contentLines + props.extraLines
        : props.minLines
      if (effectiveMinLines !== lastMinLines) {
        lastMinLines = effectiveMinLines
        editor.value.setOption('minLines', effectiveMinLines)
      }
    }

    // Single synchronous resize flushes all pending render changes
    // (setValue, markers, minLines) in one pass including $autosize
    if (currentValue !== newValue) {
      editor.value.resize(true)
    }
  }
}, { immediate: true })

/* Reapply markers when marker prop changes independently of value */
watch(() => props.markers, () => {
  applyMarkers()
}, { deep: true })

// Expose editor instance if needed
defineExpose({
  editor
})
</script>

<style scoped>
  /* Editor wrapper styling to match design system */
  :deep(.ace_editor) {
    border-radius: var(--radius-lg);
    border: 2px solid var(--color-bg-input);
    box-shadow: var(--shadow-md);
    font-family: Monaco, Menlo, 'Ubuntu Mono', monospace;
    font-size: var(--font-size-sm);

    /* Transition only visual properties — never height/width.
       ACE's $autosize sets container height synchronously; animating it
       creates a ResizeObserver feedback loop that corrupts cached layout. */
    transition-property: border-color, box-shadow;
    transition-duration: 0.3s;
    transition-timing-function: ease;
  }

  /* Remove extra padding at bottom when using auto-height (minLines/maxLines) */
  :deep(.ace_scroller) {
    padding-bottom: 0 !important;
  }

  /* Fix text wrapping - ensure wrapped lines maintain proper indentation */
  :deep(.ace_text-layer .ace_line) {
    white-space: pre-wrap;
    overflow-wrap: break-word;

    /* Use hanging indent to align wrapped text properly */
    padding-left: 0;
    text-indent: 0;
  }

  /* Ensure proper hanging indent for wrapped text */
  :deep(.ace_content) {
    overflow-wrap: break-word;
  }

  /* Alternative approach: use CSS hanging-punctuation if needed */
  :deep(.ace_line_group) {
    text-indent: 0;

    /* Maintain consistent spacing for wrapped content */
    line-height: 1.2;
  }

  :deep(.ace_editor:hover) {
    border-color: var(--color-primary-gradient-start);
    box-shadow: var(--shadow-lg);
  }

  /* Gutter styling */
  :deep(.ace_gutter) {
    background: var(--color-bg-section);
    color: var(--color-text-muted);
    border-right: 1px solid var(--color-bg-input);
  }

  :deep(.ace_gutter-cell) {
    color: var(--color-text-muted);
    padding-right: var(--spacing-md);
    padding-left: var(--spacing-sm);
  }

  :deep(.ace_gutter-active-line) {
    background: var(--color-bg-input);
    color: var(--color-text-primary);
  }

  /* Scrollbar styling */
  :deep(.ace_scrollbar::-webkit-scrollbar) {
    width: 12px;
    height: 12px;
  }

  :deep(.ace_scrollbar::-webkit-scrollbar-track) {
    background: var(--color-bg-section);
    border-radius: var(--radius-sm);
  }

  :deep(.ace_scrollbar::-webkit-scrollbar-thumb) {
    background: var(--color-bg-border);
    border-radius: var(--radius-sm);
    border: 2px solid var(--color-bg-hover);
  }

  :deep(.ace_scrollbar::-webkit-scrollbar-thumb:hover) {
    background: var(--color-primary-gradient-start);
  }

  /* Selection styling */
  :deep(.ace_selection) {
    background: var(--color-ace-selection) !important;
    color: var(--color-text-primary) !important;
  }

  /* Active line highlighting */
  :deep(.ace_active-line) {
    background: var(--color-primary-overlay);
  }

  /* Cursor styling */
  :deep(.ace_cursor) {
    color: var(--color-primary-gradient-start);
    border-left: 2px solid var(--color-primary-gradient-start);
  }

  /* Bracket matching */
  :deep(.ace_bracket) {
    margin: -1px -1px 0;
    border: 1px solid var(--color-primary-gradient-start);
    background: var(--color-primary-overlay);
  }

  /* Search highlights */
  :deep(.ace_selected-word) {
    border: 1px solid var(--color-primary-gradient-start);
    background: var(--color-primary-overlay);
  }


  /* Print margin */
  :deep(.ace_print-margin) {
    background: var(--color-bg-border);
    width: 1px;
  }

  /* Fold widgets */
  :deep(.ace_fold-widget) {
    color: var(--color-text-muted);
  }

  :deep(.ace_fold-widget:hover) {
    color: var(--color-primary-gradient-start);
  }

  /* Indent guides */
  :deep(.ace_indent-guide) {
    background: none;
    border-right: 1px solid var(--color-bg-border);
  }

  /* Hint System Styles */

  /* Variable fade has no visual styling - just transforms variable names */

  /* Subgoal highlighting: force comment tokens to have transparent backgrounds
     so fullLine marker backgrounds show through consistently across all themes */
  :deep(.ace_comment) {
    background-color: transparent !important;
  }

  /* Hide cursor only for read-only editors */
  :deep(.ace_editor.ace_read-only .ace_cursor-layer) {
    display: none !important;
  }

  :deep(.ace_editor.ace_read-only .ace_cursor) {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
  }

  /* Remove active line highlighting only for read-only editors */
  :deep(.ace_editor.ace_read-only .ace_active-line) {
    background: transparent !important;
  }

  /* Make editor truly read-only visually */
  :deep(.ace_editor.ace_read-only) {
    cursor: default !important;
  }

  :deep(.ace_editor.ace_read-only .ace_content) {
    cursor: text !important;
  }


  @keyframes pulse-subgoal {
    0% {
      background: var(--color-warning-overlay);
    }

    50% {
      background: var(--color-warning-overlay);
    }

    100% {
      background: var(--color-warning-overlay);
    }
  }

  :deep(.suggested-trace) {
    background: var(--color-warning-overlay);
    border-right: 3px solid var(--color-warning);
    font-style: italic;
    position: relative;
  }

  :deep(.suggested-trace)::after {
    content: "🔍";
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0.6;
  }

  :deep(.suggestion-instructions) {
    background: var(--color-info-overlay);
    border-right: 3px solid var(--color-info);
  }

  :deep(.suggestion-test_case) {
    background: var(--color-warning-overlay);
    border-right: 3px solid var(--color-warning);
  }

  /* Annotation styles for hint system */
  :deep(.ace_gutter .subgoal-annotation) {
    background: var(--color-success-overlay);
    border-radius: 3px;
    padding: 2px 4px;
    margin: 1px 0;
  }
</style>
