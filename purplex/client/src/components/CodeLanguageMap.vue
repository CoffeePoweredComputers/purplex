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

<script>

    import Editor from './Editor.vue'

    export default {
        components: {Editor},
        props: {
            code: {
                type: String,
                default: 0,
            },
            comprehensionResults: {
                type: Array,
                default: () => [],
            },
        },
        data() {
        },
        onMounted() {
        },
        methods: {

        }
    };

</script>
