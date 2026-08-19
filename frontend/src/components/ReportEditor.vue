<template>
  <div class="report-editor">
    <!-- ── Meta fields ─────────────────────────────────────────────────────── -->
    <div class="section-title">基本資訊</div>
    <div class="meta-grid">
      <div class="field">
        <label>ADO 主旨</label>
        <InputText v-model="local.ado_subject" class="w-full" />
      </div>
      <div class="field">
        <label>測試環境</label>
        <InputText v-model="local.test_environment" class="w-full" />
      </div>
      <div class="field">
        <label>Site</label>
        <InputText v-model="local.site" class="w-full" />
      </div>
      <div class="field">
        <label>版本號</label>
        <InputText v-model="local.version" class="w-full" />
      </div>
      <div class="field">
        <label>測試日期</label>
        <InputText v-model="local.test_date" class="w-full" />
      </div>
      <div class="field">
        <label>測試人員</label>
        <InputText v-model="local.tester" class="w-full" />
      </div>
      <div class="field">
        <label>審核人員</label>
        <InputText v-model="local.reviewer" class="w-full" />
      </div>
      <div class="field">
        <label>Redmine ID</label>
        <InputText v-model="local.redmine_id" class="w-full" />
      </div>
    </div>

    <!-- ── Test Items ──────────────────────────────────────────────────────── -->
    <div class="section-header">
      <span class="section-title">Test Items</span>
      <Button icon="pi pi-plus" label="新增" size="small" outlined @click="addTestItem" />
    </div>

    <DataTable :value="local.test_items" editMode="cell" @cell-edit-complete="onCellEdit" class="test-items-table">
      <Column field="no" header="#" style="width:50px">
        <template #body="{ data }">{{ data.no }}</template>
      </Column>
      <Column field="item_name" header="項目名稱" style="min-width:160px">
        <template #editor="{ data, field }">
          <InputText v-model="data[field]" class="w-full" />
        </template>
      </Column>
      <Column field="test_data" header="測試資料" style="min-width:160px">
        <template #body="{ data }">
          <span>{{ Array.isArray(data.test_data) ? data.test_data.join('\n') : data.test_data }}</span>
        </template>
        <template #editor="{ data }">
          <Textarea
            :modelValue="Array.isArray(data.test_data) ? data.test_data.join('\n') : data.test_data"
            @update:modelValue="(v: string) => { data.test_data = v.split('\n') }"
            rows="3"
            class="w-full"
          />
        </template>
      </Column>
      <Column field="expected_result" header="預期結果" style="min-width:160px">
        <template #editor="{ data, field }">
          <InputText v-model="data[field]" class="w-full" />
        </template>
      </Column>
      <Column field="test_result" header="測試結果" style="min-width:120px">
        <template #editor="{ data, field }">
          <InputText v-model="data[field]" class="w-full" />
        </template>
      </Column>
      <Column header="" style="width:60px">
        <template #body="{ index }">
          <Button icon="pi pi-trash" text rounded severity="danger" size="small" @click="removeTestItem(index)" />
        </template>
      </Column>
    </DataTable>

    <!-- ── Test Steps ──────────────────────────────────────────────────────── -->
    <div class="section-header">
      <span class="section-title">Test Steps</span>
      <Button icon="pi pi-plus" label="新增" size="small" outlined @click="addTestStep" />
    </div>

    <div
      v-for="(step, idx) in local.test_steps"
      :key="idx"
      class="step-card"
    >
      <div class="step-header">
        <span class="step-label">Step {{ step.no }}</span>
        <Button
          icon="pi pi-trash"
          text
          rounded
          severity="danger"
          size="small"
          @click="removeTestStep(idx)"
        />
      </div>
      <Textarea v-model="step.description" rows="3" class="w-full step-textarea" />
      <div v-if="step.images && step.images.length" class="step-images">
        <img
          v-for="(img, iIdx) in step.images"
          :key="iIdx"
          :src="imageSrc(img)"
          :alt="`Step ${step.no} image ${iIdx + 1}`"
          class="step-img"
        />
      </div>
    </div>

    <!-- ── Save ────────────────────────────────────────────────────────────── -->
    <div class="save-row">
      <Button label="儲存" icon="pi pi-save" :loading="saving" @click="emit('save', local)" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import type { Report, TestItem, TestStep } from '@/types'

const props = defineProps<{
  report: Report
  saving?: boolean
}>()

const emit = defineEmits<{
  save: [report: Report]
}>()

// Deep-clone the report so edits don't mutate the prop directly
const local = ref<Report>(JSON.parse(JSON.stringify(props.report)))

watch(
  () => props.report,
  (newVal) => {
    local.value = JSON.parse(JSON.stringify(newVal))
  },
)

function onCellEdit(event: { newData: TestItem }) {
  // DataTable editable cell — data is mutated in-place via v-model in the editor slot
  void event
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

.test-items-table {
  font-size: 0.88rem;
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
  gap: 0.5rem;
}

.step-img {
  max-width: 200px;
  max-height: 150px;
  border-radius: 4px;
  border: 1px solid var(--p-surface-200);
  object-fit: contain;
}

.save-row {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.5rem;
}
</style>
