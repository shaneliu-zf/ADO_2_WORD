<template>
  <div class="pipeline-panel">
    <Button
      label="全流程自動完成"
      icon="pi pi-bolt"
      class="full-run-btn"
      severity="success"
      :loading="pipelineBusy"
      :disabled="isRunning"
      @click="runAll()"
    />

    <div class="progress-wrap">
      <div class="progress" :class="{ busy: pipelineBusy }">
        <div class="progress-bar" :style="progressStyle" />
      </div>
    </div>

    <ol class="steps">
      <li
        v-for="s in STEP_DEFS"
        :key="s.index"
        class="step"
        :class="stepKind(s.index)"
      >
        <span class="step-mark">
          <span v-if="reachedStep >= s.index" class="pi pi-check" />
          <span v-else>{{ s.index }}</span>
        </span>
        <span class="step-body">
          <strong>{{ s.label }}</strong>
          <span class="step-hint">{{ s.hint }}</span>
          <span v-if="pipelineBusy && currentStep === s.index" class="step-progress"><span /></span>
        </span>
      </li>
    </ol>

    <p class="status" :class="{ error: statusKind === 'error', empty: !status }">{{ status }}</p>

    <div class="pane-foot">
      <Button
        label="上一步"
        class="btn-prev"
        outlined
        :disabled="currentStep <= 1 || isRunning"
        @click="pipelineStore.prevStep()"
      />
      <Button
        :label="executeLabel"
        icon="pi pi-play"
        class="btn-run"
        severity="success"
        :loading="pipelineBusy"
        :disabled="isRunning"
        @click="runCurrent()"
      />
    </div>

    <Button
      v-if="isRunning"
      label="中止執行"
      icon="pi pi-stop-circle"
      severity="danger"
      class="abort-btn"
      size="small"
      @click="pipelineStore.abortScript()"
    />

    <div class="log-toggle">
      <Checkbox v-model="showLog" inputId="show-log" binary />
      <label for="show-log">顯示 log</label>
    </div>

    <Dialog v-model:visible="confirmVisible" modal :header="confirmTitle" :style="{ width: '28rem' }">
      <p class="confirm-msg">{{ confirmMessage }}</p>
      <template #footer>
        <Button :label="confirmSkipLabel" outlined @click="confirmSkip" />
        <Button :label="confirmRedoLabel" severity="success" @click="confirmRedo" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import { STEP_DEFS, usePipelineStore } from '@/stores/pipeline'
import { useItemsStore } from '@/stores/items'
import { storeToRefs } from 'pinia'

const pipelineStore = usePipelineStore()
const itemsStore = useItemsStore()
const toast = useToast()
const { currentStep, reachedStep, isRunning, runningStep, showLog, status, statusKind } = storeToRefs(pipelineStore)

const pipelineBusy = computed(() => isRunning.value && (runningStep.value ?? -1) >= 0)

const confirmVisible = ref(false)
const confirmKind = ref<'fetch' | 'report'>('fetch')
const pending = ref<{ script: string; index: number; ids: number[] } | null>(null)

const confirmTitle = computed(() => (confirmKind.value === 'fetch' ? '下載資料' : '產生報告'))
const confirmMessage = computed(() =>
  confirmKind.value === 'fetch'
    ? '是否重新下載已經下載完成的項目'
    : '是否重新整理已整理的項目',
)
const confirmRedoLabel = computed(() => (confirmKind.value === 'fetch' ? '重新下載' : '重新整理'))
const confirmSkipLabel = '略過'

const executeLabel = computed(() => {
  if (isRunning.value && pipelineBusy.value) return '處理中…'
  const step = STEP_DEFS.find(s => s.index === currentStep.value)
  return step ? `執行：${step.label}` : '執行'
})

const progressStyle = computed(() => {
  if (pipelineBusy.value) return {}
  return { width: `${(Math.min(reachedStep.value, 4) / 4) * 100}%` }
})

function stepKind(index: number): string {
  const kinds: string[] = []
  if (index < currentStep.value) kinds.push('done')
  else if (index === currentStep.value) kinds.push('current')
  else kinds.push('pending')
  if (reachedStep.value >= index) kinds.push('reached')
  if (pipelineBusy.value && index === currentStep.value) kinds.push('busy')
  return kinds.join(' ')
}

function resolveIds(): number[] {
  return [...itemsStore.selectedIds]
}

function selectedWithFlag(flag: 'hasHtml' | 'hasJson'): number[] {
  const selected = new Set(resolveIds())
  return itemsStore.items.filter(item => selected.has(item.id) && item[flag]).map(item => item.id)
}

function startRun(script: string, ids: number[], index: number, workingIds?: number[]) {
  pipelineStore.runScript(script, ids, index, workingIds)
}

function runCurrent() {
  const step = STEP_DEFS.find(s => s.index === currentStep.value)
  if (!step) return
  const ids = resolveIds()
  if (ids.length === 0) {
    toast.add({
      severity: 'warn',
      summary: '尚未勾選',
      detail: '請先在左邊勾選要處理的 ADO。',
      life: 3000,
    })
    pipelineStore.setStatus('請先在左邊勾選要處理的 ADO。', 'error')
    return
  }

  if (step.index === 1 && selectedWithFlag('hasHtml').length) {
    pending.value = { script: step.script, index: step.index, ids }
    confirmKind.value = 'fetch'
    confirmVisible.value = true
    return
  }
  if (step.index === 3 && selectedWithFlag('hasJson').length) {
    pending.value = { script: step.script, index: step.index, ids }
    confirmKind.value = 'report'
    confirmVisible.value = true
    return
  }
  startRun(step.script, ids, step.index)
}

function confirmRedo() {
  const job = pending.value
  confirmVisible.value = false
  pending.value = null
  if (!job) return
  startRun(job.script, job.ids, job.index, job.ids)
}

async function confirmSkip() {
  const job = pending.value
  const kind = confirmKind.value
  confirmVisible.value = false
  pending.value = null
  if (!job) return
  const flag = kind === 'fetch' ? 'hasHtml' : 'hasJson'
  const done = new Set(
    itemsStore.items.filter(item => job.ids.includes(item.id) && item[flag]).map(item => item.id),
  )
  const remaining = job.ids.filter(id => !done.has(id))
  if (!remaining.length) {
    await pipelineStore.skipStep(job.index, job.ids)
    return
  }
  startRun(job.script, remaining, job.index, job.ids)
}

function runAll() {
  const ids = resolveIds()
  if (ids.length === 0) {
    toast.add({
      severity: 'warn',
      summary: '尚未勾選',
      detail: '請先在左邊勾選要處理的 ADO。',
      life: 3000,
    })
    pipelineStore.setStatus('請先在左邊勾選要處理的 ADO。', 'error')
    return
  }
  pipelineStore.runScript('main', ids, 0, ids)
}
</script>

<style scoped>
.pipeline-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--p-surface-0, #fff);
  border-left: 1px solid var(--p-surface-200);
  overflow: hidden;
}

.full-run-btn {
  margin: 0.85rem 1rem 0;
  flex-shrink: 0;
}

.progress-wrap {
  padding: 0.85rem 1.15rem 0;
  flex-shrink: 0;
}

.progress {
  height: 8px;
  border-radius: 999px;
  background: #e4eaf0;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  width: 0;
  border-radius: 999px;
  background: var(--p-green-500, #22c55e);
  transition: width 0.25s ease;
}

.progress.busy .progress-bar {
  width: 40% !important;
  animation: progress-slide 1.1s ease-in-out infinite;
}

@keyframes progress-slide {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(280%); }
}

.steps {
  list-style: none;
  margin: 0;
  padding: 0.75rem 1.15rem 0.4rem;
  flex: 1;
  overflow-y: auto;
}

.step {
  display: flex;
  gap: 0.85rem;
  align-items: flex-start;
  padding: 0.75rem 0.9rem;
  border-left: 3px solid #ddd;
  margin-bottom: 0.45rem;
  background: var(--p-surface-0, #fff);
  border-radius: 0 8px 8px 0;
}

.step.done,
.step.reached {
  border-left-color: var(--p-green-500, #22c55e);
}

.step.current {
  border-left-color: var(--p-green-600, #16a34a);
  box-shadow: 0 0 0 1px #bbf7d0 inset;
  background: #f0fdf4;
}

.step.pending {
  opacity: 0.55;
}

.step-mark {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #eef1f4;
  font-size: 13px;
  font-weight: 700;
  flex: 0 0 28px;
}

.step.done .step-mark,
.step.reached .step-mark {
  background: #d3f9d8;
  color: #2b8a3e;
}

.step.current .step-mark {
  background: var(--p-green-500, #22c55e);
  color: #fff;
}

.step-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.step-body strong {
  font-size: 0.92rem;
}

.step-hint {
  display: block;
  color: #666;
  font-size: 12px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.step-progress {
  display: block;
  height: 6px;
  margin-top: 8px;
  border-radius: 999px;
  background: #e4eaf0;
  overflow: hidden;
}

.step-progress > span {
  display: block;
  height: 100%;
  width: 40%;
  border-radius: 999px;
  background: var(--p-green-500, #22c55e);
  animation: progress-slide 1.1s ease-in-out infinite;
}

.status {
  margin: 0 1.15rem 0.5rem;
  min-height: 1.4em;
  font-size: 0.82rem;
  color: var(--p-text-color);
  flex-shrink: 0;
}

.status.empty {
  color: #666;
}

.status.error {
  color: var(--p-red-500, #ef4444);
}

.pane-foot {
  display: flex;
  gap: 0.4rem;
  padding: 0.75rem 1rem 0.6rem;
  border-top: 1px solid var(--p-surface-200);
  background: var(--p-surface-0, #fff);
  flex-shrink: 0;
}

.btn-prev {
  flex: 0 0 auto;
}

.btn-run {
  flex: 1.4;
}

.abort-btn {
  margin: 0 1rem;
  flex-shrink: 0;
}

.log-toggle {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.55rem 1.15rem 0.85rem;
  font-size: 0.85rem;
  color: var(--p-text-color);
  flex-shrink: 0;
}

.log-toggle label {
  cursor: pointer;
  user-select: none;
}

.confirm-msg {
  margin: 0;
  line-height: 1.5;
}
</style>
