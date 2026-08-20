<template>
  <iframe
    :srcdoc="srcdoc"
    sandbox="allow-same-origin"
    class="html-preview-frame"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  html: string
}>()

const FONT_STYLE =
  '<style>html,body,*{font-family:"Segoe UI","PingFang TC","Noto Sans TC",sans-serif!important}</style>'

const srcdoc = computed(() => {
  const html = props.html || ''
  if (/<\/head>/i.test(html)) return html.replace(/<\/head>/i, `${FONT_STYLE}</head>`)
  return `${FONT_STYLE}${html}`
})
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
