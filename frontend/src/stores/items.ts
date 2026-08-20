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
    relations: [] as Array<'related' | 'solo' | 'unknown'>,
    hasReport: [] as Array<'yes' | 'no'>,
  })

  const relatedById = computed(() => {
    const map = new Map<number, Group>()
    for (const group of groups.value) {
      if (group.ids.length < 2) continue
      for (const id of group.ids) map.set(id, group)
    }
    return map
  })

  function relationKindOf(item: AdoItem): 'related' | 'solo' | 'unknown' {
    if (relatedById.value.has(item.id)) return 'related'
    if (item.grouped) return 'solo'
    return 'unknown'
  }

  const filteredItems = computed(() => {
    const { idText, titleText, types, states, fetched, relations, hasReport } = filters.value
    const idQ = idText.trim()
    const titleQ = titleText.toLowerCase().trim()
    return items.value.filter(item => {
      if (idQ && !String(item.id).includes(idQ)) return false
      if (titleQ && !item.title.toLowerCase().includes(titleQ)) return false
      if (!types.includes(item.workItemType)) return false
      if (!states.includes(item.state)) return false
      if (!matchFlag(fetched, item.fetched)) return false
      if (!relations.includes(relationKindOf(item))) return false
      if (!matchFlag(hasReport, item.hasReport)) return false
      return true
    })
  })

  const tableRows = computed<AdoTableRow[]>(() => {
    const rows = filteredItems.value
      .map(item => {
        const related = relatedById.value.get(item.id)
        const groupIds = related?.ids?.length ? related.ids : [item.id]
        const relationKind = relationKindOf(item)
        return {
          ...item,
          groupKey: related?.primary_id ?? item.id,
          groupSize: groupIds.length,
          groupIds,
          redmineId: item.redmineId || related?.redmine_id || '',
          isGroupHead: false,
          groupHasReport: false,
          relationKind,
        }
      })
      .sort((a, b) => {
        if (a.groupKey !== b.groupKey) return a.groupKey - b.groupKey
        return a.id - b.id
      })
    const counts = new Map<number, number>()
    const reportByGroup = new Map<number, boolean>()
    for (const row of rows) {
      counts.set(row.groupKey, (counts.get(row.groupKey) ?? 0) + 1)
      if (row.hasReport) reportByGroup.set(row.groupKey, true)
    }
    const seen = new Set<number>()
    return rows.map(row => {
      const isGroupHead = !seen.has(row.groupKey)
      seen.add(row.groupKey)
      return {
        ...row,
        groupSize: counts.get(row.groupKey) ?? 1,
        isGroupHead,
        groupHasReport: reportByGroup.get(row.groupKey) ?? false,
      }
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
    if (!filters.value.relations.length) filters.value.relations = ['related', 'solo', 'unknown']
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
    filters.value.relations = ['related', 'solo', 'unknown']
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
