<template>
  <VAceEditor
      @init="editorInit"
      :lang="lang"
      theme="clouds_midnight"
      mode="python"
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
  /* make the virdis color pallete */
  .ace-virdis .ace_gutter {
    background: var(--color-bg-table);
    color: var(--color-text-secondary);
  }

  .ace-virdis .ace_gutter-cell {
    color: var(--color-text-secondary);
  }
</style>