import { defineStore } from 'pinia'
import { ref } from 'vue'
import { runPipeline, abortPipeline, fetchSession, updateSession } from '@/api/client'
import { useItemsStore } from './items'
import type { PipelineSession } from '@/types'

export const STEP_DEFS = [
  { index: 1, script: 'fetch', label: '下載資料', hint: '下載描述、圖片與變動歷史' },
  { index: 2, script: 'group', label: '關聯分組', hint: 'Related Work Item 合併成一組' },
  { index: 3, script: 'report', label: '產生報告', hint: '整理成測試報告 JSON（會扣 Bobcoins）' },
  { index: 4, script: 'word', label: '合併成Word', hint: '填進範本，寫出 report_*.docx' },
] as const
const LAST_STEP = 4

function stepLabel(index: number): string {
  return STEP_DEFS.find(s => s.index === index)?.label ?? ''
}

// 從 log 解析各步驟進度的 pattern
const TOTAL_FETCH_RE = /抓取 ADO JSON（(\d+) 筆）/
const DONE_FETCH_RE = /^完成 Work Item \d/
const TOTAL_REPORT_RE = /共 (\d+) 組，開始處理/
const DONE_REPORT_RE = /^完成分析 Work Item /

export const usePipelineStore = defineStore('pipeline', () => {
  const currentStep = ref(1)
  const reachedStep = ref(0)
  const isRunning = ref(false)
  const runningStep = ref<number | null>(null)
  const logs = ref<string[]>([])
  const showLog = ref(false)
  const status = ref('從下載資料開始，每次只處理目前勾選的項目。')
  const statusKind = ref<'info' | 'error' | ''>('')
  // 當前執行步驟的進度 0-100，null 表示無法解析（indeterminate）
  const stepProgress = ref<number | null>(null)
  // 解析進度用的內部狀態
  let _progressTotal = 0
  let _progressDone = 0

  function setStatus(message: string, kind: 'info' | 'error' | '' = '') {
    status.value = message
    statusKind.value = kind
  }

  function applySession(session: PipelineSession) {
    currentStep.value = session.currentStep
    reachedStep.value = session.reachedStep
  }

  async function loadSession() {
    applySession(await fetchSession())
  }

  async function resetToStart() {
    const session = await updateSession({ currentStep: 1, reachedStep: 0 })
    applySession(session)
    logs.value = []
    showLog.value = false
    stepProgress.value = null
    setStatus('從下載資料開始，每次只處理目前勾選的項目。')
  }

  function _parseLogProgress(line: string, script: string): void {
    // 全流程 main 依序執行 fetch → group → report → word，
    // 每次進入新步驟時 total 會被重設
    const fetchTotal = TOTAL_FETCH_RE.exec(line)
    if (fetchTotal) {
      _progressTotal = parseInt(fetchTotal[1], 10)
      _progressDone = 0
      stepProgress.value = 0
      return
    }
    const reportTotal = TOTAL_REPORT_RE.exec(line)
    if (reportTotal) {
      _progressTotal = parseInt(reportTotal[1], 10)
      _progressDone = 0
      stepProgress.value = 0
      return
    }
    if (DONE_FETCH_RE.test(line) || DONE_REPORT_RE.test(line)) {
      if (_progressTotal > 0) {
        _progressDone = Math.min(_progressDone + 1, _progressTotal)
        stepProgress.value = Math.round((_progressDone / _progressTotal) * 100)
      }
    }
  }

  async function runScript(script: string, ids: number[], stepIndex: number, workingIds?: number[]): Promise<boolean> {
    if (isRunning.value) return false
    isRunning.value = true
    runningStep.value = stepIndex
    logs.value = []
    stepProgress.value = null
    _progressTotal = 0
    _progressDone = 0
    let failed = false
    const label =
      stepIndex === 0 ? '全流程自動完成' : stepIndex < 0 ? '列出 ID' : stepLabel(stepIndex)
    setStatus(`正在執行「${label}」…`)

    try {
      const response = await runPipeline(script, ids, workingIds)
      if (!response.ok || !response.body) {
        logs.value.push(`[Error] HTTP ${response.status}`)
        setStatus(`執行失敗：HTTP ${response.status}`, 'error')
        isRunning.value = false
        runningStep.value = null
        return false
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const dataLine = part
            .split('\n')
            .find(l => l.startsWith('data: '))
          if (!dataLine) continue
          try {
            const event = JSON.parse(dataLine.slice(6)) as {
              type: string
              line?: string
              message?: string
              currentStep?: number
              reachedStep?: number
              ids?: number[]
              listedIds?: number[]
            }
            if (event.type === 'log' && event.line != null) {
              logs.value.push(event.line)
              _parseLogProgress(event.line, script)
            } else if (event.type === 'error') {
              failed = true
              logs.value.push(`[Error] ${event.message ?? ''}`)
              setStatus(event.message ?? '執行失敗', 'error')
            } else if (event.type === 'done') {
              applySession({
                ids: event.ids ?? [],
                listedIds: event.listedIds ?? [],
                currentStep: event.currentStep ?? currentStep.value,
                reachedStep: event.reachedStep ?? reachedStep.value,
              })
              if (script === 'list_ids') {
                setStatus(`已列出 ${event.ids?.length ?? 0} 筆。`)
              } else if (reachedStep.value >= LAST_STEP) {
                setStatus('流程都跑完了。')
              } else {
                setStatus(`「${label}」完成。下一步：${stepLabel(currentStep.value)}`)
              }
            }
          } catch {
            // ignore parse errors
          }
        }
      }

      if (!failed) {
        await useItemsStore().refresh()
      }
    } catch (err) {
      failed = true
      logs.value.push(`[Network error] ${String(err)}`)
      setStatus(String(err), 'error')
    } finally {
      isRunning.value = false
      runningStep.value = null
      stepProgress.value = null
    }
    return !failed
  }

  async function abortScript() {
    try {
      const result = await abortPipeline()
      logs.value.push(`[中止] ${result.message}`)
      setStatus(result.message, 'error')
    } catch (err) {
      logs.value.push(`[中止失敗] ${String(err)}`)
    }
  }

  async function skipStep(stepIndex: number, ids: number[]) {
    const next = Math.min(stepIndex + 1, LAST_STEP)
    const session = await updateSession({
      ids,
      currentStep: next,
      reachedStep: Math.max(reachedStep.value, stepIndex),
    })
    applySession(session)
    await useItemsStore().refresh()
    if (reachedStep.value >= LAST_STEP) {
      setStatus('流程都跑完了。')
    } else {
      setStatus(`已略過「${stepLabel(stepIndex)}」。下一步：${stepLabel(currentStep.value)}`)
    }
  }

  async function prevStep() {
    if (currentStep.value <= 1) return
    const next = currentStep.value - 1
    // 退回到 next 步驟：reachedStep 也同步縮減，清除後面步驟的完成狀態與進度條
    const newReached = Math.min(reachedStep.value, next - 1)
    const session = await updateSession({ currentStep: next, reachedStep: newReached })
    applySession(session)
    setStatus(`回到「${stepLabel(currentStep.value)}」。再按執行會重跑這一步。`)
  }

  return {
    currentStep,
    reachedStep,
    isRunning,
    runningStep,
    logs,
    showLog,
    status,
    statusKind,
    stepProgress,
    applySession,
    loadSession,
    resetToStart,
    runScript,
    abortScript,
    prevStep,
    skipStep,
    setStatus,
  }
})
