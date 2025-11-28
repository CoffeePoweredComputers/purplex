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
  import 'ace-builds/src-noconflict/mode-python';
  import 'ace-builds/src-noconflict/theme-clouds_midnight';
  import 'ace-builds/src-noconflict/theme-chrome';
  import 'ace-builds/src-noconflict/theme-monokai';
  import 'ace-builds/src-noconflict/theme-github';
  import 'ace-builds/src-noconflict/theme-solarized_dark';
  import 'ace-builds/src-noconflict/theme-solarized_light';
  import 'ace-builds/src-noconflict/theme-dracula';
  import 'ace-builds/src-noconflict/theme-tomorrow_night';

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
      value: {
        type: String,
        default: '',
      },
      readOnly: {
        type: Boolean,
        default: false,
      },
      tabTargetId: {
        type: String,
        default: null,
      },
    },
    emits: ['update:value'],
    setup(props, { emit, expose }) {
      const editor = ref(null);
      
      /* Simple editor initialization */
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
          indentedSoftWrap: false
        });

        // Make editor container tabbable
        editorInstance.container.setAttribute('tabindex', '0');

        // Disable cursor visibility when read-only
        if (props.readOnly) {
          editorInstance.renderer.$cursorLayer.element.style.display = 'none';
          editorInstance.setOption('showCursor', false);
          editorInstance.renderer.container.style.pointerEvents = 'none';
          editorInstance.renderer.container.style.userSelect = 'text';
        }

        // CRITICAL ACCESSIBILITY FIX: Override Tab key behavior to allow tabbing out
        // By default, ACE captures Tab for indentation, creating a keyboard trap

        // Helper function to get all focusable elements (excluding ACE editor internals)
        const getFocusableElements = () => {
          return Array.from(document.querySelectorAll(
            'button:not([disabled]):not([tabindex="-1"]), ' +
            '[href]:not([tabindex="-1"]), ' +
            'input:not([disabled]):not([tabindex="-1"]), ' +
            'select:not([disabled]):not([tabindex="-1"]), ' +
            'textarea:not([disabled]):not([tabindex="-1"]), ' +
            '[tabindex]:not([tabindex="-1"])'
          )).filter((el: any) => {
            // Filter out hidden elements and ACE editor internal elements
            const isVisible = el.offsetParent !== null &&
                   getComputedStyle(el).visibility !== 'hidden' &&
                   getComputedStyle(el).display !== 'none';

            // Exclude elements inside ACE editor (except the container itself)
            const isAceInternal = el.classList.contains('ace_text-input') ||
                                 el.classList.contains('ace_content');

            return isVisible && !isAceInternal;
          });
        };

        editorInstance.commands.addCommand({
          name: 'overrideTab',
          bindKey: { win: 'Tab', mac: 'Tab' },
          exec: function(editor: any) {
            // Temporarily remove tabindex to prevent re-focusing
            const container = editor.container;
            const originalTabIndex = container.getAttribute('tabindex');
            container.setAttribute('tabindex', '-1');

            editor.blur();

            setTimeout(() => {
              // Restore tabindex
              container.setAttribute('tabindex', originalTabIndex);

              const focusableElements = getFocusableElements();
              const currentIndex = focusableElements.indexOf(container);

              if (currentIndex !== -1 && currentIndex < focusableElements.length - 1) {
                const nextElement = focusableElements[currentIndex + 1] as HTMLElement;
                nextElement.focus();
              } else {
                // Use custom tab target if provided, otherwise fall back to submit button
                const targetId = props.tabTargetId || 'submitButton';
                const targetElement = document.getElementById(targetId);
                if (targetElement) {
                  // If target is a wrapper with an editor inside, focus the editor
                  const innerEditor = targetElement.querySelector('.ace_text-input');
                  if (innerEditor) {
                    (innerEditor as HTMLElement).focus();
                  } else {
                    targetElement.focus();
                  }
                }
              }
            }, 10);
          }
        });

        // Shift+Tab to move focus backward
        editorInstance.commands.addCommand({
          name: 'overrideShiftTab',
          bindKey: { win: 'Shift-Tab', mac: 'Shift-Tab' },
          exec: function(editor: any) {
            // Temporarily remove tabindex to prevent re-focusing
            const container = editor.container;
            const originalTabIndex = container.getAttribute('tabindex');
            container.setAttribute('tabindex', '-1');

            editor.blur();

            setTimeout(() => {
              // Restore tabindex
              container.setAttribute('tabindex', originalTabIndex);

              const focusableElements = getFocusableElements();
              const currentIndex = focusableElements.indexOf(container);

              if (currentIndex > 0) {
                const prevElement = focusableElements[currentIndex - 1] as HTMLElement;
                prevElement.focus();
              }
            }, 10);
          }
        });

        // Keep Escape key handler as alternative exit method
        editorInstance.commands.addCommand({
          name: 'exitEditor',
          bindKey: { win: 'Esc', mac: 'Esc' },
          exec: function(editor: any) {
            editor.blur();

            // Try to focus submit button after escaping
            setTimeout(() => {
              const submitBtn = document.getElementById('submitButton');
              if (submitBtn) {
                submitBtn.focus();
              }
            }, 10);
          }
        });
      };
      
      /* Handle input changes */
      const handleInput = (value: string) => {
        emit('update:value', value);
      };



      /* Simple value update - just replace the entire content */
      watch(() => props.value, (newValue) => {
        if (editor.value && newValue !== undefined) {
          const currentValue = editor.value.getValue();
          if (currentValue !== newValue) {
            // Simple full replacement
            editor.value.setValue(newValue, 1);
          }
        }
      });
      
      // Expose editor instance if needed
      expose({
        editor
      });

      return {
        editor,
        editorInit,
        handleInput
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

