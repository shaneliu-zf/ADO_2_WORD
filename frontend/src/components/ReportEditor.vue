<template>
  <div class="report-editor">
    <!-- ── Meta fields ─────────────────────────────────────────────────────── -->
    <div class="section-title">基本資訊</div>
    <div class="meta-grid">
      <div class="field">
        <label>ADO 主旨</label>
        <InputText v-model="local.ado_subject" class="w-full" :readonly="readonly" />
      </div>
      <div class="field">
        <label>測試環境</label>
        <InputText v-model="local.test_environment" class="w-full" :readonly="readonly" />
      </div>
      <div class="field">
        <label>Site</label>
        <InputText v-model="local.site" class="w-full" :readonly="readonly" />
      </div>
      <div class="field">
        <label>版本號</label>
        <InputText v-model="local.version" class="w-full" :readonly="readonly" />
      </div>
      <div class="field">
        <label>測試日期</label>
        <InputText v-model="local.test_date" class="w-full" :readonly="readonly" />
      </div>
      <div class="field">
        <label>測試人員</label>
        <InputText v-model="local.tester" class="w-full" :readonly="readonly" />
      </div>
      <div class="field">
        <label>審核人員</label>
        <InputText v-model="local.reviewer" class="w-full" :readonly="readonly" />
      </div>
      <div class="field">
        <label>Redmine ID</label>
        <InputText v-model="local.redmine_id" class="w-full" :readonly="readonly" />
      </div>
    </div>

    <!-- ── Test Items ──────────────────────────────────────────────────────── -->
    <div class="section-header">
      <span class="section-title">Test Items</span>
      <Button v-if="!readonly" icon="pi pi-plus" label="新增項目" size="small" outlined @click="addTestItem" />
    </div>

    <div v-if="!local.test_items.length" class="empty-hint">尚無測試項目</div>
    <div
      v-for="(item, idx) in local.test_items"
      :key="idx"
      class="item-card"
    >
      <div class="step-header">
        <span class="step-label">Item {{ item.no }}</span>
        <Button
          v-if="!readonly"
          icon="pi pi-trash"
          label="刪除"
          text
          rounded
          severity="danger"
          size="small"
          @click="removeTestItem(idx)"
        />
      </div>
      <div class="item-grid">
        <div class="field field-span">
          <label>項目名稱</label>
          <InputText v-model="item.item_name" class="w-full" :readonly="readonly" placeholder="例如：登入後能否看到首頁" />
        </div>
        <div class="field field-span">
          <label>測試資料</label>
          <Textarea
            :modelValue="testDataText(item)"
            @update:modelValue="(v: string) => setTestData(item, v)"
            rows="3"
            class="w-full"
            :readonly="readonly"
            placeholder="每行一筆，例如帳號、密碼"
          />
        </div>
        <div class="field">
          <label>預期結果</label>
          <Textarea v-model="item.expected_result" rows="2" class="w-full" :readonly="readonly" placeholder="應該出現什麼" />
        </div>
        <div class="field">
          <label>測試結果</label>
          <Textarea v-model="item.test_result" rows="2" class="w-full" :readonly="readonly" placeholder="實際結果，例如 Pass / Fail" />
        </div>
      </div>
    </div>

    <!-- ── Test Steps ──────────────────────────────────────────────────────── -->
    <div class="section-header">
      <span class="section-title">Test Steps</span>
      <Button v-if="!readonly" icon="pi pi-plus" label="新增" size="small" outlined @click="addTestStep" />
    </div>

    <div
      v-for="(step, idx) in local.test_steps"
      :key="idx"
      class="step-card"
    >
      <div class="step-header">
        <span class="step-label">Step {{ step.no }}</span>
        <Button
          v-if="!readonly"
          icon="pi pi-trash"
          text
          rounded
          severity="danger"
          size="small"
          @click="removeTestStep(idx)"
        />
      </div>
      <Textarea v-model="step.description" rows="3" class="w-full step-textarea" :readonly="readonly" />
      <div class="step-images">
        <div v-for="(img, iIdx) in step.images || []" :key="iIdx" class="step-img-wrap">
          <img
            :src="imageSrc(img)"
            :alt="`Step ${step.no} image ${iIdx + 1}`"
            class="step-img"
          />
          <Button
            v-if="!readonly"
            icon="pi pi-times"
            rounded
            text
            severity="danger"
            size="small"
            class="step-img-remove"
            @click="removeStepImage(idx, iIdx)"
          />
        </div>
        <Button
          v-if="!readonly"
          icon="pi pi-upload"
          label="上傳圖片"
          size="small"
          outlined
          :loading="uploadingStep === idx"
          @click="pickStepImage(idx)"
        />
      </div>
    </div>
    <input
      ref="fileInput"
      type="file"
      accept="image/png,image/jpeg,image/gif,image/webp,image/bmp"
      multiple
      hidden
      @change="onStepImagesSelected"
    />

    <!-- ── Save ────────────────────────────────────────────────────────────── -->
    <div v-if="showSave && !readonly" class="save-row">
      <Button label="儲存" icon="pi pi-save" :loading="saving" @click="emit('save', local)" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { uploadItemImage } from '@/api/client'
import type { Report, TestItem } from '@/types'

const props = defineProps<{
  report: Report
  saving?: boolean
  readonly?: boolean
  showSave?: boolean
}>()

const emit = defineEmits<{
  save: [report: Report]
}>()

// Deep-clone the report so edits don't mutate the prop directly
const local = ref<Report>(JSON.parse(JSON.stringify(props.report)))

const readonly = computed(() => props.readonly === true)
const showSave = computed(() => props.showSave !== false)
const toast = useToast()
const fileInput = ref<HTMLInputElement | null>(null)
const uploadTarget = ref(-1)
const uploadingStep = ref<number | null>(null)

watch(
  () => [props.report, props.readonly] as const,
  () => {
    local.value = JSON.parse(JSON.stringify(props.report))
  },
)

function getDraft(): Report {
  return local.value
}

function reset() {
  local.value = JSON.parse(JSON.stringify(props.report))
}

defineExpose({ getDraft, reset })

function testDataText(item: TestItem): string {
  return Array.isArray(item.test_data) ? item.test_data.join('\n') : String(item.test_data ?? '')
}

function setTestData(item: TestItem, value: string) {
  item.test_data = value.split('\n')
}

function addTestItem() {
  const no = local.value.test_items.length + 1
  local.value.test_items.push({
    no,
    item_name: '',
    test_data: [],
    expected_result: '',
    test_result: '',
  })
}

function removeTestItem(index: number) {
  local.value.test_items.splice(index, 1)
  // Renumber
  local.value.test_items.forEach((item, i) => {
    item.no = i + 1
  })
}

function addTestStep() {
  const no = local.value.test_steps.length + 1
  local.value.test_steps.push({ no, description: '', images: [] })
}

function removeTestStep(index: number) {
  local.value.test_steps.splice(index, 1)
  local.value.test_steps.forEach((s, i) => {
    s.no = i + 1
  })
}

function pickStepImage(index: number) {
  uploadTarget.value = index
  fileInput.value?.click()
}

async function onStepImagesSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  const index = uploadTarget.value
  const itemId = local.value.ado_id
  if (index < 0 || !itemId || !files.length) return
  const step = local.value.test_steps[index]
  if (!step) return
  if (!step.images) step.images = []
  uploadingStep.value = index
  try {
    for (const file of files) {
      const { src } = await uploadItemImage(itemId, file)
      step.images.push(src)
    }
  } catch (err) {
    toast.add({ severity: 'error', summary: '上傳失敗', detail: String(err), life: 4000 })
  } finally {
    uploadingStep.value = null
  }
}

function removeStepImage(stepIndex: number, imageIndex: number) {
  local.value.test_steps[stepIndex]?.images?.splice(imageIndex, 1)
}

function imageSrc(src: string): string {
  if (!src) return ''
  if (/^(https?:|data:|\/)/i.test(src)) return src
  return `/static/ado/${src.replace(/^\.\//, '')}`
}
</script>

<style scoped>
.report-editor {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  font-family: "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif;
}

.section-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--p-text-color);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--p-text-secondary-color);
}

.w-full {
  width: 100%;
}

.empty-hint {
  margin: 0;
  font-size: 0.82rem;
  color: var(--p-text-secondary-color);
}

.item-card {
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  background: var(--p-surface-50);
}

.item-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem 1rem;
}

.field-span {
  grid-column: 1 / -1;
}

.step-card {
  border: 1px solid var(--p-surface-200);
  border-radius: 6px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: var(--p-surface-50);
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.step-label {
  font-weight: 600;
  font-size: 0.9rem;
}

.step-textarea {
  resize: vertical;
}

.step-images {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.5rem;
}

.step-img-wrap {
  position: relative;
}

.step-img {
  max-width: 200px;
  max-height: 150px;
  border-radius: 4px;
  border: 1px solid var(--p-surface-200);
  object-fit: contain;
  display: block;
}

.step-img-remove {
  position: absolute;
  top: -6px;
  right: -6px;
}

.save-row {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.5rem;
}
</style>
