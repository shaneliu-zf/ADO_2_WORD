<template>
  <div class="dash">
    <header class="dash-head">
      <Button icon="pi pi-arrow-left" label="返回列表" text @click="router.push('/')" />
      <h1>資料分析</h1>
      <span class="muted">點統計卡、圖例或長條圖可打開該分類清單</span>
    </header>

    <div v-if="loading" class="status-row">
      <ProgressSpinner style="width:2rem;height:2rem" />
      <span>載入中…</span>
    </div>
    <div v-else-if="loadError" class="status-row error">
      <i class="pi pi-exclamation-triangle" />
      {{ loadError }}
      <Button label="重試" text size="small" @click="load" />
    </div>

    <template v-else>
      <div class="stats">
        <button class="stat" type="button" @click="openList('fetched', '', '已下載')">
          <strong>{{ fetchedN }} / {{ items.length }}</strong>
          <span>已下載／清單</span>
        </button>
        <div class="stat split">
          <button type="button" @click="openList('type', 'Issue', 'Issue')">
            <strong>{{ issueN }}</strong>
            <span>Issue</span>
          </button>
          <button type="button" @click="openList('type', 'Task', 'Task')">
            <strong>{{ taskN }}</strong>
            <span>Task</span>
          </button>
        </div>
        <div class="stat warn split">
          <button type="button" @click="openList('redmine', 'yes', '有 Redmine')">
            <strong>{{ hasRm }}</strong>
            <span>有 Redmine</span>
          </button>
          <button type="button" @click="openList('redmine', 'no', '無 Redmine')">
            <strong>{{ noRm }}</strong>
            <span>沒有</span>
          </button>
        </div>
        <button class="stat danger" type="button" @click="openList('open', '', '未關閉')">
          <strong>{{ openN }}</strong>
          <span>未關閉</span>
        </button>
      </div>

      <p v-if="!fetchedN" class="need-fetch">
        建立月份、指派人、創建者、SA、工程師、測試人員、Category 要讀本機 ADO JSON。
        目前清單 {{ items.length }} 筆都還沒下載，請回首頁勾選後執行「下載資料」。
      </p>

      <div class="charts">
        <section class="panel">
          <h2>Work Item 類型</h2>
          <DonutChart :slices="typeSlices" :total="items.length" @select="s => openList('type', s.label, s.label)" />
        </section>

        <section class="panel">
          <h2>有沒有 Redmine</h2>
          <DonutChart
            :slices="redmineSlices"
            :total="items.length"
            @select="s => openList('redmine', s.key ?? s.label, s.label)"
          />
        </section>

        <section class="panel">
          <h2>狀態分布</h2>
          <DonutChart :slices="stateSlices" :total="items.length" @select="s => openList('state', s.label, s.label)" />
        </section>

        <section v-if="fetchedN" class="panel">
          <h2>Category</h2>
          <DonutChart
            :slices="categorySlices"
            :total="fetchedN"
            @select="s => openList('category', s.label, s.label)"
          />
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>建立月份</h2>
          <BarList :rows="monthRows" @select="row => openList('month', row.label, row.label)" />
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>指派人</h2>
          <BarList :rows="assigneeRows" @select="row => openList('assignee', row.label, row.label)" />
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>創建者</h2>
          <BarList :rows="createdByRows" @select="row => openList('createdBy', row.label, `創建者：${row.label}`)" />
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>SA</h2>
          <BarList :rows="saRows" @select="row => openList('sa', row.label, `SA：${row.label}`)" />
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>工程師</h2>
          <BarList :rows="engineerRows" @select="row => openList('engineer', row.label, `工程師：${row.label}`)" />
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>測試人員</h2>
          <BarList :rows="testerRows" @select="row => openList('tester', row.label, `測試人員：${row.label}`)" />
        </section>

        <section class="panel wide">
          <h2>標題模組</h2>
          <BarList :rows="moduleRows" @select="row => openList('module', row.label, row.label)" />
        </section>
      </div>
    </template>

    <Dialog
      v-model:visible="listVisible"
      :header="listTitle"
      modal
      dismissableMask
      :style="{ width: '72vw', maxWidth: '960px' }"
    >
      <div class="list-toolbar">
        <span class="muted">{{ listRows.length }} 筆</span>
        <Button label="複製 ID" size="small" outlined icon="pi pi-copy" @click="copyIds" />
      </div>
      <DataTable :value="listRows" dataKey="id" scrollable scrollHeight="420px" stripedRows>
        <Column field="id" header="ID" sortable style="width:88px">
          <template #body="{ data }">{{ data.id }}</template>
        </Column>
        <Column field="workItemType" header="類型" sortable style="width:100px" />
        <Column field="state" header="狀態" sortable style="width:110px" />
        <Column field="category" header="Category" sortable style="width:110px">
          <template #body="{ data }">{{ categoryLabel(data.category) }}</template>
        </Column>
        <Column field="redmineId" header="Redmine" sortable style="width:110px">
          <template #body="{ data }">{{ data.redmineId || '—' }}</template>
        </Column>
        <Column field="assignedTo" header="指派" sortable style="width:160px">
          <template #body="{ data }">{{ shortName(data.assignedTo) || '—' }}</template>
        </Column>
        <Column field="title" header="標題">
          <template #body="{ data }">
            <button type="button" class="title-link" @click="openAdo(data)">{{ data.title }}</button>
          </template>
        </Column>
      </DataTable>
    </Dialog>

    <AdoDetailDialog v-model:visible="detailVisible" :item="detailItem" mode="ado" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { useItemsStore } from '@/stores/items'
import AdoDetailDialog from '@/components/AdoDetailDialog.vue'
import DonutChart from '@/components/charts/DonutChart.vue'
import BarList from '@/components/charts/BarList.vue'
import { categoryLabel, shortName, useDashboardStats } from '@/composables/useDashboardStats'
import { errorMessage } from '@/utils/apiError'
import type { AdoItem } from '@/types'

const router = useRouter()
const toast = useToast()
const itemsStore = useItemsStore()
const loading = ref(false)
const loadError = ref('')
const listVisible = ref(false)
const listTitle = ref('')
const listRows = ref<AdoItem[]>([])
const detailVisible = ref(false)
const detailItem = ref<AdoItem | null>(null)

const {
  items,
  fetchedN,
  issueN,
  taskN,
  hasRm,
  noRm,
  openN,
  typeSlices,
  redmineSlices,
  stateSlices,
  categorySlices,
  monthRows,
  assigneeRows,
  createdByRows,
  saRows,
  engineerRows,
  testerRows,
  moduleRows,
  rowsFor,
} = useDashboardStats()

function openList(kind: string, key: string, title: string) {
  listRows.value = rowsFor(kind, key)
  listTitle.value = `${title} · ${listRows.value.length} 筆`
  listVisible.value = true
}

function openAdo(item: AdoItem) {
  detailItem.value = item
  detailVisible.value = true
}

async function copyIds() {
  const text = listRows.value.map(item => String(item.id)).join(', ')
  try {
    await navigator.clipboard.writeText(text)
    toast.add({ severity: 'success', summary: '已複製 ID', detail: `${listRows.value.length} 筆`, life: 2500 })
  } catch {
    toast.add({ severity: 'error', summary: '複製失敗', life: 2500 })
  }
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    await itemsStore.refresh()
  } catch (err) {
    loadError.value = `載入失敗：${errorMessage(err)}`
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.dash {
  min-height: 100vh;
  padding: 1rem 1.25rem 2rem;
  box-sizing: border-box;
  background: var(--p-surface-50, #f8fafc);
}
.dash-head {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.dash-head h1 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 650;
}
.muted {
  color: var(--p-text-muted-color, #6b7280);
  font-size: 0.85rem;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
}
.status-row.error { color: var(--p-red-500); }
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.need-fetch {
  margin: 0 0 1rem;
  padding: 0.75rem 1rem;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  color: #9a3412;
  font-size: 0.9rem;
}
.stat {
  border: 1px solid var(--p-content-border-color, #e5e7eb);
  background: #fff;
  border-radius: 8px;
  padding: 0.9rem 1rem;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
}
.stat.split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 0;
  cursor: default;
}
.stat.split button {
  border: 0;
  background: none;
  padding: 0.9rem 1rem;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
}
.stat strong {
  display: block;
  font-size: 1.35rem;
  font-weight: 650;
}
.stat span {
  color: var(--p-text-muted-color);
  font-size: 0.8rem;
}
.stat.warn strong { color: var(--p-orange-600); }
.stat.danger strong { color: var(--p-red-500); }
.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.panel {
  background: #fff;
  border: 1px solid var(--p-content-border-color, #e5e7eb);
  border-radius: 8px;
  padding: 0.9rem 1rem;
}
.panel.wide { grid-column: span 2; }
.panel h2 {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  font-weight: 650;
}
.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.title-link {
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  color: var(--p-primary-color, #2563eb);
  text-align: left;
  cursor: pointer;
}
.title-link:hover { text-decoration: underline; }
@media (max-width: 960px) {
  .stats,
  .charts { grid-template-columns: 1fr; }
  .panel.wide { grid-column: span 1; }
}
</style>
