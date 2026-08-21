<template>
  <Dialog
    v-model:visible="visible"
    header="載入 ID"
    modal
    :style="{ width: '36rem' }"
    @show="fillFromCurrent"
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
      <Button label="取消" outlined severity="secondary" @click="visible = false" />
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
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'
import { fetchAdoIds, loadItemSummaries } from '@/api/client'
import { useItemsStore } from '@/stores/items'
import { usePipelineStore } from '@/stores/pipeline'
import { errorMessage } from '@/utils/apiError'
import { parseIds } from '@/utils/parseIds'

const visible = defineModel<boolean>('visible', { default: false })

const itemsStore = useItemsStore()
const pipelineStore = usePipelineStore()
const toast = useToast()
const importText = ref('')
const importError = ref('')
const importing = ref(false)
const listing = ref(false)

function fillFromCurrent() {
  importError.value = ''
  importText.value = itemsStore.items.map(item => item.id).join(', ')
}

async function importIds() {
  importError.value = ''
  const ids = parseIds(importText.value)
  if (!ids.length) {
    importError.value = '請貼上至少一個 ID'
    return
  }
  if (pipelineStore.isRunning) return
  importing.value = true
  try {
    const result = await loadItemSummaries(ids)
    await pipelineStore.resetToStart()
    await itemsStore.refresh({ selectAll: true })
    toast.add({
      severity: 'success',
      summary: '已載入 ID',
      detail: `共 ${result.count} 筆`,
      life: 4000,
    })
    visible.value = false
  } catch (err) {
    importError.value = `載入失敗：${errorMessage(err)}`
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
    importError.value = `列出 ID 失敗：${errorMessage(err)}`
  } finally {
    listing.value = false
  }
}
</script>

<style scoped>
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

.error-msg {
  color: var(--p-red-500);
}
</style>
