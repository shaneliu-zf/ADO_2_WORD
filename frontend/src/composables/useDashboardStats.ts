import { computed } from 'vue'
import { useItemsStore } from '@/stores/items'
import type { AdoItem } from '@/types'

export type Slice = { label: string; value: number; color: string; key?: string }
export type CountRow = { label: string; value: number }

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

function moduleOf(title: string): string {
  const match = /^\[([^\]]+)\]/.exec(title || '')
  if (!match) return '無標記'
  const raw = match[1].trim()
  if (/^line changeover/i.test(raw)) return 'Line Changeover'
  return raw
}

export function shortName(name: string): string {
  if (!name) return ''
  if (name === 'Shihan Chen WYMTN Wiwynn') return 'Shihan Chen'
  if (name === 'Justin TY Huang WYMTN Wiwynn') return 'Justin Huang'
  if (name.includes('@')) return name.split('@')[0]
  return name
}

export function categoryLabel(name: string): string {
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

export function useDashboardStats() {
  const itemsStore = useItemsStore()
  const items = computed(() => itemsStore.items)
  const fetchedItems = computed(() => items.value.filter(i => i.fetched))
  const fetchedN = computed(() => fetchedItems.value.length)

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
  const categorySlices = computed<Slice[]>(() =>
    countMap(fetchedItems.value.map(i => categoryLabel(i.category))).map((row, index) => ({
      label: row.label,
      value: row.value,
      color: CATEGORY_COLORS[row.label] || PALETTE[index % PALETTE.length],
    })),
  )
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

  return {
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
  }
}
