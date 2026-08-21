<template>
  <div class="home-view">
    <div class="content-row">
      <div class="table-area">
        <div class="left-toolbar">
          <Button
            label="載入 ID"
            icon="pi pi-download"
            outlined
            :disabled="pipelineStore.isRunning"
            @click="importVisible = true"
          />
          <Button
            label="只留下勾選項目"
            icon="pi pi-filter"
            outlined
            :disabled="!canKeepOnlySelected"
            :loading="keeping"
            @click="confirmKeepOnly"
          />
          <Button
            label="刪除"
            icon="pi pi-trash"
            outlined
            severity="danger"
            :disabled="itemsStore.selectedIds.size === 0 || pipelineStore.isRunning"
            :loading="deleting"
            @click="confirmDelete"
          />
          <Button
            label="分析"
            icon="pi pi-chart-bar"
            outlined
            class="settings-btn"
            @click="router.push('/dashboard')"
          />
          <Button
            label="設定"
            icon="pi pi-cog"
            outlined
            @click="configVisible = true"
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
    <ConfigDialog v-model:visible="configVisible" :required="configMissing" @saved="onConfigSaved" />
    <ImportIdsDialog v-model:visible="importVisible" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import AdoTable from '@/components/AdoTable.vue'
import PipelinePanel from '@/components/PipelinePanel.vue'
import LogPanel from '@/components/LogPanel.vue'
import AdoDetailDialog from '@/components/AdoDetailDialog.vue'
import ConfigDialog from '@/components/ConfigDialog.vue'
import ImportIdsDialog from '@/components/ImportIdsDialog.vue'
import { useItemsStore } from '@/stores/items'
import { usePipelineStore } from '@/stores/pipeline'
import { fetchConfigStatus, updateSession } from '@/api/client'
import { errorMessage } from '@/utils/apiError'
import type { AdoItem } from '@/types'

const itemsStore = useItemsStore()
const pipelineStore = usePipelineStore()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const loading = ref(false)
const loadError = ref('')
const deleting = ref(false)
const keeping = ref(false)
const detailVisible = ref(false)
const detailItem = ref<AdoItem | null>(null)
const detailMode = ref<'ado' | 'report'>('ado')
const configVisible = ref(false)
const configMissing = ref(false)
const importVisible = ref(false)

const canKeepOnlySelected = computed(() => {
  if (pipelineStore.isRunning) return false
  const selected = itemsStore.selectedIds.size
  if (!selected) return false
  return selected < itemsStore.items.length
})

async function refresh() {
  loading.value = true
  loadError.value = ''
  try {
    const session = await pipelineStore.loadSession()
    await itemsStore.refresh({ restoreSelected: session.selectedIds ?? [] })
  } catch (err) {
    loadError.value = `載入失敗：${errorMessage(err)}`
  } finally {
    loading.value = false
  }
  if (!loadError.value) await checkSetup()
}

async function checkSetup() {
  try {
    const status = await fetchConfigStatus()
    if (!status.exists) {
      configMissing.value = true
      configVisible.value = true
      return
    }
  } catch {
    // 設定狀態讀不到時仍繼續後面的空清單提示
  }
  promptIfEmpty()
}

function onConfigSaved() {
  configMissing.value = false
  promptIfEmpty()
}

function promptIfEmpty() {
  if (itemsStore.items.length > 0 || pipelineStore.isRunning) return
  confirm.require({
    header: '目前沒有資料',
    message: '發現目前沒有資料，是否需要從 ADO 取得 ID 跟 Title',
    icon: 'pi pi-inbox',
    rejectProps: { label: '不用', severity: 'secondary', outlined: true },
    acceptProps: { label: '取得' },
    accept: () => {
      importVisible.value = true
    },
  })
}

function confirmKeepOnly() {
  const ids = [...itemsStore.selectedIds]
  if (!ids.length) return
  const drop = itemsStore.items.length - ids.length
  confirm.require({
    header: '只留下勾選項目',
    message: `清單將只保留勾選的 ${ids.length} 筆，其餘 ${drop} 筆會從目前清單移除（本機檔案不會刪除）。確定嗎？`,
    icon: 'pi pi-filter',
    rejectProps: { label: '取消', severity: 'secondary', outlined: true },
    acceptProps: { label: '只留下勾選' },
    accept: () => {
      void handleKeepOnly()
    },
  })
}

async function handleKeepOnly() {
  const ids = [...itemsStore.selectedIds]
  if (!ids.length) return
  keeping.value = true
  try {
    await updateSession({ ids, selectedIds: ids })
    await itemsStore.refresh({ selectAll: true })
    toast.add({
      severity: 'success',
      summary: '已更新清單',
      detail: `目前留下 ${ids.length} 筆`,
      life: 3000,
    })
  } catch (err) {
    toast.add({ severity: 'error', summary: '更新失敗', detail: errorMessage(err), life: 4000 })
  } finally {
    keeping.value = false
  }
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
    toast.add({ severity: 'error', summary: '刪除失敗', detail: errorMessage(err), life: 4000 })
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
