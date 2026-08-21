export type SseEvent = {
  type: string
  line?: string
  message?: string
  currentStep?: number
  reachedStep?: number
  ids?: number[]
  listedIds?: number[]
  docx?: string
}

export async function readSseStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const dataLine = part.split('\n').find(l => l.startsWith('data: '))
      if (!dataLine) continue
      try {
        onEvent(JSON.parse(dataLine.slice(6)) as SseEvent)
      } catch {
        // ignore parse errors
      }
    }
  }
}
