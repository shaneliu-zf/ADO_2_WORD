<template>
  <Dialog
    v-model:visible="visibleModel"
    :header="`ADO #${itemId}`"
    :style="{ width: '80vw', maxWidth: '1000px' }"
    :contentStyle="{ height: 'calc(85vh - 6rem)', overflowY: 'auto' }"
    modal
    @hide="onClose"
  >
    <!-- Loading -->
    <div v-if="loading" class="state-msg">
      <ProgressSpinner style="width:2rem;height:2rem" />
      <span>載入中…</span>
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="state-msg error">
      <i class="pi pi-exclamation-triangle" />
      {{ loadError }}
    </div>

    <TabView v-else :activeIndex="activeTab">
      <!-- ── Tab 0: Bob 報告 ─────────────────────────────────────────────────── -->
      <TabPanel header="Bob 報告" :disabled="!item?.hasJson">
        <div v-if="report" class="tab-content">
          <!-- Edit / Save / Cancel toolbar -->
          <div class="tab-toolbar">
            <Button v-if="!editing" label="編輯" icon="pi pi-pencil" size="small" outlined @click="startEdit" />
            <template v-else>
              <Button label="儲存" icon="pi pi-save" size="small" :loading="saving" @click="handleSave" />
              <Button label="取消" icon="pi pi-times" size="small" outlined severity="secondary" @click="cancelEdit" />
            </template>
          </div>

          <!-- Read-only view -->
          <template v-if="!editing">
            <!-- Subject info table -->
            <table class="info-table">
              <tbody>
                <tr v-for="f in META_FIELDS" :key="f.key">
                  <th>{{ f.label }}</th>
                  <td>{{ (report as Record<string, unknown>)[f.key] ?? '' }}</td>
                </tr>
              </tbody>
            </table>

            <!-- Test items table -->
            <div class="section-heading">測試項目</div>
            <table class="data-table">
              <thead>
                <tr>
                  <th style="width:40px">#</th>
                  <th>項目名稱</th>
                  <th>測試資料</th>
                  <th>預期結果</th>
                  <th>測試結果</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="ti in report.test_items" :key="ti.no">
                  <td>{{ ti.no }}</td>
                  <td>{{ ti.item_name }}</td>
                  <td><span v-html="(Array.isArray(ti.test_data) ? ti.test_data.join('<br>') : ti.test_data)"></span></td>
                  <td>{{ ti.expected_result }}</td>
                  <td>{{ ti.test_result }}</td>
                </tr>
              </tbody>
            </table>

            <!-- Test steps -->
            <div class="section-heading">測試步驟</div>
            <div v-for="step in report.test_steps" :key="step.no" class="step-card">
              <div class="step-label">Step {{ step.no }}</div>
              <div class="step-desc">{{ step.description }}</div>
              <div v-if="step.images && step.images.length" class="step-images">
                <img
                  v-for="(img, i) in step.images"
                  :key="i"
                  :src="imageSrc(img)"
                  :alt="`Step ${step.no} image ${i + 1}`"
                  class="step-img"
                />
              </div>
            </div>
          </template>

          <!-- Editing view -->
          <template v-else>
            <ReportEditor v-if="editDraft" :report="editDraft" :saving="saving" @save="handleSave" />
          </template>
        </div>
        <div v-else class="state-msg">無 Bob 報告資料</div>
      </TabPanel>

      <!-- ── Tab 1: ADO 原文 ─────────────────────────────────────────────────── -->
      <TabPanel header="ADO 原文">
        <div class="tab-content">
          <HtmlPreview v-if="htmlContent" :html="htmlContent" class="html-preview" />
          <div v-else class="state-msg">無 HTML 資料</div>
        </div>
      </TabPanel>
    </TabView>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import ReportEditor from '@/components/ReportEditor.vue'
import HtmlPreview from '@/components/HtmlPreview.vue'
import { fetchItemJson, fetchItemHtml, updateItem } from '@/api/client'
import type { AdoItem, Report } from '@/types'

const props = defineProps<{
  visible: boolean
  item: AdoItem | null
}>()

const emit = defineEmits<{
  'update:visible': [v: boolean]
}>()

const visibleModel = computed({
  get: () => props.visible,
  set: (v) => emit('update:visible', v),
})

const itemId = computed(() => props.item?.id ?? 0)

const toast = useToast()
const loading = ref(false)
const loadError = ref('')
const report = ref<Report | null>(null)
const htmlContent = ref('')
const saving = ref(false)
const editing = ref(false)
const editDraft = ref<Report | null>(null)

const activeTab = computed(() => (props.item?.hasJson ? 0 : 1))

const META_FIELDS = [
  { key: 'ado_subject',      label: 'ADO 主旨' },
  { key: 'test_environment', label: '測試環境' },
  { key: 'site',             label: 'Site' },
  { key: 'version',          label: '版本號' },
  { key: 'test_date',        label: '測試日期' },
  { key: 'tester',           label: '測試人員' },
  { key: 'reviewer',         label: '審核人員' },
]

async function load(id: number) {
  loading.value = true
  loadError.value = ''
  report.value = null
  htmlContent.value = ''
  editing.value = false
  editDraft.value = null

  try {
    const [jsonResult, htmlResult] = await Promise.allSettled([
      fetchItemJson(id),
      fetchItemHtml(id),
    ])
    if (jsonResult.status === 'fulfilled') report.value = jsonResult.value
    if (htmlResult.status === 'fulfilled') htmlContent.value = htmlResult.value
  } catch (err) {
    loadError.value = `載入失敗：${String(err)}`
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.visible, props.item?.id] as [boolean, number | undefined],
  ([visible, id]) => {
    if (visible && id != null) load(id)
  },
  { immediate: true },
)

function onClose() {
  editing.value = false
  editDraft.value = null
}

function startEdit() {
  if (!report.value) return
  editDraft.value = JSON.parse(JSON.stringify(report.value))
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  editDraft.value = null
}

async function handleSave(updated?: Report) {
  const data = updated ?? editDraft.value
  if (!data || !itemId.value) return
  saving.value = true
  try {
    await updateItem(itemId.value, data)
    report.value = data
    editing.value = false
    editDraft.value = null
    toast.add({ severity: 'success', summary: '儲存成功', detail: `ADO #${itemId.value} 已更新`, life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: '儲存失敗', detail: String(err), life: 4000 })
  } finally {
    saving.value = false
  }
}

function imageSrc(src: string): string {
  if (!src) return ''
  if (/^(https?:|data:|\/)/i.test(src)) return src
  return `/static/ado/${src.replace(/^\.\//, '')}`
}
</script>

<style scoped>
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-top: 0.5rem;
}

.tab-toolbar {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

/* ── Info table ─────────────────────────────────────────────────────────────── */
.info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}

.info-table th {
  width: 110px;
  text-align: left;
  font-weight: 600;
  color: var(--p-text-secondary-color);
  padding: 0.3rem 0.6rem 0.3rem 0;
  vertical-align: top;
  white-space: nowrap;
}

.info-table td {
  padding: 0.3rem 0;
  color: var(--p-text-color);
}

/* ── Data table ─────────────────────────────────────────────────────────────── */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.data-table th,
.data-table td {
  border: 1px solid var(--p-surface-200);
  padding: 0.35rem 0.5rem;
  text-align: left;
  vertical-align: top;
}

.data-table th {
  background: var(--p-surface-100);
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--p-text-secondary-color);
}

/* ── Section heading ────────────────────────────────────────────────────────── */
.section-heading {
  font-size: 0.9rem;
  font-weight: 700;
  border-bottom: 1px solid var(--p-surface-200);
  padding-bottom: 0.3rem;
  color: var(--p-text-color);
}

/* ── Step cards ─────────────────────────────────────────────────────────────── */
.step-card {
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  padding: 0.65rem 0.75rem;
  background: var(--p-surface-50);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.step-label {
  font-weight: 700;
  font-size: 0.85rem;
}

.step-desc {
  font-size: 0.85rem;
  white-space: pre-wrap;
}

.step-images {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.step-img {
  max-width: 180px;
  max-height: 130px;
  border-radius: 4px;
  border: 1px solid var(--p-surface-200);
  object-fit: contain;
}

/* ── HTML preview ───────────────────────────────────────────────────────────── */
.html-preview {
  height: 620px;
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
