<template>
  <VAceEditor
      @init="editorInit"
      :lang="lang"
      :theme="theme"
      :mode="mode"
      :style="{ height: height, width: width }"
      :value="value"
      :options="{ readOnly: readOnly }"
      @input="handleInput"
      />
</template>

<script lang="ts">
  import { defineComponent, ref } from 'vue';
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

  interface Marker {
    start_line: number;
    end_line: number;
    explanation_portion: string;
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
      highlightMarkers: {
        type: Array as () => Marker[],
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
    setup(props, { emit }) {
      const editor = ref(null);
      
      /* Initialize the editor */
      const editorInit = (editorInstance: any) => {
        editor.value = editorInstance;
        editorInstance.setOptions({
          showGutter: props.showGutter,
          maxLines: props.characterLimit,
          readOnly: props.readOnly,
        });
        
        if (props.highlightMarkers.length > 0) {
          setHighlightMarkers(props.highlightMarkers);
        }
      };
      
      /* Handle input changes */
      const handleInput = (value: string) => {
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

      /* Setter for highlight markers */
      const setHighlightMarkers = (markers: Marker[]) => {
        if (!editor.value) return;
        
        markers.forEach((marker, index) => {
          const Range = ace.require('ace/range').Range;
          const color = getVirdisColor(index);
          const css = `.myMarker${index} { background: ${color}; position: absolute; z-index: 20; }`;
          const style = document.createElement('style');
          style.appendChild(document.createTextNode(css));
          document.head.appendChild(style);
          editor.value.session.addMarker(
            new Range(marker.start_line - 1, 0, marker.end_line - 1, 2), 
            `myMarker${index}`, 
            'fullLine'
          );
        });

        /* add the message to the highlight markers */
        editor.value.session.setAnnotations(
          markers.map((marker) => ({
            row: marker.start_line - 1,
            column: 0,
            text: marker.explanation_portion,
            type: 'info',
          }))
        );
      };

      /* utility function to return virdis color pallete for setting the background for the markers */
      const getVirdisColor = (index: number) => {
        const colors = [
          '#44015482',
          '#48287882',
          '#3E498982',
          '#31688E82',
          '#26828E82',
          '#1F9E8982',
          '#35B77982',
          '#6DCD5982',
          '#B4DE2C82',
          '#FDE72582',
        ];
        return colors[index % colors.length];
      };
      
      return {
        editor,
        editorInit,
        setValue,
        getValue,
        setHighlightMarkers,
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
</style>