import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchItems, deleteItems, fetchGroups, updateSession } from '@/api/client'
import { buildRelatedById, buildTableRows, filterItems, type ItemFilters } from '@/utils/tableRows'
import type { AdoItem, AdoTableRow, Group } from '@/types'

export const useItemsStore = defineStore('items', () => {
  const items = ref<AdoItem[]>([])
  const groups = ref<Group[]>([])
  const selectedIds = ref<Set<number>>(new Set())
  const sortBy = ref<string>('groupKey')
  const sortDir = ref<1 | -1>(1)
  const filters = ref<ItemFilters>({
    idText: '',
    titleText: '',
    types: [],
    states: [],
    fetched: [],
    relations: [],
    hasReport: [],
  })

  const relatedById = computed(() => buildRelatedById(groups.value))

  const filteredItems = computed(() =>
    filterItems(items.value, filters.value, relatedById.value),
  )

  const tableRows = computed<AdoTableRow[]>(() =>
    buildTableRows(filteredItems.value, relatedById.value, sortBy.value, sortDir.value),
  )

  const distinctTypes = computed(() => [...new Set(items.value.map(i => i.workItemType).filter(Boolean))])
  const distinctStates = computed(() => [...new Set(items.value.map(i => i.state).filter(Boolean))])

  function mergeSelected(current: string[], previousAll: string[], nextAll: string[]) {
    if (!current.length) return [...nextAll]
    const nextSet = new Set(nextAll)
    const kept = current.filter(value => nextSet.has(value))
    const added = nextAll.filter(value => !previousAll.includes(value))
    return [...new Set([...kept, ...added])]
  }

  function selectAllFilters(list: AdoItem[], previousTypes: string[], previousStates: string[]) {
    const nextTypes = [...new Set(list.map(i => i.workItemType).filter(Boolean))]
    const nextStates = [...new Set(list.map(i => i.state).filter(Boolean))]
    filters.value.types = mergeSelected(filters.value.types, previousTypes, nextTypes)
    filters.value.states = mergeSelected(filters.value.states, previousStates, nextStates)
    if (!filters.value.fetched.length) filters.value.fetched = ['yes', 'no']
    if (!filters.value.relations.length) filters.value.relations = ['related', 'solo', 'unknown']
    if (!filters.value.hasReport.length) filters.value.hasReport = ['yes', 'no']
  }

  async function refresh(options?: { selectAll?: boolean; restoreSelected?: number[] }) {
    const [nextItems, nextGroups] = await Promise.all([
      fetchItems(),
      fetchGroups().catch(() => [] as Group[]),
    ])
    const previousTypes = distinctTypes.value
    const previousStates = distinctStates.value
    const previousSelected = selectedIds.value
    items.value = nextItems
    groups.value = nextGroups
    const nextIds = nextItems.map(item => item.id)
    if (options?.selectAll) {
      selectedIds.value = new Set(nextIds)
      persistSelected(nextIds)
    } else if (options?.restoreSelected) {
      const keep = new Set(options.restoreSelected)
      selectedIds.value = new Set(nextIds.filter(id => keep.has(id)))
    } else {
      selectedIds.value = new Set(nextIds.filter(id => previousSelected.has(id)))
    }
    selectAllFilters(nextItems, previousTypes, previousStates)
  }

  function persistSelected(ids: number[]) {
    void updateSession({ selectedIds: ids })
  }

  async function removeItems(ids: number[]) {
    await deleteItems(ids)
    await refresh()
  }

  function setSelectedIds(next: number[]) {
    selectedIds.value = new Set(next)
    persistSelected(next)
  }

  function setSort(field: string, order: 1 | -1) {
    sortBy.value = field
    sortDir.value = order
  }

  return {
    items,
    groups,
    selectedIds,
    filters,
    filteredItems,
    tableRows,
    distinctTypes,
    distinctStates,
    refresh,
    removeItems,
    setSelectedIds,
    setSort,
  }
})
