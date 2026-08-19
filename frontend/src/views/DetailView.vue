<template>
  <div class="detail-view">
    <!-- Back link -->
    <RouterLink to="/" class="back-link">
      <i class="pi pi-arrow-left" />
      返回列表
    </RouterLink>

    <div v-if="loading" class="loading-msg">
      <ProgressSpinner style="width:2rem;height:2rem" />
      <span>載入中…</span>
    </div>

    <div v-else-if="loadError" class="error-msg">
      <i class="pi pi-exclamation-triangle" />
      {{ loadError }}
    </div>

    <template v-else-if="report">
      <!-- ── Report Editor ─────────────────────────────────────────────────── -->
      <div class="section-card">
        <div class="section-heading">
          <span>Report 編輯 — ADO #{{ id }}</span>
        </div>
        <ReportEditor :report="report" :saving="saving" @save="handleSave" />
      </div>

      <!-- ── HTML Preview ──────────────────────────────────────────────────── -->
      <div v-if="htmlContent" class="section-card">
        <div class="section-heading">HTML 預覽（唯讀）</div>
        <HtmlPreview :html="htmlContent" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import ReportEditor from '@/components/ReportEditor.vue'
import HtmlPreview from '@/components/HtmlPreview.vue'
import { fetchItemJson, fetchItemHtml, updateItem } from '@/api/client'
import type { Report } from '@/types'

const props = defineProps<{ id: number }>()

const toast = useToast()
const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const report = ref<Report | null>(null)
const htmlContent = ref('')

onMounted(async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [json, html] = await Promise.all([
      fetchItemJson(props.id),
      fetchItemHtml(props.id).catch(() => ''),
    ])
    report.value = json
    htmlContent.value = html
  } catch (err) {
    loadError.value = `載入失敗：${String(err)}`
  } finally {
    loading.value = false
  }
})

async function handleSave(updated: Report) {
  saving.value = true
  try {
    await updateItem(props.id, updated)
    report.value = updated
    toast.add({ severity: 'success', summary: '儲存成功', detail: `ADO #${props.id} 已更新`, life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: '儲存失敗', detail: String(err), life: 4000 })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.detail-view {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.9rem;
  color: var(--p-primary-color);
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.section-card {
  border: 1px solid var(--p-surface-200);
  border-radius: 8px;
  padding: 1.25rem;
  background: var(--p-surface-0);
}

.section-heading {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--p-surface-200);
}

.loading-msg,
.error-msg {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem;
  color: var(--p-text-secondary-color);
}

.error-msg {
  color: var(--p-red-500);
}
</style>
