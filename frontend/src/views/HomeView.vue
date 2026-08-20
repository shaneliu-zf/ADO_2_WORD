<template>
  <div class="home-view">
    <div class="content-row">
      <div class="table-area">
        <div class="left-toolbar">
          <Button
            icon="pi pi-refresh"
            outlined
            rounded
            :loading="listing"
            :disabled="pipelineStore.isRunning && !listing"
            @click="reloadListed"
            v-tooltip="'重載：從 Azure DevOps 列出 ID'"
          />
          <Button
            icon="pi pi-trash"
            outlined
            rounded
            severity="danger"
            :disabled="itemsStore.selectedIds.size === 0"
            :loading="deleting"
            @click="confirmDelete"
            v-tooltip="itemsStore.selectedIds.size > 0 ? `刪除 ${itemsStore.selectedIds.size} 筆` : '請先勾選要刪除的項目'"
          />
          <Button
            icon="pi pi-cog"
            outlined
            rounded
            class="settings-btn"
            @click="configVisible = true"
            v-tooltip="'設定：填寫 config.json'"
          />
        </div>

        <div v-if="loading" class="loading-msg">
          <ProgressSpinner style="width:2rem;height:2rem" />
          <span>載入中…</span>
        </div>
        <div v-else-if="loadError" class="error-msg">
          <i class="pi pi-exclamation-triangle" />
          {{ loadError }}
          <Button label="重試" text size="small" @click="refresh" />
        </div>
        <template v-else>
          <div class="table-body">
            <AdoTable @open-detail="openDetail" />
          </div>
        </template>
        <LogPanel v-if="pipelineStore.showLog" />
      </div>

      <div class="pipeline-area">
        <PipelinePanel />
      </div>
    </div>

    <AdoDetailDialog
      v-model:visible="detailVisible"
      :item="detailItem"
      :mode="detailMode"
    />
    <ConfigDialog v-model:visible="configVisible" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import AdoTable from '@/components/AdoTable.vue'
import PipelinePanel from '@/components/PipelinePanel.vue'
import LogPanel from '@/components/LogPanel.vue'
import AdoDetailDialog from '@/components/AdoDetailDialog.vue'
import ConfigDialog from '@/components/ConfigDialog.vue'
import { useItemsStore } from '@/stores/items'
import { usePipelineStore } from '@/stores/pipeline'
import type { AdoItem } from '@/types'

const itemsStore = useItemsStore()
const pipelineStore = usePipelineStore()
const toast = useToast()
const confirm = useConfirm()
const loading = ref(false)
const listing = ref(false)
const loadError = ref('')
const deleting = ref(false)
const detailVisible = ref(false)
const detailItem = ref<AdoItem | null>(null)
const detailMode = ref<'ado' | 'report'>('ado')
const configVisible = ref(false)

async function reloadListed() {
  if (pipelineStore.isRunning) return
  listing.value = true
  try {
    const ok = await pipelineStore.runScript('list_ids', [], -1)
    if (ok) {
      toast.add({
        severity: 'success',
        summary: '已列出 ID',
        detail: `共 ${itemsStore.items.length} 筆`,
        life: 3000,
      })
    }
  } catch (err) {
    toast.add({ severity: 'error', summary: '列出 ID 失敗', detail: String(err), life: 4000 })
  } finally {
    listing.value = false
  }
}

async function refresh() {
  loading.value = true
  loadError.value = ''
  try {
    await pipelineStore.loadSession()
    await itemsStore.refresh()
  } catch (err) {
    loadError.value = `載入失敗：${String(err)}`
  } finally {
    loading.value = false
  }
  if (!loadError.value) promptIfEmpty()
}

function promptIfEmpty() {
  if (itemsStore.items.length > 0 || listing.value || pipelineStore.isRunning) return
  confirm.require({
    header: '目前沒有資料',
    message: '發現目前沒有資料，是否需要從 ADO 取得 ID 跟 Title',
    icon: 'pi pi-inbox',
    rejectProps: { label: '不用', severity: 'secondary', outlined: true },
    acceptProps: { label: '取得' },
    accept: () => {
      void reloadListed()
    },
  })
}

function confirmDelete() {
  const ids = [...itemsStore.selectedIds]
  if (!ids.length) return
  confirm.require({
    header: '確認刪除',
    message: `將永久刪除本機 ${ids.length} 筆資料（ADO JSON、附件與報告），無法復原。確定要刪除嗎？`,
    icon: 'pi pi-exclamation-triangle',
    rejectProps: { label: '取消', severity: 'secondary', outlined: true },
    acceptProps: { label: '刪除', severity: 'danger' },
    accept: () => {
      void handleDelete(ids)
    },
  })
}

async function handleDelete(ids: number[]) {
  deleting.value = true
  try {
    await itemsStore.removeItems(ids)
    toast.add({ severity: 'success', summary: '刪除成功', detail: `已刪除 ${ids.length} 筆`, life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: '刪除失敗', detail: String(err), life: 4000 })
  } finally {
    deleting.value = false
  }
}

function openDetail(payload: { id: number; mode: 'ado' | 'report' }) {
  const found = itemsStore.filteredItems.find(i => i.id === payload.id) ?? null
  detailItem.value = found
  detailMode.value = payload.mode
  detailVisible.value = true
}

onMounted(refresh)
</script>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 0.75rem 1rem;
  gap: 0.5rem;
  box-sizing: border-box;
  overflow: hidden;
}

.left-toolbar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-shrink: 0;
}

.left-toolbar :deep(.p-button) {
  width: 2.75rem;
  height: 2.75rem;
}

.left-toolbar :deep(.p-button .p-button-icon) {
  font-size: 1.15rem;
}

.settings-btn {
  margin-left: auto;
}

.content-row {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 0.75rem;
  overflow: hidden;
}

.table-area {
  flex: 3;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  gap: 0.5rem;
}

.table-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.pipeline-area {
  flex: 0 0 360px;
  width: 360px;
  min-width: 320px;
  max-width: 400px;
  overflow: hidden;
}

.loading-msg,
.error-msg {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  color: var(--p-text-secondary-color);
}

.error-msg {
  color: var(--p-red-500);
}
</style>
