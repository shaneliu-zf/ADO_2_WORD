export function parseIds(text: string): number[] {
  const ids: number[] = []
  const seen = new Set<number>()
  for (const match of text.matchAll(/\d+/g)) {
    const id = Number(match[0])
    if (!id || seen.has(id)) continue
    seen.add(id)
    ids.push(id)
  }
  return ids
}
