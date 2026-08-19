import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchItems, deleteItems, fetchGroups, updateSession } from '@/api/client'
import type { AdoItem, AdoTableRow, Group } from '@/types'

export const useItemsStore = defineStore('items', () => {
  const items = ref<AdoItem[]>([])
  const groups = ref<Group[]>([])
  const selectedIds = ref<Set<number>>(new Set())
  const filters = ref({
    idText: '',
    titleText: '',
    types: [] as string[],
    states: [] as string[],
    fetched: [] as Array<'yes' | 'no'>,
    grouped: [] as Array<'yes' | 'no'>,
    hasReport: [] as Array<'yes' | 'no'>,
  })

  const filteredItems = computed(() => {
    const { idText, titleText, types, states, fetched, grouped, hasReport } = filters.value
    const idQ = idText.trim()
    const titleQ = titleText.toLowerCase().trim()
    return items.value.filter(item => {
      if (idQ && !String(item.id).includes(idQ)) return false
      if (titleQ && !item.title.toLowerCase().includes(titleQ)) return false
      if (!types.includes(item.workItemType)) return false
      if (!states.includes(item.state)) return false
      if (!matchFlag(fetched, item.fetched)) return false
      if (!matchFlag(grouped, item.grouped)) return false
      if (!matchFlag(hasReport, item.hasReport)) return false
      return true
    })
  })

  const tableRows = computed<AdoTableRow[]>(() => {
    const byId = new Map<number, Group>()
    for (const group of groups.value) {
      for (const id of group.ids) byId.set(id, group)
    }
    return filteredItems.value
      .map(item => {
        const group = byId.get(item.id)
        const groupIds = group?.ids?.length ? group.ids : [item.id]
        return {
          ...item,
          groupKey: group?.primary_id ?? item.id,
          groupSize: groupIds.length,
          groupIds,
          redmineId: group?.redmine_id ?? '',
        }
      })
      .sort((a, b) => {
        if (a.groupKey !== b.groupKey) return a.groupKey - b.groupKey
        return a.id - b.id
      })
  })

  const distinctTypes = computed(() => [...new Set(items.value.map(i => i.workItemType).filter(Boolean))])
  const distinctStates = computed(() => [...new Set(items.value.map(i => i.state).filter(Boolean))])

  function matchFlag(selected: Array<'yes' | 'no'>, value: boolean) {
    if (!selected.length) return false
    if (selected.length === 2) return true
    return selected.includes(value ? 'yes' : 'no')
  }

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
    if (!filters.value.grouped.length) filters.value.grouped = ['yes', 'no']
    if (!filters.value.hasReport.length) filters.value.hasReport = ['yes', 'no']
  }

  async function refresh() {
    const [nextItems, nextGroups] = await Promise.all([
      fetchItems(),
      fetchGroups().catch(() => [] as Group[]),
    ])
    const previousTypes = distinctTypes.value
    const previousStates = distinctStates.value
    items.value = nextItems
    groups.value = nextGroups
    selectedIds.value = new Set(nextItems.map(item => item.id))
    selectAllFilters(nextItems, previousTypes, previousStates)
  }

  async function keepOnlySelected() {
    await updateSession({ ids: [...selectedIds.value] })
    await refresh()
  }

  async function restoreListed() {
    await updateSession({ restoreListed: true })
    await refresh()
  }

  async function removeItems(ids: number[]) {
    await deleteItems(ids)
    await refresh()
  }

  function setSelectedIds(next: number[]) {
    selectedIds.value = new Set(next)
  }

  function clearFilters() {
    filters.value.idText = ''
    filters.value.titleText = ''
    filters.value.types = [...distinctTypes.value]
    filters.value.states = [...distinctStates.value]
    filters.value.fetched = ['yes', 'no']
    filters.value.grouped = ['yes', 'no']
    filters.value.hasReport = ['yes', 'no']
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
    keepOnlySelected,
    restoreListed,
    removeItems,
    setSelectedIds,
    clearFilters,
  }
})
