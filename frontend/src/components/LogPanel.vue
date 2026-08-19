<template>
  <div class="log-panel">
    <div class="log-header">
      <span class="log-title">
        <i class="pi pi-terminal" />
        執行 Log
        <ProgressSpinner
          v-if="pipelineStore.isRunning"
          style="width: 1rem; height: 1rem; margin-left: 0.4rem"
          strokeWidth="6"
        />
      </span>
      <button type="button" class="log-close" aria-label="關閉 log" @click="pipelineStore.showLog = false">×</button>
    </div>
    <div ref="logContainer" class="log-body" @scroll="onLogScroll">
      <div v-for="(line, idx) in pipelineStore.logs" :key="idx" class="log-line">
        {{ line }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import ProgressSpinner from 'primevue/progressspinner'
import { usePipelineStore } from '@/stores/pipeline'

const pipelineStore = usePipelineStore()
const logContainer = ref<HTMLElement>()
const stickToBottom = ref(true)

function onLogScroll() {
  const el = logContainer.value
  if (!el) return
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 32
}

watch(
  () => pipelineStore.logs.length,
  async () => {
    await nextTick()
    if (stickToBottom.value && logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  },
)
</script>

<style scoped>
.log-panel {
  flex: 0 0 220px;
  height: 220px;
  min-height: 220px;
  margin-top: auto;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0.75rem;
  background: var(--p-surface-100);
  border-bottom: 1px solid var(--p-surface-200);
  flex-shrink: 0;
}

.log-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 600;
}

.log-close {
  border: 0;
  background: transparent;
  color: var(--p-text-muted-color, #666);
  font-size: 1.25rem;
  line-height: 1;
  padding: 0 0.15rem;
  cursor: pointer;
}

.log-close:hover {
  color: var(--p-text-color, #222);
}

.log-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  padding: 0.5rem 0.75rem;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.78rem;
  line-height: 1.5;
  background: #1e1e2e;
  color: #cdd6f4;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
