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
          <div class="chart-row">
            <svg viewBox="0 0 42 42" class="donut">
              <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--p-surface-200)" stroke-width="6" />
              <circle
                v-for="ring in typeRings"
                :key="ring.label"
                cx="21" cy="21" r="15.915"
                fill="transparent"
                :stroke="ring.color"
                stroke-width="6"
                :stroke-dasharray="ring.dash"
                :stroke-dashoffset="ring.offset"
                class="donut-slice"
                @click="openList('type', ring.label, ring.label)"
              />
              <text x="21" y="22.5" text-anchor="middle" class="donut-total">{{ items.length }}</text>
            </svg>
            <ul class="legend">
              <li v-for="s in typeSlices" :key="s.label">
                <button type="button" @click="openList('type', s.label, s.label)">
                  <i :style="{ background: s.color }" />{{ s.label }}<b>{{ s.value }}</b>
                </button>
              </li>
            </ul>
          </div>
        </section>

        <section class="panel">
          <h2>有沒有 Redmine</h2>
          <div class="chart-row">
            <svg viewBox="0 0 42 42" class="donut">
              <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--p-surface-200)" stroke-width="6" />
              <circle
                v-for="ring in redmineRings"
                :key="ring.label"
                cx="21" cy="21" r="15.915"
                fill="transparent"
                :stroke="ring.color"
                stroke-width="6"
                :stroke-dasharray="ring.dash"
                :stroke-dashoffset="ring.offset"
                class="donut-slice"
                @click="openList('redmine', ring.key, ring.label)"
              />
              <text x="21" y="22.5" text-anchor="middle" class="donut-total">{{ items.length }}</text>
            </svg>
            <ul class="legend">
              <li v-for="s in redmineSlices" :key="s.label">
                <button type="button" @click="openList('redmine', s.key, s.label)">
                  <i :style="{ background: s.color }" />{{ s.label }}<b>{{ s.value }}</b>
                </button>
              </li>
            </ul>
          </div>
        </section>

        <section class="panel">
          <h2>狀態分布</h2>
          <div class="chart-row">
            <svg viewBox="0 0 42 42" class="donut">
              <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--p-surface-200)" stroke-width="6" />
              <circle
                v-for="ring in stateRings"
                :key="ring.label"
                cx="21" cy="21" r="15.915"
                fill="transparent"
                :stroke="ring.color"
                stroke-width="6"
                :stroke-dasharray="ring.dash"
                :stroke-dashoffset="ring.offset"
                class="donut-slice"
                @click="openList('state', ring.label, ring.label)"
              />
              <text x="21" y="22.5" text-anchor="middle" class="donut-total">{{ items.length }}</text>
            </svg>
            <ul class="legend">
              <li v-for="s in stateSlices" :key="s.label">
                <button type="button" @click="openList('state', s.label, s.label)">
                  <i :style="{ background: s.color }" />{{ s.label }}<b>{{ s.value }}</b>
                </button>
              </li>
            </ul>
          </div>
        </section>

        <section v-if="fetchedN" class="panel">
          <h2>Category</h2>
          <div class="chart-row">
            <svg viewBox="0 0 42 42" class="donut">
              <circle cx="21" cy="21" r="15.915" fill="transparent" stroke="var(--p-surface-200)" stroke-width="6" />
              <circle
                v-for="ring in categoryRings"
                :key="ring.label"
                cx="21" cy="21" r="15.915"
                fill="transparent"
                :stroke="ring.color"
                stroke-width="6"
                :stroke-dasharray="ring.dash"
                :stroke-dashoffset="ring.offset"
                class="donut-slice"
                @click="openList('category', ring.label, ring.label)"
              />
              <text x="21" y="22.5" text-anchor="middle" class="donut-total">{{ fetchedN }}</text>
            </svg>
            <ul class="legend">
              <li v-for="s in categorySlices" :key="s.label">
                <button type="button" @click="openList('category', s.label, s.label)">
                  <i :style="{ background: s.color }" />{{ s.label }}<b>{{ s.value }}</b>
                </button>
              </li>
            </ul>
          </div>
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>建立月份</h2>
          <ul class="bars">
            <li v-for="row in monthRows" :key="row.label">
              <button type="button" class="bar-row" @click="openList('month', row.label, row.label)">
                <span class="bar-label">{{ row.label }}</span>
                <span class="bar-track">
                  <span class="bar-fill" :style="{ width: barWidth(row.value, monthRows) }" />
                </span>
                <span class="bar-n">{{ row.value }} 張</span>
              </button>
            </li>
          </ul>
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>指派人</h2>
          <ul class="bars">
            <li v-for="row in assigneeRows" :key="row.label">
              <button type="button" class="bar-row" @click="openList('assignee', row.label, row.label)">
                <span class="bar-label">{{ row.label }}</span>
                <span class="bar-track">
                  <span class="bar-fill" :style="{ width: barWidth(row.value, assigneeRows) }" />
                </span>
                <span class="bar-n">{{ row.value }} 張</span>
              </button>
            </li>
          </ul>
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>創建者</h2>
          <ul class="bars">
            <li v-for="row in createdByRows" :key="row.label">
              <button type="button" class="bar-row" @click="openList('createdBy', row.label, `創建者：${row.label}`)">
                <span class="bar-label">{{ row.label }}</span>
                <span class="bar-track">
                  <span class="bar-fill" :style="{ width: barWidth(row.value, createdByRows) }" />
                </span>
                <span class="bar-n">{{ row.value }} 張</span>
              </button>
            </li>
          </ul>
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>SA</h2>
          <ul class="bars">
            <li v-for="row in saRows" :key="row.label">
              <button type="button" class="bar-row" @click="openList('sa', row.label, `SA：${row.label}`)">
                <span class="bar-label">{{ row.label }}</span>
                <span class="bar-track">
                  <span class="bar-fill" :style="{ width: barWidth(row.value, saRows) }" />
                </span>
                <span class="bar-n">{{ row.value }} 張</span>
              </button>
            </li>
          </ul>
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>工程師</h2>
          <ul class="bars">
            <li v-for="row in engineerRows" :key="row.label">
              <button type="button" class="bar-row" @click="openList('engineer', row.label, `工程師：${row.label}`)">
                <span class="bar-label">{{ row.label }}</span>
                <span class="bar-track">
                  <span class="bar-fill" :style="{ width: barWidth(row.value, engineerRows) }" />
                </span>
                <span class="bar-n">{{ row.value }} 張</span>
              </button>
            </li>
          </ul>
        </section>

        <section v-if="fetchedN" class="panel wide">
          <h2>測試人員</h2>
          <ul class="bars">
            <li v-for="row in testerRows" :key="row.label">
              <button type="button" class="bar-row" @click="openList('tester', row.label, `測試人員：${row.label}`)">
                <span class="bar-label">{{ row.label }}</span>
                <span class="bar-track">
                  <span class="bar-fill" :style="{ width: barWidth(row.value, testerRows) }" />
                </span>
                <span class="bar-n">{{ row.value }} 張</span>
              </button>
            </li>
          </ul>
        </section>

        <section class="panel wide">
          <h2>標題模組</h2>
          <ul class="bars">
            <li v-for="row in moduleRows" :key="row.label">
              <button type="button" class="bar-row" @click="openList('module', row.label, row.label)">
                <span class="bar-label">{{ row.label }}</span>
                <span class="bar-track">
                  <span class="bar-fill" :style="{ width: barWidth(row.value, moduleRows) }" />
                </span>
                <span class="bar-n">{{ row.value }} 張</span>
              </button>
            </li>
          </ul>
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
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { useItemsStore } from '@/stores/items'
import AdoDetailDialog from '@/components/AdoDetailDialog.vue'
import type { AdoItem } from '@/types'

type Slice = { label: string; value: number; color: string; key?: string }
type CountRow = { label: string; value: number }

const CLOSED = new Set(['Done', 'Cancel'])
const TYPE_COLORS: Record<string, string> = {
  Issue: 'var(--p-blue-500)',
  Task: 'var(--p-teal-500)',
}
const STATE_COLORS: Record<string, string> = {
  Done: 'var(--p-green-500)',
  Cancel: 'var(--p-surface-400)',
  'To Do': 'var(--p-orange-500)',
  Analyze: 'var(--p-amber-500)',
  Testing: 'var(--p-cyan-500)',
  Develop: 'var(--p-indigo-400)',
  Review: 'var(--p-purple-400)',
}
const CATEGORY_COLORS: Record<string, string> = {
  Bug: 'var(--p-red-400)',
  Data: 'var(--p-blue-500)',
  Enhance: 'var(--p-green-500)',
  CR: 'var(--p-purple-400)',
  Performance: 'var(--p-orange-500)',
}
const PALETTE = [
  'var(--p-blue-500)',
  'var(--p-teal-500)',
  'var(--p-orange-500)',
  'var(--p-green-500)',
  'var(--p-purple-400)',
  'var(--p-cyan-600)',
]

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
const items = computed(() => itemsStore.items)
const fetchedItems = computed(() => items.value.filter(i => i.fetched))
const fetchedN = computed(() => fetchedItems.value.length)

function moduleOf(title: string): string {
  const match = /^\[([^\]]+)\]/.exec(title || '')
  if (!match) return '無標記'
  const raw = match[1].trim()
  if (/^line changeover/i.test(raw)) return 'Line Changeover'
  return raw
}

function shortName(name: string): string {
  if (!name) return ''
  if (name === 'Shihan Chen WYMTN Wiwynn') return 'Shihan Chen'
  if (name === 'Justin TY Huang WYMTN Wiwynn') return 'Justin Huang'
  if (name.includes('@')) return name.split('@')[0]
  return name
}

function categoryLabel(name: string): string {
  return (name || '').trim() || '無標記'
}

function personLabel(name: string): string {
  return shortName(name) || '無標記'
}

function yearMonth(value: unknown): string {
  if (value == null || value === '') return ''
  const text = value instanceof Date ? value.toISOString() : String(value)
  const match = /(\d{4}-\d{2})/.exec(text)
  return match?.[1] ?? ''
}

function countMap(values: string[]): CountRow[] {
  const map = new Map<string, number>()
  for (const value of values) map.set(value, (map.get(value) || 0) + 1)
  return [...map.entries()]
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value || a.label.localeCompare(b.label))
}

function toRings(slices: Slice[]) {
  const total = slices.reduce((sum, s) => sum + s.value, 0)
  let offset = 25
  return slices.map(slice => {
    const pct = total ? (slice.value / total) * 100 : 0
    const ring = { ...slice, dash: `${pct} ${100 - pct}`, offset }
    offset -= pct
    return ring
  })
}

function barWidth(value: number, rows: CountRow[]): string {
  const max = Math.max(1, ...rows.map(r => r.value))
  return `${(value / max) * 100}%`
}

const issueN = computed(() => items.value.filter(i => i.workItemType === 'Issue').length)
const taskN = computed(() => items.value.filter(i => i.workItemType === 'Task').length)
const hasRm = computed(() => items.value.filter(i => Boolean(i.redmineId)).length)
const noRm = computed(() => items.value.length - hasRm.value)
const openN = computed(() => items.value.filter(i => !CLOSED.has(i.state)).length)

const typeSlices = computed<Slice[]>(() =>
  countMap(items.value.map(i => i.workItemType || '無標記')).map((row, index) => ({
    label: row.label,
    value: row.value,
    color: TYPE_COLORS[row.label] || PALETTE[index % PALETTE.length],
  })),
)
const redmineSlices = computed<Slice[]>(() =>
  [
    { label: '無 Redmine', value: noRm.value, color: 'var(--p-orange-500)', key: 'no' },
    { label: '有 Redmine', value: hasRm.value, color: 'var(--p-green-500)', key: 'yes' },
  ].filter(s => s.value > 0),
)
const stateSlices = computed<Slice[]>(() =>
  countMap(items.value.map(i => i.state || '無標記')).map((row, index) => ({
    label: row.label,
    value: row.value,
    color: STATE_COLORS[row.label] || PALETTE[index % PALETTE.length],
  })),
)
const typeRings = computed(() => toRings(typeSlices.value))
const redmineRings = computed(() => toRings(redmineSlices.value))
const stateRings = computed(() => toRings(stateSlices.value))
const categorySlices = computed<Slice[]>(() =>
  countMap(fetchedItems.value.map(i => categoryLabel(i.category))).map((row, index) => ({
    label: row.label,
    value: row.value,
    color: CATEGORY_COLORS[row.label] || PALETTE[index % PALETTE.length],
  })),
)
const categoryRings = computed(() => toRings(categorySlices.value))
const monthRows = computed(() =>
  countMap(fetchedItems.value.map(i => yearMonth(i.createdDate) || '無標記')).sort((a, b) =>
    a.label.localeCompare(b.label),
  ),
)
const assigneeRows = computed(() => countMap(fetchedItems.value.map(i => personLabel(i.assignedTo))))
const createdByRows = computed(() => countMap(fetchedItems.value.map(i => personLabel(i.createdBy))))
const saRows = computed(() => countMap(fetchedItems.value.map(i => personLabel(i.saBy))))
const engineerRows = computed(() => countMap(fetchedItems.value.map(i => personLabel(i.engineerBy))))
const testerRows = computed(() => countMap(fetchedItems.value.map(i => personLabel(i.testerBy))))
const moduleRows = computed(() => countMap(items.value.map(i => moduleOf(i.title))).slice(0, 10))

function rowsFor(kind: string, key: string): AdoItem[] {
  return items.value
    .filter(item => {
      if (kind === 'fetched') return item.fetched
      if (kind === 'unfetched') return !item.fetched
      if (kind === 'type') return (item.workItemType || '無標記') === key
      if (kind === 'redmine') return key === 'yes' ? Boolean(item.redmineId) : !item.redmineId
      if (kind === 'state') return (item.state || '無標記') === key
      if (kind === 'open') return !CLOSED.has(item.state)
      if (kind === 'month') return yearMonth(item.createdDate) === key || (!yearMonth(item.createdDate) && key === '無標記')
      if (kind === 'assignee') return personLabel(item.assignedTo) === key
      if (kind === 'createdBy') return personLabel(item.createdBy) === key
      if (kind === 'sa') return personLabel(item.saBy) === key
      if (kind === 'engineer') return personLabel(item.engineerBy) === key
      if (kind === 'tester') return personLabel(item.testerBy) === key
      if (kind === 'category') return item.fetched && categoryLabel(item.category) === key
      if (kind === 'module') return moduleOf(item.title) === key
      return false
    })
    .sort((a, b) => a.id - b.id)
}

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
    loadError.value = `載入失敗：${String(err)}`
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
.chart-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.donut {
  width: 140px;
  height: 140px;
  flex-shrink: 0;
}
.donut-total {
  font-size: 7px;
  fill: var(--p-text-color, #222);
  font-weight: 650;
}
.legend,
.bars {
  list-style: none;
  margin: 0;
  padding: 0;
}
.legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.donut-slice { cursor: pointer; }
.legend button,
.bar-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  border: 0;
  background: none;
  padding: 0;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-align: left;
}
.legend i {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}
.legend b,
.bar-n {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
}
.bars {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.bar-label {
  width: 120px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-track {
  flex: 1;
  min-width: 48px;
  height: 10px;
  background: var(--p-surface-200, #e5e7eb);
  border-radius: 99px;
  overflow: hidden;
}
.bar-fill {
  display: block;
  height: 100%;
  background: var(--p-blue-500);
  border-radius: 99px;
}
.bar-n {
  width: 4.5rem;
  text-align: right;
  color: var(--p-text-muted-color);
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
