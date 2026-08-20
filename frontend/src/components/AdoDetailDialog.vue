<template>
  <Dialog
    v-model:visible="visibleModel"
    :header="dialogHeader"
    :style="{ width: '80vw', maxWidth: '1000px' }"
    :baseZIndex="2000"
    :contentStyle="{ height: 'calc(85vh - 6rem)', overflowY: 'auto', display: 'flex', flexDirection: 'column' }"
    modal
    dismissableMask
    @hide="onClose"
  >
    <div v-if="mode === 'ado'" class="tab-content ado-mode">
      <div class="tab-toolbar">
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
      <HtmlPreview v-else-if="htmlContent" :html="htmlContent" class="html-preview" />
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
import { fetchItemJson, fetchItemHtml, updateItem, refreshWorkItem } from '@/api/client'
import { useItemsStore } from '@/stores/items'
import { usePipelineStore } from '@/stores/pipeline'
import type { AdoItem, Report } from '@/types'

const props = defineProps<{
  visible: boolean
  item: AdoItem | null
  mode: 'ado' | 'report'
}>()

const emit = defineEmits<{
  'update:visible': [v: boolean]
}>()

const pipelineStore = usePipelineStore()
const itemsStore = useItemsStore()

const visibleModel = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const itemId = computed(() => props.item?.id ?? 0)
const dialogHeader = computed(() =>
  props.mode === 'ado' ? `ADO #${itemId.value} 原文` : `ADO #${itemId.value} 報告`,
)

const toast = useToast()
const loading = ref(false)
const loadError = ref('')
const report = ref<Report | null>(null)
const htmlContent = ref('')
const saving = ref(false)
const refreshing = ref(false)
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
    loadError.value = `載入失敗：${String(err)}`
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.visible, props.item?.id, props.mode] as const,
  ([visible, id]) => {
    if (visible && id != null) void load(id)
  },
  { immediate: true },
)

function onClose() {
  editing.value = false
}

async function refreshAdo() {
  if (!itemId.value || pipelineStore.isRunning || refreshing.value) return
  refreshing.value = true
  loadError.value = ''
  try {
    await refreshWorkItem(itemId.value)
    htmlContent.value = await fetchItemHtml(itemId.value)
    const selected = [...itemsStore.selectedIds]
    await itemsStore.refresh()
    itemsStore.setSelectedIds(selected.filter(id => itemsStore.items.some(item => item.id === id)))
    toast.add({
      severity: 'success',
      summary: '已更新',
      detail: `ADO ${itemId.value} 已重新下載`,
      life: 3000,
    })
  } catch (err) {
    toast.add({ severity: 'error', summary: '更新失敗', detail: String(err), life: 4000 })
  } finally {
    refreshing.value = false
  }
}

function startEdit() {
  editing.value = true
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
    toast.add({ severity: 'error', summary: '儲存失敗', detail: String(err), life: 4000 })
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

/* ADO 原文模式：撐滿 dialog 高度，overflow 交給 iframe */
.tab-content.ado-mode {
  height: 100%;
  overflow: hidden;
}

.tab-toolbar {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  flex-shrink: 0;
}

.html-preview {
  flex: 1;
  min-height: 0;
  height: 100%;
}

/* ── State messages ─────────────────────────────────────────────────────────── */
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
