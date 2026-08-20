import axios from 'axios'
import type { AdoItem, AppConfig, Report, Group, PipelineSession } from '@/types'

const http = axios.create({ baseURL: '/' })

function unwrapApiError(error: unknown): never {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { message?: string; error?: string } | undefined
    const message = data?.message || data?.error || error.message
    throw new Error(message)
  }
  throw error
}

// ── Session / items ────────────────────────────────────────────────────────────

export function fetchConfig(): Promise<AppConfig> {
  return http.get<AppConfig>('/api/config').then(r => r.data)
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
  currentStep?: number
  reachedStep?: number
}): Promise<PipelineSession> {
  return http.put<PipelineSession>('/api/session', body).then(r => r.data)
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

export function updateItem(id: number, report: Report): Promise<{ ok: boolean }> {
  return http.put<{ ok: boolean }>(`/api/items/${id}`, report).then(r => r.data).catch(unwrapApiError)
}

export function uploadItemImage(id: number, file: File): Promise<{ src: string }> {
  const body = new FormData()
  body.append('file', file)
  return http.post<{ src: string }>(`/api/items/${id}/images`, body).then(r => r.data)
}

export function deleteItems(ids: number[]): Promise<{ deleted: number[] }> {
  return http
    .delete<{ deleted: number[] }>('/api/items', { data: { ids } })
    .then(r => r.data)
}

export function fetchGroups(): Promise<Group[]> {
  return http.get<Group[]>('/api/groups').then(r => r.data)
}

// ── Pipeline ───────────────────────────────────────────────────────────────────

/** Run a pipeline script; returns a native Response for SSE streaming. */
export function runPipeline(script: string, ids: number[], workingIds?: number[]): Promise<Response> {
  return fetch('/api/pipeline/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script, ids, workingIds }),
  })
}

export function abortPipeline(): Promise<{ ok: boolean; message: string }> {
  return http.post<{ ok: boolean; message: string }>('/api/pipeline/abort').then(r => r.data)
}

export function downloadWord(): void {
  window.location.href = '/api/pipeline/download'
}
