<template>
  <div>
    <!-- make a template for a code language map -->
    <Editor 
      :value="code"
      height="150px"
      width="500px"
      :highlight-markers="comprehensionResults"
    />
  </div>
</template>

<script lang="ts">

    import { defineComponent, PropType } from 'vue'
    import Editor from './Editor.vue'

    export default defineComponent({
        components: {Editor},
        props: {
            code: {
                type: String as PropType<string>,
                default: ''
            },
            comprehensionResults: {
                type: Array as PropType<any[]>,
                default: () => []
            }
        }
    });

</script>
