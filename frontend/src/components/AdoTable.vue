<template>
  <DataTable
    :value="itemsStore.tableRows"
    v-model:selection="selectedRows"
    dataKey="id"
    scrollable
    scrollHeight="flex"
    filterDisplay="row"
    rowGroupMode="rowspan"
    groupRowsBy="groupKey"
    sortMode="single"
    sortField="groupKey"
    :sortOrder="1"
    :rowHover="true"
    class="ado-table"
    :rowClass="rowClass"
  >
    <Column selectionMode="multiple" headerStyle="width:3rem" :showFilterMenu="false" />
    <Column field="id" header="ID" sortable style="width:88px" :showFilterMenu="false">
      <template #filter>
        <InputText v-model="itemsStore.filters.idText" placeholder="ID" class="w-full filter-control" />
      </template>
    </Column>
    <Column field="workItemType" header="Type" sortable style="width:120px" :showFilterMenu="false">
      <template #filter>
        <MultiSelect
          v-model="itemsStore.filters.types"
          :options="itemsStore.distinctTypes"
          placeholder="全部"
          :maxSelectedLabels="allSelected(itemsStore.filters.types, itemsStore.distinctTypes) ? 0 : 1"
          selectedItemsLabel="全部"
          scrollHeight="2000px"
          class="w-full filter-control"
        />
      </template>
    </Column>
    <Column field="state" header="State" sortable style="width:130px" :showFilterMenu="false">
      <template #body="{ data }">
        <Tag :value="data.state" :severity="stateSeverity(data.state)" />
      </template>
      <template #filter>
        <MultiSelect
          v-model="itemsStore.filters.states"
          :options="itemsStore.distinctStates"
          placeholder="全部"
          :maxSelectedLabels="allSelected(itemsStore.filters.states, itemsStore.distinctStates) ? 0 : 1"
          selectedItemsLabel="全部"
          scrollHeight="2000px"
          class="w-full filter-control"
        />
      </template>
    </Column>
    <Column field="title" header="Title" sortable :showFilterMenu="false">
      <template #body="{ data }">{{ data.title }}</template>
      <template #filter>
        <InputText v-model="itemsStore.filters.titleText" placeholder="標題" class="w-full filter-control" />
      </template>
    </Column>
    <Column
      field="fetched"
      header="下載資料"
      sortable
      headerStyle="width:8.5rem;white-space:nowrap"
      style="width:8.5rem;text-align:center"
      :showFilterMenu="false"
    >
      <template #body="{ data }">
        <button
          v-if="data.fetched"
          type="button"
          class="view-data-link"
          @click.stop="emit('open-detail', { id: data.id, mode: 'ado' })"
        >
          查看資料
        </button>
        <span v-else class="no-data">未下載</span>
      </template>
      <template #filter>
        <MultiSelect
          v-model="itemsStore.filters.fetched"
          :options="fetchedOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="全部"
          :maxSelectedLabels="allSelected(itemsStore.filters.fetched, statusValues) ? 0 : 1"
          selectedItemsLabel="全部"
          scrollHeight="2000px"
          class="w-full filter-control"
        />
      </template>
    </Column>
    <Column
      field="groupKey"
      header="關聯分組"
      sortable
      headerStyle="width:10rem;white-space:nowrap"
      style="width:10rem;text-align:center"
      :showFilterMenu="false"
    >
      <template #body="{ data }">
        <div v-if="data.relationKind === 'related'" class="group-cell">
          <span class="group-ids">{{ data.groupIds.map((id: number) => `#${id}`).join(' · ') }}</span>
          <span v-if="data.redmineId" class="group-redmine">Redmine #{{ data.redmineId }}</span>
        </div>
        <span v-else class="no-data">{{ data.relationKind === 'solo' ? '無關聯item' : '未判斷關聯' }}</span>
      </template>
      <template #filter>
        <MultiSelect
          v-model="itemsStore.filters.relations"
          :options="relationOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="全部"
          :maxSelectedLabels="allSelected(itemsStore.filters.relations, relationValues) ? 0 : 1"
          selectedItemsLabel="全部"
          scrollHeight="2000px"
          class="w-full filter-control"
        />
      </template>
    </Column>
    <Column
      field="groupKey"
      header="產生報告"
      sortable
      headerStyle="width:8.5rem;white-space:nowrap"
      style="width:8.5rem;text-align:center"
      :showFilterMenu="false"
    >
      <template #body="{ data }">
        <button
          v-if="data.groupHasReport"
          type="button"
          class="view-data-link"
          @click.stop="emit('open-detail', { id: data.id, mode: 'report' })"
        >
          查看結果
        </button>
        <span v-else class="no-data">未產生</span>
      </template>
      <template #filter>
        <MultiSelect
          v-model="itemsStore.filters.hasReport"
          :options="reportOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="全部"
          :maxSelectedLabels="allSelected(itemsStore.filters.hasReport, statusValues) ? 0 : 1"
          selectedItemsLabel="全部"
          scrollHeight="2000px"
          class="w-full filter-control"
        />
      </template>
    </Column>
  </DataTable>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import { useItemsStore } from '@/stores/items'
import type { AdoTableRow } from '@/types'

const emit = defineEmits<{
  'open-detail': [payload: { id: number; mode: 'ado' | 'report' }]
}>()

const itemsStore = useItemsStore()
const fetchedOptions = [
  { label: '下載完成', value: 'yes' },
  { label: '未下載', value: 'no' },
]
const reportOptions = [
  { label: '查看結果', value: 'yes' },
  { label: '未產生', value: 'no' },
]
const relationOptions = [
  { label: '有關聯item', value: 'related' },
  { label: '無關聯item', value: 'solo' },
  { label: '未判斷關聯', value: 'unknown' },
]
const relationValues = ['related', 'solo', 'unknown']
const statusValues = ['yes', 'no']

function allSelected(selected: string[], options: string[]) {
  return options.length > 0 && selected.length === options.length && options.every(opt => selected.includes(opt))
}

/** Two-way bind: converts between Set<number> in store and AdoItem[] for DataTable. */
const selectedRows = computed<AdoTableRow[]>({
  get() {
    return itemsStore.tableRows.filter(i => itemsStore.selectedIds.has(i.id))
  },
  set(rows) {
    itemsStore.setSelectedIds(rows.map(r => r.id))
  },
})

function rowClass(data: AdoTableRow) {
  return data.relationKind === 'related' ? 'grouped-row' : ''
}

function stateSeverity(state: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  const s = state.toLowerCase()
  if (s.includes('done') || s.includes('closed')) return 'success'
  if (s.includes('testing')) return 'info'
  if (s.includes('develop') || s.includes('progress')) return 'warn'
  return 'secondary'
}
</script>

<style scoped>
.ado-table {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}
:deep(.p-datatable-thead > tr > th) {
  white-space: nowrap;
  vertical-align: middle;
}
:deep(.p-datatable-thead > tr > th.p-datatable-column-sorted),
:deep(.p-datatable-thead > tr > th.p-datatable-column-sorted .p-datatable-column-header-content),
:deep(.p-datatable-thead > tr > th.p-datatable-column-sorted .p-datatable-sort-icon) {
  background: inherit;
  color: inherit;
}
:deep(.p-datatable-thead .filter-control),
:deep(.p-datatable-thead .p-inputtext),
:deep(.p-datatable-thead .p-multiselect) {
  width: 100%;
  min-width: 0;
  height: 2.25rem;
  min-height: 2.25rem;
  box-sizing: border-box;
  font-size: 0.8125rem;
}
:deep(.p-datatable-thead .p-inputtext) {
  padding: 0 0.65rem;
  line-height: 2.25rem;
}
:deep(.p-datatable-thead .p-multiselect) {
  overflow: hidden;
}
:deep(.p-datatable-thead .p-multiselect .p-multiselect-label),
:deep(.p-datatable-thead .p-multiselect .p-multiselect-label-container) {
  padding: 0 0.65rem;
  line-height: 2.25rem;
  display: flex;
  align-items: center;
  min-height: 2.25rem;
}
:deep(.p-datatable-tbody > tr) {
  cursor: default;
}

.w-full {
  width: 100%;
}

.status-icon {
  font-size: 0.95rem;
}
.status-icon.done {
  color: var(--p-green-500, #22c55e);
}
:deep(.p-datatable-tbody > tr.grouped-row) {
  background: color-mix(in srgb, var(--p-green-50, #f0fdf4) 70%, white);
}
:deep(.p-datatable-tbody > tr.grouped-row:hover) {
  background: color-mix(in srgb, var(--p-green-100, #dcfce7) 80%, white);
}

.group-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  align-items: center;
  font-size: 0.75rem;
  line-height: 1.3;
  white-space: normal;
  font-weight: 600;
}
.no-data {
  color: var(--p-text-secondary-color);
  font-size: 0.85rem;
}
.view-data-link {
  background: none;
  border: none;
  padding: 0;
  color: var(--p-primary-color, #2563eb);
  cursor: pointer;
  font: inherit;
  font-size: 0.85rem;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.view-data-link:hover {
  color: var(--p-primary-600, #1d4ed8);
}
</style>
