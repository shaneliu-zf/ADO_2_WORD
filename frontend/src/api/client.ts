import axios from 'axios'
import type { AdoItem, AppConfig, ConfigStatus, Report, Group, PipelineSession } from '@/types'
import { errorMessage } from '@/utils/apiError'

const http = axios.create({ baseURL: '/' })

http.interceptors.response.use(
  response => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const data = error.response?.data as { message?: string; error?: string } | undefined
      return Promise.reject(new Error(data?.message || data?.error || error.message))
    }
    return Promise.reject(error instanceof Error ? error : new Error(errorMessage(error)))
  },
)

// ── Session / items ────────────────────────────────────────────────────────────

export function fetchConfig(): Promise<AppConfig> {
  return http.get<AppConfig>('/api/config').then(r => r.data)
}

export function fetchConfigStatus(): Promise<ConfigStatus> {
  return http.get<ConfigStatus>('/api/config/status').then(r => r.data)
}

export function updateConfig(body: AppConfig): Promise<AppConfig> {
  return http.put<AppConfig>('/api/config', body).then(r => r.data)
}

export function fetchSession(): Promise<PipelineSession> {
  return http.get<PipelineSession>('/api/session').then(r => r.data)
}

export function updateSession(body: {
  ids?: number[]
  listed?: boolean
  restoreListed?: boolean
  selectedIds?: number[]
  currentStep?: number
  reachedStep?: number
}): Promise<PipelineSession> {
  return http.put<PipelineSession>('/api/session', body).then(r => r.data)
}

export function fetchAdoIds(): Promise<number[]> {
  return http.get<{ ids: number[] }>('/api/ado/ids').then(r => r.data.ids)
}

export function loadItemSummaries(ids: number[]): Promise<{ ok: boolean; count: number }> {
  return http.post<{ ok: boolean; count: number }>('/api/items/summaries', { ids }).then(r => r.data)
}

export function fetchItems(): Promise<AdoItem[]> {
  return http.get<AdoItem[]>('/api/items').then(r => r.data)
}

export function fetchItemJson(id: number): Promise<Report> {
  return http.get<Report>(`/api/items/${id}`).then(r => r.data)
}

export function fetchItemHtml(id: number): Promise<string> {
  return http.get<string>(`/api/items/${id}/html`, { responseType: 'text' }).then(r => r.data)
}

export function refreshWorkItem(id: number): Promise<{ ok: boolean }> {
  return http.post<{ ok: boolean }>(`/api/items/${id}/refresh`).then(r => r.data)
}

export function regenerateReport(id: number): Promise<Report> {
  return http.post<Report>(`/api/items/${id}/regenerate-report`).then(r => r.data)
}

export function updateItem(id: number, report: Report): Promise<{ ok: boolean }> {
  return http.put<{ ok: boolean }>(`/api/items/${id}`, report).then(r => r.data)
}

export function uploadItemImage(id: number, file: File): Promise<{ src: string }> {
  const body = new FormData()
  body.append('file', file)
  return http.post<{ src: string }>(`/api/items/${id}/images`, body).then(r => r.data)
}

export function deleteItems(ids: number[]): Promise<{ deleted: number[]; ok: boolean }> {
  return http.post<{ deleted: number[]; ok: boolean }>('/api/items/delete', { ids }).then(r => r.data)
}

export function fetchGroups(): Promise<Group[]> {
  return http.get<Group[]>('/api/groups').then(r => r.data)
}

export function clearGroups(ids: number[]): Promise<{ ok: boolean }> {
  return http.delete<{ ok: boolean }>('/api/groups', { data: { ids } }).then(r => r.data)
}

// ── Pipeline ───────────────────────────────────────────────────────────────────

/** Run a pipeline script; returns a native Response for SSE streaming. */
export function runPipeline(script: string, ids: number[]): Promise<Response> {
  return fetch('/api/pipeline/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script, ids }),
  })
}

export function abortPipeline(): Promise<{ ok: boolean; message: string }> {
  return http.post<{ ok: boolean; message: string }>('/api/pipeline/abort').then(r => r.data)
}

function filenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (utf8?.[1]) return decodeURIComponent(utf8[1])
  const quoted = /filename="([^"]+)"/i.exec(header)
  if (quoted?.[1]) return quoted[1]
  const plain = /filename=([^;]+)/i.exec(header)
  return plain?.[1]?.trim() || fallback
}

/** 下載剛產出的 Word；後端傳完會刪檔。 */
export async function downloadPipelineWord(filename?: string): Promise<string> {
  const query = filename ? `?file=${encodeURIComponent(filename)}` : ''
  const response = await fetch(`/api/pipeline/download${query}`)
  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const data = (await response.json()) as { message?: string; error?: string }
      message = data.message || data.error || message
    } catch {
      // 不是 JSON 錯誤時沿用 HTTP 狀態
    }
    throw new Error(message)
  }
  const blob = await response.blob()
  const name = filenameFromDisposition(response.headers.get('Content-Disposition'), filename || 'report.docx')
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
  return name
}
