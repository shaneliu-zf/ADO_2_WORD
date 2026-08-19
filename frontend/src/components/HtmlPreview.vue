<template>
  <iframe
    :srcdoc="html"
    sandbox="allow-same-origin"
    class="html-preview-frame"
  />
</template>

<script setup lang="ts">
defineProps<{
  html: string
}>()
</script>

<style scoped>
.html-preview-frame {
  width: 100%;
  height: 600px;
  border: none;
  border-radius: 4px;
  background: #fff;
}
</style>
