<template>
  <iframe
    :srcdoc="srcdoc"
    sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
    referrerpolicy="no-referrer"
    class="html-preview-frame"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  html: string
}>()

function openLinksInNewTab(html: string): string {
  if (!html) return html
  if (typeof DOMParser === 'undefined') {
    return html.replace(/<a\b(?![^>]*\btarget=)/gi, '<a target="_blank" rel="noopener noreferrer" ')
  }
  const doc = new DOMParser().parseFromString(html, 'text/html')
  for (const anchor of doc.querySelectorAll('a[href]')) {
    anchor.setAttribute('target', '_blank')
    anchor.setAttribute('rel', 'noopener noreferrer')
  }
  if (!doc.querySelector('base')) {
    const base = doc.createElement('base')
    base.setAttribute('target', '_blank')
    ;(doc.head ?? doc.documentElement).prepend(base)
  }
  const style = doc.createElement('style')
  style.textContent =
    'html,body{margin:0;height:100%;overflow:auto}html,body,*{font-family:"Segoe UI","PingFang TC","Noto Sans TC",sans-serif!important}'
  ;(doc.head ?? doc.documentElement).append(style)
  return '<!DOCTYPE html>\n' + doc.documentElement.outerHTML
}

const srcdoc = computed(() => openLinksInNewTab(props.html || ''))
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
