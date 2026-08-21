<template>
  <Dialog
    v-model:visible="visible"
    :header="dialogHeader"
    class="ado-detail-dialog"
    :class="{ 'ado-detail-dialog--ado': mode === 'ado' }"
    :style="dialogStyle"
    :baseZIndex="2000"
    :contentStyle="contentStyle"
    modal
    dismissableMask
    @hide="onClose"
  >
    <div v-if="mode === 'ado'" class="ado-shell">
      <div class="tab-toolbar">
        <Button
          label="導出 HTML"
          icon="pi pi-download"
          size="small"
          outlined
          :disabled="!htmlContent || loading"
          @click="exportHtml"
        />
        <Button
          label="從 ADO 更新"
          icon="pi pi-refresh"
          size="small"
          outlined
          :loading="refreshing"
          :disabled="pipelineStore.isRunning || loading"
          @click="refreshAdo"
        />
      </div>
      <div v-if="loading" class="state-msg">
        <ProgressSpinner style="width:2rem;height:2rem" />
        <span>載入中…</span>
      </div>
      <div v-else-if="loadError" class="state-msg error">
        <i class="pi pi-exclamation-triangle" />
        {{ loadError }}
      </div>
      <div v-else-if="htmlContent" class="ado-preview-slot">
        <HtmlPreview :html="htmlContent" />
      </div>
      <div v-else class="state-msg">無 HTML 資料</div>
    </div>

    <template v-else>
      <div v-if="loading" class="state-msg">
        <ProgressSpinner style="width:2rem;height:2rem" />
        <span>載入中…</span>
      </div>
      <div v-else-if="loadError" class="state-msg error">
        <i class="pi pi-exclamation-triangle" />
        {{ loadError }}
      </div>
      <div v-else class="tab-content">
        <template v-if="report">
          <div class="tab-toolbar">
            <Button
              v-if="!editing"
              label="用 Bob 重新生成報告"
              icon="pi pi-replay"
              size="small"
              outlined
              :loading="regenerating"
              :disabled="pipelineStore.isRunning"
              @click="confirmRegenerate"
            />
            <Button v-if="!editing" label="編輯" icon="pi pi-pencil" size="small" outlined @click="startEdit" />
            <template v-else>
              <Button label="儲存" icon="pi pi-save" size="small" :loading="saving" @click="handleSave(editorRef?.getDraft())" />
              <Button label="取消" icon="pi pi-times" size="small" outlined severity="secondary" @click="cancelEdit" />
            </template>
          </div>
          <ReportEditor
            ref="editorRef"
            :report="report"
            :readonly="!editing"
            :show-save="false"
            :saving="saving"
            @save="handleSave"
          />
        </template>
        <div v-else class="state-msg">無 Bob 報告資料</div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import ReportEditor from '@/components/ReportEditor.vue'
import HtmlPreview from '@/components/HtmlPreview.vue'
import { fetchItemJson, fetchItemHtml, updateItem, refreshWorkItem, regenerateReport } from '@/api/client'
import { useItemsStore } from '@/stores/items'
import { usePipelineStore } from '@/stores/pipeline'
import { useConfirm } from 'primevue/useconfirm'
import { errorMessage } from '@/utils/apiError'
import { downloadHtmlFile, prepareAdoHtml } from '@/utils/adoHtml'
import type { AdoItem, Report } from '@/types'

const visible = defineModel<boolean>('visible', { default: false })
const props = defineProps<{
  item: AdoItem | null
  mode: 'ado' | 'report'
}>()

const pipelineStore = usePipelineStore()
const itemsStore = useItemsStore()

const itemId = computed(() => props.item?.id ?? 0)
const dialogHeader = computed(() =>
  props.mode === 'ado' ? `ADO #${itemId.value} 原文` : `ADO #${itemId.value} 報告`,
)

const dialogStyle = computed(() =>
  props.mode === 'ado'
    ? { width: '80vw', maxWidth: '1000px', height: '90vh', maxHeight: '90vh' }
    : { width: '80vw', maxWidth: '1000px' },
)

const contentStyle = computed(() =>
  props.mode === 'ado'
    ? {
        flex: '1 1 auto',
        minHeight: '0',
        height: '0',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column' as const,
        paddingBottom: '1rem',
      }
    : {
        maxHeight: 'calc(85vh - 6rem)',
        overflowY: 'auto' as const,
        display: 'flex',
        flexDirection: 'column' as const,
      },
)

const toast = useToast()
const confirm = useConfirm()
const loading = ref(false)
const loadError = ref('')
const report = ref<Report | null>(null)
const htmlContent = ref('')
const saving = ref(false)
const refreshing = ref(false)
const regenerating = ref(false)
const editing = ref(false)
const editorRef = ref<{ getDraft: () => Report; reset: () => void } | null>(null)

async function load(id: number) {
  loading.value = true
  loadError.value = ''
  report.value = null
  htmlContent.value = ''
  editing.value = false

  try {
    if (props.mode === 'ado') {
      htmlContent.value = await fetchItemHtml(id)
    } else {
      report.value = await fetchItemJson(id)
    }
  } catch (err) {
    loadError.value = `載入失敗：${errorMessage(err)}`
  } finally {
    loading.value = false
  }
}

watch(
  () => [visible.value, props.item?.id, props.mode] as const,
  ([isVisible, id]) => {
    if (isVisible && id != null) void load(id)
  },
  { immediate: true },
)

function onClose() {
  editing.value = false
}

function exportHtml() {
  if (!htmlContent.value || !itemId.value) return
  const html = prepareAdoHtml(htmlContent.value, {
    absolutizeOrigin: window.location.origin,
  })
  downloadHtmlFile(`ado_${itemId.value}.html`, html)
  toast.add({
    severity: 'success',
    summary: '已導出',
    detail: `ado_${itemId.value}.html`,
    life: 2500,
  })
}

async function refreshAdo() {
  if (!itemId.value || pipelineStore.isRunning || refreshing.value) return
  refreshing.value = true
  loadError.value = ''
  try {
    await refreshWorkItem(itemId.value)
    htmlContent.value = await fetchItemHtml(itemId.value)
    await itemsStore.refresh()
    toast.add({
      severity: 'success',
      summary: '已更新',
      detail: `ADO ${itemId.value} 已重新下載`,
      life: 3000,
    })
  } catch (err) {
    toast.add({ severity: 'error', summary: '更新失敗', detail: errorMessage(err), life: 4000 })
  } finally {
    refreshing.value = false
  }
}

function startEdit() {
  editing.value = true
}

function confirmRegenerate() {
  if (!itemId.value || pipelineStore.isRunning || regenerating.value) return
  confirm.require({
    header: '用 Bob 重新生成報告',
    message: '會依目前 ADO 資料重新產生此報告（會扣 Bobcoins），現有內容會被覆蓋。確定要繼續嗎？',
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: '取消', severity: 'secondary', outlined: true },
    acceptProps: { label: '重新生成' },
    accept: () => {
      void regenerate()
    },
  })
}

async function regenerate() {
  if (!itemId.value) return
  regenerating.value = true
  try {
    report.value = await regenerateReport(itemId.value)
    await itemsStore.refresh()
    toast.add({
      severity: 'success',
      summary: '已重新生成',
      detail: `ADO ${itemId.value} 報告已更新`,
      life: 3000,
    })
  } catch (err) {
    toast.add({ severity: 'error', summary: '重新生成失敗', detail: errorMessage(err), life: 5000 })
  } finally {
    regenerating.value = false
  }
}

function cancelEdit() {
  editorRef.value?.reset()
  editing.value = false
}

async function handleSave(updated?: Report) {
  const data = updated ?? editorRef.value?.getDraft()
  if (!data || !itemId.value) return
  saving.value = true
  try {
    await updateItem(itemId.value, data)
    report.value = data
    editing.value = false
    toast.add({ severity: 'success', summary: '儲存成功', detail: `ADO #${itemId.value} 已更新`, life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: '儲存失敗', detail: errorMessage(err), life: 4000 })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-top: 0.5rem;
  font-family: "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif;
}

.ado-shell {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  gap: 0.75rem;
  overflow: hidden;
}

.tab-toolbar {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  flex-shrink: 0;
}

.ado-preview-slot {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  width: 100%;
  overflow: hidden;
  background: #fff;
}

.ado-preview-slot :deep(iframe) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
}

.state-msg {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem;
  color: var(--p-text-secondary-color);
  justify-content: center;
}

.state-msg.error {
  color: var(--p-red-500);
}
</style>

<!-- Dialog 本體不在 scoped 根上，用全域 class 強制 flex 填滿 -->
<style>
.ado-detail-dialog.p-dialog {
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
}

.ado-detail-dialog.ado-detail-dialog--ado {
  height: 90vh !important;
  max-height: 90vh !important;
}

.ado-detail-dialog .p-dialog-header {
  flex-shrink: 0;
}

.ado-detail-dialog.ado-detail-dialog--ado .p-dialog-content {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
}
</style>
