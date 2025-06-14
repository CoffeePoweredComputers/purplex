<template>
  <VAceEditor
      @init="editorInit"
      :lang="lang"
      :theme="theme"
      :mode="mode"
      :style="{ height: height, width: width }"
      :value="value"
      :options="{ readOnly: readOnly }"
      @update:value="handleInput"
      />
</template>

<script lang="ts">
  import { defineComponent, ref, watch } from 'vue';
  import { VAceEditor } from 'vue3-ace-editor';
  import workerJsonUrl from 'ace-builds/src-noconflict/worker-json?url'
  import 'ace-builds/src-noconflict/mode-python';
  import 'ace-builds/src-noconflict/theme-clouds_midnight';
  import 'ace-builds/src-noconflict/theme-chrome';
  import 'ace-builds/src-noconflict/theme-monokai';
  import 'ace-builds/src-noconflict/theme-github';
  import 'ace-builds/src-noconflict/theme-solarized_dark';
  import 'ace-builds/src-noconflict/theme-solarized_light';
  import 'ace-builds/src-noconflict/theme-dracula';
  import 'ace-builds/src-noconflict/theme-tomorrow_night';

  interface HintMarker {
    startLine: number;
    endLine: number;
    startColumn?: number;
    endColumn?: number;
    className: string;
    type: 'fullLine' | 'text';
    tooltipText?: string;
    hintType: string;
  }

  export default defineComponent({
    name: "Editor",
    components: {
      VAceEditor,
    },
    emits: ['update:value'],
    props: {
      lang: {
        type: String,
        default: 'python',
      },
      theme: {
        type: String,
        default: 'clouds_midnight',
      },
      mode: {
        type: String,
        default: 'python',
      },
      height: {
        type: String,
        default: '300px',
      },
      width: {
        type: String,
        default: '500px',
      },
      showGutter: {
        type: Boolean,
        default: true,
      },
      characterLimit: {
        type: Number,
        default: null,
      },
      hintMarkers: {
        type: Array as () => HintMarker[],
        default: () => [],
      },
      value: {
        type: String,
        default: '',
      },
      readOnly: {
        type: Boolean,
        default: false,
      },
    },
    setup(props, { emit, expose }) {
      const editor = ref(null);
      const activeMarkerIds = ref(new Set());
      
      /* Initialize the editor */
      const editorInit = (editorInstance: any) => {
        editor.value = editorInstance;
        editorInstance.setOptions({
          showGutter: props.showGutter,
          maxLines: props.characterLimit,
          readOnly: props.readOnly,
        });
        
        if (props.hintMarkers.length > 0) {
          setHintMarkers(props.hintMarkers);
        }
      };
      
      /* Handle input changes */
      const handleInput = (value: string) => {
        // ACE editor should only send strings - if it's not a string, something is wrong
        if (typeof value !== 'string') {
          console.error('ACE editor sent non-string value:', value);
          return;
        }
        
        emit('update:value', value);
      };

      /* Setters and getters for the values */
      const setValue = (value: string) => {
        if (editor.value) {
          editor.value.setOptions({
            value: value,
          });
        }
      };

      const getValue = () => {
        return editor.value ? editor.value.getValue() : '';
      };

      /* Setter for hint markers */
      const setHintMarkers = (markers: HintMarker[]) => {
        if (!editor.value) {
          console.log('setHintMarkers: Editor not available');
          return;
        }
        
        console.log('setHintMarkers called with:', markers);
        
        // Clear existing hint markers
        clearHintMarkers();
        
        markers.forEach((marker, index) => {
          console.log(`Adding marker ${index}:`, marker);
          
          const Range = ace.require('ace/range').Range;
          
          // Create range based on marker type
          let range;
          if (marker.type === 'fullLine') {
            range = new Range(
              marker.startLine, 
              0, 
              marker.endLine, 
              Number.MAX_SAFE_INTEGER
            );
          } else {
            range = new Range(
              marker.startLine,
              marker.startColumn || 0,
              marker.endLine,
              marker.endColumn || Number.MAX_SAFE_INTEGER
            );
          }
          
          console.log(`Created range for marker ${index}:`, {
            startLine: marker.startLine,
            endLine: marker.endLine,
            className: marker.className
          });
          
          // Add marker to session
          const markerId = editor.value.session.addMarker(
            range,
            marker.className,
            marker.type === 'fullLine' ? 'fullLine' : 'text'
          );
          
          console.log(`Added marker ${index} with ID:`, markerId);
          
          // Track marker ID for cleanup
          activeMarkerIds.value.add(markerId);
          
          // Add tooltip if specified
          if (marker.tooltipText) {
            // Add click handler for tooltips
            editor.value.on('click', (e: any) => {
              const position = e.getDocumentPosition();
              if (position.row >= marker.startLine && position.row <= marker.endLine) {
                // Show tooltip (could be implemented with a tooltip library)
                console.log('Tooltip:', marker.tooltipText);
              }
            });
          }
        });
        
        console.log(`Total active markers: ${activeMarkerIds.value.size}`);
      };

      /* Clear all hint markers */
      const clearHintMarkers = () => {
        if (!editor.value) return;
        
        // Remove all tracked markers
        activeMarkerIds.value.forEach(markerId => {
          editor.value.session.removeMarker(markerId);
        });
        
        // Clear the tracking set
        activeMarkerIds.value.clear();
      };

      /* Set new code content while preserving cursor */
      const setCode = (newCode: string) => {
        if (!editor.value) return;
        
        const cursorPosition = editor.value.getCursorPosition();
        editor.value.setValue(newCode);
        editor.value.moveCursorToPosition(cursorPosition);
      };

      /* Get current cursor position */
      const getCursorPosition = () => {
        if (!editor.value) return { row: 0, column: 0 };
        return editor.value.getCursorPosition();
      };

      /* Move cursor to specific position */
      const moveCursorToPosition = (position: { row: number; column: number }) => {
        if (!editor.value) return;
        editor.value.moveCursorToPosition(position);
      };

      /* Watch for hintMarkers prop changes */
      watch(() => props.hintMarkers, (newMarkers) => {
        if (editor.value && newMarkers) {
          console.log('Editor: hintMarkers prop changed:', newMarkers);
          setHintMarkers(newMarkers);
        }
      }, { deep: true });
      
      // Expose methods for external access
      expose({
        setHintMarkers,
        clearHintMarkers,
        setCode,
        getValue,
        getCursorPosition,
        moveCursorToPosition
      });

      return {
        editor,
        editorInit,
        setValue,
        getValue,
        handleInput,
        setHintMarkers,
        clearHintMarkers,
        setCode,
        getCursorPosition,
        moveCursorToPosition
      };
    }
  });
</script>

<style scoped>
  /* Editor wrapper styling to match design system */
  :deep(.ace_editor) {
    border-radius: var(--radius-lg);
    border: 2px solid var(--color-bg-input);
    box-shadow: var(--shadow-md);
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: var(--font-size-sm);
    transition: var(--transition-base);
  }

  :deep(.ace_editor:hover) {
    border-color: var(--color-primary-gradient-start);
    box-shadow: var(--shadow-lg);
  }

  /* Gutter styling */
  :deep(.ace_gutter) {
    background: var(--color-bg-hover);
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
    background: var(--color-bg-hover);
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
    background: rgba(102, 126, 234, 0.3);
  }

  /* Active line highlighting */
  :deep(.ace_active-line) {
    background: rgba(102, 126, 234, 0.1);
  }

  /* Cursor styling */
  :deep(.ace_cursor) {
    color: var(--color-primary-gradient-start);
    border-left: 2px solid var(--color-primary-gradient-start);
  }

  /* Bracket matching */
  :deep(.ace_bracket) {
    margin: -1px -1px 0 -1px;
    border: 1px solid var(--color-primary-gradient-start);
    background: rgba(102, 126, 234, 0.2);
  }

  /* Search highlights */
  :deep(.ace_selected-word) {
    border: 1px solid var(--color-primary-gradient-start);
    background: rgba(102, 126, 234, 0.2);
  }

  /* Annotations/Markers */
  :deep(.ace_marker-layer .ace_info) {
    background: var(--color-info-bg);
    border-left: 3px solid var(--color-info);
  }

  :deep(.ace_marker-layer .ace_warning) {
    background: var(--color-warning-bg);
    border-left: 3px solid var(--color-warning);
  }

  :deep(.ace_marker-layer .ace_error) {
    background: var(--color-error-bg);
    border-left: 3px solid var(--color-error);
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
  :deep(.variable-fade-highlight) {
    background: rgba(102, 126, 234, 0.2);
    border-bottom: 2px solid #667eea;
    transition: all 0.2s ease;
  }

  :deep(.variable-fade-highlight:hover) {
    background: rgba(102, 126, 234, 0.3);
  }

  :deep(.subgoal-highlight) {
    background: rgba(76, 175, 80, 0.15);
    border-left: 4px solid #4caf50;
    transition: all 0.2s ease;
  }

  :deep(.subgoal-0) {
    border-left-color: #4caf50;
  }

  :deep(.subgoal-1) {
    border-left-color: #2196f3;
  }

  :deep(.subgoal-2) {
    border-left-color: #ff9800;
  }

  :deep(.subgoal-3) {
    border-left-color: #9c27b0;
  }

  :deep(.subgoal-current) {
    background: rgba(255, 193, 7, 0.2);
    animation: pulse-subgoal 2s infinite;
  }

  :deep(.subgoal-completed) {
    background: rgba(76, 175, 80, 0.1);
    opacity: 0.7;
  }

  @keyframes pulse-subgoal {
    0% {
      background: rgba(255, 193, 7, 0.2);
    }
    50% {
      background: rgba(255, 193, 7, 0.3);
    }
    100% {
      background: rgba(255, 193, 7, 0.2);
    }
  }

  :deep(.input-suggestion) {
    background: rgba(255, 193, 7, 0.1);
    border-right: 3px solid #ffc107;
    font-style: italic;
    position: relative;
  }

  :deep(.input-suggestion)::after {
    content: "💡";
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0.6;
  }

  :deep(.suggestion-instructions) {
    background: rgba(33, 150, 243, 0.1);
    border-right: 3px solid #2196f3;
  }

  :deep(.suggestion-test_case) {
    background: rgba(255, 193, 7, 0.1);
    border-right: 3px solid #ffc107;
  }

  /* Annotation styles for hint system */
  :deep(.ace_gutter .subgoal-annotation) {
    background: rgba(76, 175, 80, 0.1);
    border-radius: 3px;
    padding: 2px 4px;
    margin: 1px 0;
  }
</style>