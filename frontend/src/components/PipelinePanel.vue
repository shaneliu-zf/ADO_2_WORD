<template>
  <div class="pipeline-panel">
    <Button
      label="全流程自動完成"
      icon="pi pi-bolt"
      class="full-run-btn"
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
          <span class="step-hint">{{ stepHint(s) }}</span>
          <span
            v-if="shouldShowStepBar(s.index)"
            class="step-progress"
          >
            <span :class="stepBarClass(s.index)" :style="stepBarStyle(s.index)" />
          </span>
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
        @click="onPrevStep()"
      />
      <Button
        v-if="!isRunning"
        :label="executeLabel"
        icon="pi pi-play"
        class="btn-run"
        :loading="pipelineBusy"
        @click="runCurrent()"
      />
      <Button
        v-else
        label="中止執行"
        icon="pi pi-stop-circle"
        class="btn-run"
        severity="danger"
        @click="pipelineStore.abortScript()"
      />
    </div>

    <div class="log-toggle">
      <Checkbox v-model="showLog" inputId="show-log" binary />
      <label for="show-log">顯示 log</label>
    </div>

    <Dialog v-model:visible="unbindVisible" modal header="解綁關聯" :style="{ width: '28rem' }">
      <p class="confirm-msg">退回上一步時，是否解綁已合併的關聯分組？解綁後項目會恢復各自獨立。</p>
      <template #footer>
        <Button label="不解綁" outlined @click="prevWithoutUnbind" />
        <Button label="解綁" severity="danger" @click="prevWithUnbind" />
      </template>
    </Dialog>

    <Dialog v-model:visible="confirmVisible" modal :header="confirmTitle" :style="{ width: '28rem' }">
      <p class="confirm-msg">{{ confirmMessage }}</p>
      <template #footer>
        <Button :label="confirmSkipLabel" outlined @click="confirmSkip" />
        <Button :label="confirmRedoLabel" @click="confirmRedo" />
      </template>
    </Dialog>

    <Dialog v-model:visible="saveVisible" modal header="合併成 Word" :style="{ width: '28rem' }" @hide="onSaveDialogHide">
      <p class="confirm-msg">Word 已合併完成，是否下載？</p>
      <template #footer>
        <Button label="否" outlined @click="declineSave()" />
        <Button label="是" :loading="savingWord" @click="onSaveWord()" />
      </template>
    </Dialog>

    <Dialog v-model:visible="prereqVisible" modal header="尚有項目未完成前面步驟" :style="{ width: '32rem' }">
      <p class="confirm-msg">以下勾選項目還沒做完前面的步驟，是否先完成再繼續？</p>
      <ul class="prereq-list">
        <li v-for="row in prereqRows" :key="row.id">
          #{{ row.id }} — 缺：{{ row.missing.join('、') }}
        </li>
      </ul>
      <template #footer>
        <Button label="取消" outlined severity="secondary" @click="prereqVisible = false" />
        <Button label="先完成" @click="confirmPrereq" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch, type Ref } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import { STEP_DEFS, usePipelineStore } from '@/stores/pipeline'
import { useItemsStore } from '@/stores/items'
import { clearGroups } from '@/api/client'
import { storeToRefs } from 'pinia'
import type { AdoItem } from '@/types'

const pipelineStore = usePipelineStore()
const itemsStore = useItemsStore()
const toast = useToast()
const demoMode = inject<Ref<boolean>>('demoMode', ref(false))
const { currentStep, reachedStep, isRunning, runningStep, showLog, status, statusKind, stepProgress, pendingDocx, savingWord } = storeToRefs(pipelineStore)

const pipelineBusy = computed(() => isRunning.value && (runningStep.value ?? -1) >= 0)

const confirmVisible = ref(false)
const unbindVisible = ref(false)
const prereqVisible = ref(false)
const saveVisible = ref(false)

watch(pendingDocx, name => {
  if (name) saveVisible.value = true
})
const confirmKind = ref<'fetch' | 'report'>('fetch')
const pending = ref<{ script: string; index: number; ids: number[] } | null>(null)
const prereqRows = ref<Array<{ id: number; missing: string[] }>>([])
const prereqPending = ref<{ script: string; index: number; ids: number[] } | null>(null)

const hasRelatedGroups = computed(() =>
  itemsStore.groups.some(group => group.ids.length >= 2),
)

const confirmTitle = computed(() => (confirmKind.value === 'fetch' ? '下載資料' : '產生報告'))
const confirmMessage = computed(() =>
  confirmKind.value === 'fetch'
    ? '是否重新下載已經下載完成的項目'
    : '是否重新產生已產生的項目',
)
const confirmRedoLabel = computed(() => (confirmKind.value === 'fetch' ? '重新下載' : '重新產生'))
const confirmSkipLabel = '略過'

function stepHint(step: (typeof STEP_DEFS)[number]): string {
  if (!demoMode.value) return step.hint
  if (step.script === 'fetch') return '載入虛構 Work Item（不連 Azure DevOps）'
  if (step.script === 'report') return '套用預先準備的報告內容（不呼叫 Bob）'
  if (step.script === 'word') return '填進展示用範本，完成後下載 Word'
  return step.hint
}

const executeLabel = computed(() => {
  if (isRunning.value && pipelineBusy.value) return '處理中…'
  const step = STEP_DEFS.find(s => s.index === currentStep.value)
  return step ? `執行：${step.label}` : '執行'
})

const progressStyle = computed(() => {
  if (pipelineBusy.value) return {}
  return { width: `${(Math.min(reachedStep.value, 4) / 4) * 100}%` }
})

function shouldShowStepBar(index: number): boolean {
  return (pipelineBusy.value && currentStep.value === index) || reachedStep.value >= index
}

function stepBarClass(index: number): Record<string, boolean> {
  const isActive = pipelineBusy.value && currentStep.value === index
  const isDone = reachedStep.value >= index && !isActive
  const isIndeterminate = isActive && stepProgress.value === null
  return { done: isDone, indeterminate: isIndeterminate }
}

function stepBarStyle(index: number): Record<string, string> {
  const isActive = pipelineBusy.value && currentStep.value === index
  const isDone = reachedStep.value >= index && !isActive
  if (isDone) return { width: '100%' }
  if (isActive && stepProgress.value !== null) {
    return { width: `${stepProgress.value}%` }
  }
  return {}
}

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

function missingPrereqs(stepIndex: number, item: AdoItem): string[] {
  const missing: string[] = []
  if (stepIndex >= 2 && !item.fetched) missing.push('下載資料')
  if (stepIndex >= 3 && !item.grouped) missing.push('關聯分組')
  if (stepIndex >= 4 && !item.hasJson) missing.push('產生報告')
  return missing
}

function collectPrereqGaps(stepIndex: number, ids: number[]) {
  const idSet = new Set(ids)
  return itemsStore.items
    .filter(item => idSet.has(item.id))
    .map(item => ({ id: item.id, missing: missingPrereqs(stepIndex, item) }))
    .filter(row => row.missing.length > 0)
}

function startRun(script: string, ids: number[], index: number) {
  void pipelineStore.runScript(script, ids, index)
}

function proceedAfterPrereqCheck(script: string, ids: number[], index: number) {
  if (index === 1 && selectedWithFlag('hasHtml').length) {
    pending.value = { script, index, ids }
    confirmKind.value = 'fetch'
    confirmVisible.value = true
    return
  }
  if (index === 3 && selectedWithFlag('hasJson').length) {
    pending.value = { script, index, ids }
    confirmKind.value = 'report'
    confirmVisible.value = true
    return
  }
  startRun(script, ids, index)
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

  const gaps = collectPrereqGaps(step.index, ids)
  if (gaps.length) {
    prereqRows.value = gaps
    prereqPending.value = { script: step.script, index: step.index, ids }
    prereqVisible.value = true
    return
  }

  proceedAfterPrereqCheck(step.script, ids, step.index)
}

async function confirmPrereq() {
  const job = prereqPending.value
  prereqVisible.value = false
  prereqPending.value = null
  if (!job) return

  const idSet = new Set(job.ids)
  const selected = itemsStore.items.filter(item => idSet.has(item.id))
  const needFetch = job.index >= 2 ? selected.filter(i => !i.fetched).map(i => i.id) : []
  const needGroup = job.index >= 3 ? selected.filter(i => !i.grouped).map(i => i.id) : []
  const needReport = job.index >= 4 ? selected.filter(i => !i.hasJson).map(i => i.id) : []

  if (needFetch.length) {
    const ok = await pipelineStore.runScript('fetch', needFetch, 1)
    if (!ok) return
  }
  if (needGroup.length) {
    const ok = await pipelineStore.runScript('group', needGroup, 2)
    if (!ok) return
  }
  if (needReport.length) {
    const ok = await pipelineStore.runScript('report', needReport, 3)
    if (!ok) return
  }

  proceedAfterPrereqCheck(job.script, job.ids, job.index)
}

function confirmRedo() {
  const job = pending.value
  confirmVisible.value = false
  pending.value = null
  if (!job) return
  startRun(job.script, job.ids, job.index)
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
    await pipelineStore.skipStep(job.index)
    return
  }
  startRun(job.script, remaining, job.index)
}

async function onPrevStep() {
  if (currentStep.value === 2 && hasRelatedGroups.value) {
    unbindVisible.value = true
    return
  }
  await pipelineStore.prevStep()
}

async function prevWithoutUnbind() {
  unbindVisible.value = false
  await pipelineStore.prevStep()
}

async function prevWithUnbind() {
  unbindVisible.value = false
  const ids = resolveIds()
  if (!ids.length) {
    toast.add({
      severity: 'warn',
      summary: '尚未勾選',
      detail: '請先勾選要解綁的項目；未勾選時不會解綁全部。',
      life: 3500,
    })
    await pipelineStore.prevStep()
    return
  }
  await clearGroups(ids)
  await itemsStore.refresh()
  await pipelineStore.prevStep()
}

async function onSaveWord() {
  const ok = await pipelineStore.savePendingWord()
  if (ok) saveVisible.value = false
}

function declineSave() {
  saveVisible.value = false
  pipelineStore.dismissPendingWord()
}

function onSaveDialogHide() {
  if (savingWord.value) return
  if (pendingDocx.value) pipelineStore.dismissPendingWord()
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
  pipelineStore.runScript('main', ids, 0)
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
  background: var(--p-primary-500, #0f62fe);
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
  border-left-color: var(--p-primary-500, #0f62fe);
}

.step.current {
  border-left-color: var(--p-primary-600, #0043ce);
  box-shadow: 0 0 0 1px #a6c8ff inset;
  background: #edf4ff;
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
  background: #d0e2ff;
  color: #0f62fe;
}

.step.current .step-mark {
  background: var(--p-primary-500, #0f62fe);
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
  width: 0%;
  border-radius: 999px;
  background: var(--p-primary-500, #0f62fe);
  transition: width 0.35s ease;
}

/* 有實際進度數字時：由 inline style 控制 width，transition 提供平滑效果 */

/* 已完成：滿格靜態 */
.step-progress > span.done {
  width: 100%;
  transition: none;
}

/* 無進度數字（group / word）：indeterminate 滑動動畫 */
.step-progress > span.indeterminate {
  width: 40%;
  transition: none;
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

.prereq-list {
  margin: 0.75rem 0 0;
  padding-left: 1.25rem;
  max-height: 240px;
  overflow-y: auto;
  line-height: 1.5;
  font-size: 0.9rem;
}
</style>
