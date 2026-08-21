<template>
  <iframe
    :srcdoc="srcdoc"
    sandbox="allow-popups allow-popups-to-escape-sandbox"
    referrerpolicy="no-referrer"
    class="html-preview-frame"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { prepareAdoHtml } from '@/utils/adoHtml'

const props = defineProps<{
  html: string
}>()

const srcdoc = computed(() => prepareAdoHtml(props.html || ''))
</script>

<style scoped>
.html-preview-frame {
  width: 100%;
  height: 100%;
  border: none;
  background: #fff;
  display: block;
}
</style>
