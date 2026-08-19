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
    sortField="groupKey"
    :sortOrder="1"
    :rowHover="true"
    class="ado-table"
    :rowClass="rowClass"
    @rowClick="onRowClick"
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
        <i
          class="status-icon"
          :class="data.fetched ? 'pi pi-check-circle done' : 'pi pi-minus-circle pending'"
          v-tooltip="data.fetched ? '已下載資料' : '尚未下載資料'"
        />
      </template>
      <template #filter>
        <MultiSelect
          v-model="itemsStore.filters.fetched"
          :options="statusOptions"
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
        <div v-if="data.groupSize > 1" class="group-cell">
          <span class="group-ids">{{ data.groupIds.map((id: number) => `#${id}`).join(' · ') }}</span>
          <span v-if="data.redmineId" class="group-redmine">Redmine #{{ data.redmineId }}</span>
        </div>
        <i
          v-else
          class="status-icon"
          :class="data.grouped ? 'pi pi-check-circle done' : 'pi pi-minus-circle pending'"
          v-tooltip="data.grouped ? '已關聯分組（無其他相關項目）' : '尚未關聯分組'"
        />
      </template>
      <template #filter>
        <MultiSelect
          v-model="itemsStore.filters.grouped"
          :options="statusOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="全部"
          :maxSelectedLabels="allSelected(itemsStore.filters.grouped, statusValues) ? 0 : 1"
          selectedItemsLabel="全部"
          scrollHeight="2000px"
          class="w-full filter-control"
        />
      </template>
    </Column>
    <Column
      field="hasReport"
      header="產生報告"
      sortable
      headerStyle="width:8.5rem;white-space:nowrap"
      style="width:8.5rem;text-align:center"
      :showFilterMenu="false"
    >
      <template #body="{ data }">
        <i
          class="status-icon"
          :class="data.hasReport ? 'pi pi-check-circle done' : 'pi pi-minus-circle pending'"
          v-tooltip="data.hasReport ? '已產生報告' : '尚未產生報告'"
        />
      </template>
      <template #filter>
        <MultiSelect
          v-model="itemsStore.filters.hasReport"
          :options="statusOptions"
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
import type { AdoItem, AdoTableRow } from '@/types'

const emit = defineEmits<{
  'open-detail': [id: number]
}>()

const itemsStore = useItemsStore()
const statusOptions = [
  { label: 'Done', value: 'yes' },
  { label: 'Not yet', value: 'no' },
]
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

function onRowClick(event: { data: AdoItem }) {
  emit('open-detail', event.data.id)
}

function rowClass(data: AdoTableRow) {
  return data.groupSize > 1 ? 'grouped-row' : ''
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
  cursor: pointer;
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
.group-redmine {
  font-weight: 400;
  color: var(--p-text-secondary-color);
}
</style>
