<template>
  <VAceEditor
    :lang="lang"
    :theme="theme"
    :mode="mode"
    :style="{ height: height, width: width }"
    :value="value"
    :options="{ readOnly: readOnly }"
    @init="editorInit"
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
  import { log } from '@/utils/logger';

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
    props: {
      lang: {
        type: String,
        default: 'python',
      },
      theme: {
        type: String,
        default: 'tomorrow_night',
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
    emits: ['update:value'],
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
          highlightActiveLine: false,
          highlightGutterLine: false,
          showPrintMargin: false,
          wrap: true,
          indentedSoftWrap: false, // This should fix the wrapping indentation issue
        });
        
        // Disable cursor visibility when read-only
        if (props.readOnly) {
          editorInstance.renderer.$cursorLayer.element.style.display = 'none';
          editorInstance.setOption('showCursor', false);
          // Remove focus outline
          editorInstance.renderer.container.style.pointerEvents = 'none';
          editorInstance.renderer.container.style.userSelect = 'text';
        }
        
        // Override ACE's comment token rendering to remove backgrounds
        const originalTokenizer = editorInstance.session.getMode().getTokenizer();
        if (originalTokenizer && originalTokenizer.getLineTokens) {
          const originalGetLineTokens = originalTokenizer.getLineTokens.bind(originalTokenizer);
          originalTokenizer.getLineTokens = function(line: string, state: any) {
            const tokens = originalGetLineTokens(line, state);
            // Remove background from comment tokens
            if (tokens && tokens.tokens) {
              tokens.tokens.forEach((token: any) => {
                if (token.type && token.type.includes('comment')) {
                  // Force transparent background for comments
                  token.type = token.type + ' ace-comment-transparent';
                }
              });
            }
            return tokens;
          };
        }
        
        // Ensure marker layer has proper z-index
        if (editorInstance.renderer.$markerBack) {
          editorInstance.renderer.$markerBack.element.style.zIndex = '3';
        }
        
        if (props.hintMarkers.length > 0) {
          setHintMarkers(props.hintMarkers);
        }
      };
      
      /* Handle input changes */
      const handleInput = (value: string) => {
        // ACE editor should only send strings - if it's not a string, something is wrong
        if (typeof value !== 'string') {
          log.error('ACE editor sent non-string value', { value, type: typeof value });
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
          log.debug('setHintMarkers: Editor not available');
          return;
        }
        
        log.debug('setHintMarkers called with', { markers });
        
        // Clear existing hint markers
        clearHintMarkers();
        
        markers.forEach((marker, index) => {
          log.debug(`Adding marker ${index}`, { marker });
          
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
          
          log.debug(`Created range for marker ${index}`, {
            startLine: marker.startLine,
            endLine: marker.endLine,
            className: marker.className,
            type: marker.type
          });
          
          // Add marker to session
          const markerId = editor.value.session.addMarker(
            range,
            marker.className,
            marker.type === 'fullLine' ? 'fullLine' : 'text'
          );
          
          log.debug(`Added marker ${index} with ID ${markerId}`, { className: marker.className });
          
          // Track marker ID for cleanup
          activeMarkerIds.value.add(markerId);
          
          // For comment markers, ensure the line has proper styling
          if (marker.className.includes('subgoal-comment')) {
            // Force a re-render of the line to ensure styles are applied
            editor.value.renderer.updateLines(marker.startLine, marker.endLine);
          }
          
          // Add tooltip if specified
          if (marker.tooltipText) {
            // Add click handler for tooltips
            editor.value.on('click', (e: any) => {
              const position = e.getDocumentPosition();
              if (position.row >= marker.startLine && position.row <= marker.endLine) {
                // Show tooltip (could be implemented with a tooltip library)
                log.debug('Tooltip', { tooltipText: marker.tooltipText });
              }
            });
          }
        });
        
        log.debug('Total active markers', { count: activeMarkerIds.value.size });
      };

      /* Clear all hint markers */
      const clearHintMarkers = () => {
        if (!editor.value) {return;}
        
        // Remove all tracked markers
        activeMarkerIds.value.forEach(markerId => {
          editor.value.session.removeMarker(markerId);
        });
        
        // Clear the tracking set
        activeMarkerIds.value.clear();
        
        log.debug('Cleared all hint markers');
      };

      /* Set new code content while preserving cursor */
      const setCode = (newCode: string) => {
        if (!editor.value) {return;}
        
        const cursorPosition = editor.value.getCursorPosition();
        editor.value.setValue(newCode);
        editor.value.moveCursorToPosition(cursorPosition);
      };

      /* Get current cursor position */
      const getCursorPosition = () => {
        if (!editor.value) {return { row: 0, column: 0 };}
        return editor.value.getCursorPosition();
      };

      /* Move cursor to specific position */
      const moveCursorToPosition = (position: { row: number; column: number }) => {
        if (!editor.value) {return;}
        editor.value.moveCursorToPosition(position);
      };


      /* Watch for hintMarkers prop changes */
      watch(() => props.hintMarkers, (newMarkers) => {
        if (editor.value && newMarkers) {
          log.debug('Editor: hintMarkers prop changed', { newMarkers });
          setHintMarkers(newMarkers);
        }
      }, { deep: true });
      
      // Expose methods for external access
      expose({
        editor,
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

  /* Fix text wrapping - ensure wrapped lines maintain proper indentation */
  :deep(.ace_text-layer .ace_line) {
    white-space: pre-wrap;
    word-wrap: break-word;
    text-indent: 0;
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
    background: rgba(128, 0, 128, 0.3) !important;
    color: var(--color-text-primary) !important;
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
  /* Variable fade has no visual styling - just transforms variable names */
  /* Subgoal highlighting styles moved to global styles block below */
  
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
  
  :deep(.ace_editor.ace_read-only .ace_cursor-layer) {
    display: none !important;
  }
  
  :deep(.ace_editor.ace_read-only .ace_content) {
    cursor: text !important;
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

  :deep(.suggested-trace) {
    background: rgba(255, 193, 7, 0.1);
    border-right: 3px solid #ffc107;
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

<!-- Global styles for ACE markers (can't be scoped) -->
<style>
/* ACE Subgoal Highlighting - Harmonized with clouds_midnight theme */

/* Force comment tokens to have transparent backgrounds when on highlighted lines */
.ace-clouds-midnight .ace_comment {
  background: transparent !important;
}

/* Special class for transparent comments */
.ace-comment-transparent {
  background: transparent !important;
}

/* Ensure marker layer is visible above text layer for highlighted lines */
.ace_marker-layer {
  pointer-events: none;
}

/* Make sure our highlights show through properly */
.ace_line {
  position: relative;
}

/* Alternative approach using attribute selectors if line has markers */
.ace_text-layer .ace_line:has(+ .ace_marker-layer .subgoal-comment-0) .ace_comment,
.ace_text-layer .ace_line:has(+ .ace_marker-layer .subgoal-comment-1) .ace_comment,
.ace_text-layer .ace_line:has(+ .ace_marker-layer .subgoal-comment-2) .ace_comment,
.ace_text-layer .ace_line:has(+ .ace_marker-layer .subgoal-comment-3) .ace_comment,
.ace_text-layer .ace_line:has(+ .ace_marker-layer .subgoal-comment-4) .ace_comment,
.ace_text-layer .ace_line:has(+ .ace_marker-layer .subgoal-comment-5) .ace_comment {
  background: transparent !important;
}

/* Additional approach: Use mix-blend-mode to ensure visibility */
.ace_marker-layer .subgoal-comment-0,
.ace_marker-layer .subgoal-comment-1,
.ace_marker-layer .subgoal-comment-2,
.ace_marker-layer .subgoal-comment-3,
.ace_marker-layer .subgoal-comment-4,
.ace_marker-layer .subgoal-comment-5 {
  mix-blend-mode: multiply;
}

/* Fallback: Apply highlighting to the entire line container */
.ace_line_group:has(.ace_line .ace_comment:only-child) {
  position: relative;
}

/* Use data attributes on the editor to mark highlighted lines if needed */
.ace_editor[data-highlighted-lines*="comment"] .ace_text-layer .ace_line_group {
  position: relative;
  z-index: 1;
}

/* Direct line styling approach for better compatibility */
.ace_gutter-cell.subgoal-line-0 ~ .ace_line,
.ace_line.subgoal-line-0 {
  background: rgba(57, 148, 106, 0.15) !important;
  position: relative;
}

.ace_gutter-cell.subgoal-line-0 ~ .ace_line::before,
.ace_line.subgoal-line-0::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  background: #39946A;
}

/* Comment Lines - Slightly more prominent backgrounds */
.ace_marker-layer .subgoal-comment-0 {
  background: rgba(57, 148, 106, 0.15) !important;  /* Muted Teal */
  border-left: 5px solid #39946A !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
  z-index: 4;
}

.ace_marker-layer .subgoal-comment-1 {
  background: rgba(93, 144, 205, 0.15) !important;  /* Soft Blue */
  border-left: 5px solid #5D90CD !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
  z-index: 4;
}

.ace_marker-layer .subgoal-comment-2 {
  background: rgba(146, 124, 93, 0.15) !important;  /* Warm Brown */
  border-left: 5px solid #927C5D !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
  z-index: 4;
}

.ace_marker-layer .subgoal-comment-3 {
  background: rgba(161, 101, 172, 0.15) !important;  /* Muted Purple */
  border-left: 5px solid #A165AC !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
  z-index: 4;
}

.ace_marker-layer .subgoal-comment-4 {
  background: rgba(231, 124, 124, 0.15) !important;  /* Dark Coral */
  border-left: 5px solid #E77C7C !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
  z-index: 4;
}

.ace_marker-layer .subgoal-comment-5 {
  background: rgba(181, 165, 114, 0.15) !important;  /* Soft Yellow */
  border-left: 5px solid #B5A572 !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
  z-index: 4;
}

/* Code Lines - Subtle backgrounds */
.ace_marker-layer .subgoal-highlight.subgoal-0 {
  background: rgba(57, 148, 106, 0.08) !important;  /* Muted Teal */
  border-left: 5px solid #39946A !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
}

.ace_marker-layer .subgoal-highlight.subgoal-1 {
  background: rgba(93, 144, 205, 0.08) !important;  /* Soft Blue */
  border-left: 5px solid #5D90CD !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
}

.ace_marker-layer .subgoal-highlight.subgoal-2 {
  background: rgba(146, 124, 93, 0.08) !important;  /* Warm Brown */
  border-left: 5px solid #927C5D !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
}

.ace_marker-layer .subgoal-highlight.subgoal-3 {
  background: rgba(161, 101, 172, 0.08) !important;  /* Muted Purple */
  border-left: 5px solid #A165AC !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
}

.ace_marker-layer .subgoal-highlight.subgoal-4 {
  background: rgba(231, 124, 124, 0.08) !important;  /* Dark Coral */
  border-left: 5px solid #E77C7C !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
}

.ace_marker-layer .subgoal-highlight.subgoal-5 {
  background: rgba(181, 165, 114, 0.08) !important;  /* Soft Yellow */
  border-left: 5px solid #B5A572 !important;
  position: absolute;
  width: 100% !important;
  left: 0 !important;
}
</style>