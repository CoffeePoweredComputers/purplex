<template>
  <VAceEditor
      @init="editorInit"
      :lang="lang"
      theme="clouds_midnight"
      mode="python"
      :style="{ height: height, width: width }"
      />
</template>

<script>

  import { VAceEditor } from 'vue3-ace-editor';
  import workerJsonUrl from 'ace-builds/src-noconflict/worker-json?url'
  import 'ace-builds/src-noconflict/mode-python';
  import 'ace-builds/src-noconflict/theme-clouds_midnight';

  export default {
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
        type: Array,
        default: () => [],
      },
    },
    methods: {

      /* Initialize the editor */
      editorInit(editor) {
        this.editor = editor;
        editor.setOptions({
          showGutter: this.showGutter,
          maxLines: this.characterLimit,
          value: this.value,
        });
        if(this.highlightMarkers.length > 0) {
          this.setHighlightMarkers(this.highlightMarkers);
        }
      },

      /* Setters and getters for the values */
      setValue(value) {
        editor.setOptions({
          value: value,
        });
      },

      getValue() {
        return this.editor.getValue();
      },

      /* Setter for hihgliht markers */
      setHighlightMarkers(markers) {
        markers.forEach((marker) => {
          const Range = ace.require('ace/range').Range;
          const markerIndex = markers.indexOf(marker);
          const color = this.getVirdisColor(markerIndex);
          const css = `.myMarker${markerIndex} { background: ${color}; position: absolute; z-index: 20; }`;
          const style = document.createElement('style');
          style.appendChild(document.createTextNode(css));
          document.head.appendChild(style);
          this.editor.session.addMarker(new Range(marker.start_line - 1, 0, marker.end_line - 1, 2), `myMarker${markerIndex}`, 'fullLine');
        });

        /* add the message to the highlight markers */
        this.editor.session.setAnnotations(
          markers.map((marker) => ({
            row: marker.start_line - 1,
            column: 0,
            text: marker.explanation_portion,
            type: 'info',
          }))
        );
      },

      /* utility function to return virdis color pallete for setting the background for the markers */
      getVirdisColor(index) {
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
      }

    },
    data() {
      return {
        value: this.value,
      };
    },
  }

</script>

<style scoped>

  /* make the virdis color pallete */
  .ace-virdis .ace_gutter {
    background: #272822;
    color: #F8F8F2;
  }

  .ace-virdis .ace_gutter-cell {
    color: #F8F8F2;
  }
</style>
