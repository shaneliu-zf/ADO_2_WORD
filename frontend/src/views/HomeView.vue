<template>
  <div class="home-view">
    <div class="content-row">
      <div class="table-area">
        <div class="left-toolbar">
          <Button
            label="載入 ID"
            icon="pi pi-download"
            outlined
            :loading="importing || listing"
            :disabled="pipelineStore.isRunning && !importing && !listing"
            @click="openImportDialog"
          />
          <Button
            label="刪除"
            icon="pi pi-trash"
            outlined
            severity="danger"
            :disabled="itemsStore.selectedIds.size === 0"
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
    <Dialog
      v-model:visible="importVisible"
      header="載入 ID"
      modal
      :style="{ width: '36rem' }"
      @show="fillImportFromCurrent"
    >
      <p class="import-lead">會透過輸入的 ID 去 ADO 撈取 Type、State、Title。</p>
      <p class="import-hint">可貼上 ID，例如 841, 842, 845；或按「填入全部 ID」取得全部 ID。</p>
      <Textarea
        v-model="importText"
        class="import-box"
        rows="6"
        autoResize
      />
      <p v-if="importError" class="error-msg">{{ importError }}</p>
      <template #footer>
        <Button label="取消" outlined severity="secondary" @click="importVisible = false" />
        <Button
          label="填入全部 ID"
          icon="pi pi-list"
          outlined
          :loading="listing"
          :disabled="pipelineStore.isRunning && !listing"
          @click="fillIdsFromAdo"
        />
        <Button
          label="載入"
          icon="pi pi-download"
          :loading="importing"
          :disabled="pipelineStore.isRunning && !importing"
          @click="importIds"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import AdoTable from '@/components/AdoTable.vue'
import PipelinePanel from '@/components/PipelinePanel.vue'
import LogPanel from '@/components/LogPanel.vue'
import AdoDetailDialog from '@/components/AdoDetailDialog.vue'
import ConfigDialog from '@/components/ConfigDialog.vue'
import { useItemsStore } from '@/stores/items'
import { usePipelineStore } from '@/stores/pipeline'
import { fetchAdoIds, fetchConfigStatus, loadItemSummaries } from '@/api/client'
import type { AdoItem } from '@/types'

const itemsStore = useItemsStore()
const pipelineStore = usePipelineStore()
const router = useRouter()
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
const configMissing = ref(false)
const importVisible = ref(false)
const importText = ref('')
const importError = ref('')
const importing = ref(false)

function currentIdText(): string {
  return itemsStore.items.map(item => item.id).join(', ')
}

function fillImportFromCurrent() {
  importError.value = ''
  importText.value = currentIdText()
}

function openImportDialog() {
  importVisible.value = true
}

function parseImportIds(text: string): number[] {
  const ids: number[] = []
  const seen = new Set<number>()
  for (const match of text.matchAll(/\d+/g)) {
    const id = Number(match[0])
    if (!id || seen.has(id)) continue
    seen.add(id)
    ids.push(id)
  }
  return ids
}

async function importIds() {
  importError.value = ''
  const ids = parseImportIds(importText.value)
  if (!ids.length) {
    importError.value = '請貼上至少一個 ID'
    return
  }
  if (pipelineStore.isRunning) return
  importing.value = true
  try {
    const result = await loadItemSummaries(ids)
    await pipelineStore.resetToStart()
    await itemsStore.refresh()
    toast.add({
      severity: 'success',
      summary: '已載入 ID',
      detail: `共 ${result.count} 筆`,
      life: 4000,
    })
    importVisible.value = false
  } catch (err) {
    importError.value = `載入失敗：${String(err)}`
  } finally {
    importing.value = false
  }
}

async function fillIdsFromAdo() {
  if (pipelineStore.isRunning) return
  listing.value = true
  importError.value = ''
  try {
    const ids = await fetchAdoIds()
    importText.value = ids.join(', ')
    toast.add({
      severity: 'success',
      summary: '已填入 ID',
      detail: `共 ${ids.length} 筆，請再按載入`,
      life: 3000,
    })
  } catch (err) {
    importError.value = `列出 ID 失敗：${String(err)}`
  } finally {
    listing.value = false
  }
}

async function refresh() {
  loading.value = true
  loadError.value = ''
  try {
    await pipelineStore.resetToStart()
    await itemsStore.refresh()
  } catch (err) {
    loadError.value = `載入失敗：${String(err)}`
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
  if (itemsStore.items.length > 0 || listing.value || pipelineStore.isRunning) return
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

.settings-btn {
  margin-left: auto;
}

.import-lead {
  margin: 0 0 0.35rem;
  line-height: 1.5;
}

.import-hint {
  margin: 0 0 0.5rem;
  color: var(--p-text-muted-color, #6b7280);
}

.import-box {
  width: 100%;
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
