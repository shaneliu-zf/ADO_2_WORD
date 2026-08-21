import type { AdoItem, AdoTableRow, Group } from '@/types'

export type ItemFilters = {
  idText: string
  titleText: string
  types: string[]
  states: string[]
  fetched: Array<'yes' | 'no'>
  relations: Array<'related' | 'solo' | 'unknown'>
  hasReport: Array<'yes' | 'no'>
}

export function buildRelatedById(groups: Group[]): Map<number, Group> {
  const map = new Map<number, Group>()
  for (const group of groups) {
    if (group.ids.length < 2) continue
    for (const id of group.ids) map.set(id, group)
  }
  return map
}

export function relationKindOf(
  item: AdoItem,
  relatedById: Map<number, Group>,
): AdoTableRow['relationKind'] {
  if (relatedById.has(item.id)) return 'related'
  if (item.grouped) return 'solo'
  return 'unknown'
}

export function matchFlag(selected: Array<'yes' | 'no'>, value: boolean) {
  if (!selected.length) return false
  if (selected.length === 2) return true
  return selected.includes(value ? 'yes' : 'no')
}

export function filterItems(
  items: AdoItem[],
  filters: ItemFilters,
  relatedById: Map<number, Group>,
): AdoItem[] {
  const { idText, titleText, types, states, fetched, relations, hasReport } = filters
  const idQ = idText.trim()
  const titleQ = titleText.toLowerCase().trim()
  return items.filter(item => {
    if (idQ && !String(item.id).includes(idQ)) return false
    if (titleQ && !item.title.toLowerCase().includes(titleQ)) return false
    if (!types.includes(item.workItemType)) return false
    if (!states.includes(item.state)) return false
    if (!matchFlag(fetched, item.fetched)) return false
    if (!relations.includes(relationKindOf(item, relatedById))) return false
    if (!matchFlag(hasReport, item.hasReport)) return false
    return true
  })
}

export function buildTableRows(
  items: AdoItem[],
  relatedById: Map<number, Group>,
  sortBy: string,
  sortDir: 1 | -1,
): AdoTableRow[] {
  const mapped = items.map(item => {
    const related = relatedById.get(item.id)
    const groupIds = related?.ids?.length ? related.ids : [item.id]
    return {
      ...item,
      groupKey: related?.primary_id ?? item.id,
      groupSize: groupIds.length,
      groupIds,
      redmineId: related?.redmine_id ?? item.redmineId ?? '',
      isGroupHead: false,
      groupHasReport: false,
      relationKind: relationKindOf(item, relatedById),
    }
  })

  const reportByGroup = new Map<number, boolean>()
  for (const row of mapped) {
    if (row.hasReport) reportByGroup.set(row.groupKey, true)
  }

  const field = sortBy as keyof AdoTableRow
  const groupHeads = new Map<number, AdoTableRow>()
  for (const row of mapped) {
    if (!groupHeads.has(row.groupKey)) groupHeads.set(row.groupKey, row)
  }

  const sortedGroupKeys = [...groupHeads.keys()].sort((a, b) => {
    const ra = groupHeads.get(a)!
    const rb = groupHeads.get(b)!
    const va = ra[field] ?? ra.groupKey
    const vb = rb[field] ?? rb.groupKey
    if (typeof va === 'string' && typeof vb === 'string') {
      return sortDir * va.localeCompare(vb)
    }
    return sortDir * ((va as number) - (vb as number))
  })

  const rows: AdoTableRow[] = []
  for (const gk of sortedGroupKeys) {
    const groupRows = mapped.filter(r => r.groupKey === gk).sort((a, b) => a.id - b.id)
    rows.push(...groupRows)
  }

  const counts = new Map<number, number>()
  for (const row of rows) {
    counts.set(row.groupKey, (counts.get(row.groupKey) ?? 0) + 1)
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
}
