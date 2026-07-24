import { onBeforeUnmount, ref } from 'vue'
import { api } from '@/api/index.js'

const POLL_INTERVAL_MS = 1800

export function useResumeMatchTask() {
  const match = ref(null)
  const status = ref('pending')
  const stage = ref('waiting')
  const progress = ref(0)
  const error = ref(null)
  const loading = ref(true)

  let taskId = null
  let eventSource = null
  let pollTimer = null
  let stopped = false

  function applyState(data) {
    if (!data) return
    match.value = data
    status.value = data.status || status.value
    stage.value = data.stage || stage.value
    if (data.progress != null) progress.value = data.progress
    error.value = data.error || null
  }

  function clearConnections() {
    eventSource?.close()
    eventSource = null
    if (pollTimer) clearTimeout(pollTimer)
    pollTimer = null
  }

  function isTerminal() {
    return ['completed', 'failed', 'cancelled'].includes(status.value)
  }

  async function refresh() {
    if (!taskId || stopped) return null
    const data = await api.getResumeMatch(taskId)
    applyState(data)
    loading.value = false
    if (isTerminal()) clearConnections()
    return data
  }

  function schedulePoll(delay = POLL_INTERVAL_MS) {
    if (stopped || isTerminal() || pollTimer) return
    pollTimer = setTimeout(async () => {
      pollTimer = null
      try {
        await refresh()
      } catch (e) {
        error.value = e.message
      }
      schedulePoll()
    }, delay)
  }

  function connectSse() {
    if (!taskId || stopped || isTerminal() || eventSource) return
    const source = new EventSource(api.getTaskStreamUrl(taskId))
    eventSource = source
    source.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data)
        status.value = data.status || status.value
        stage.value = data.stage || data.data?.stage || stage.value
        if (data.progress != null) progress.value = data.progress
        if (data.status === 'failed') error.value = data.message || '匹配分析失败'
        if (['completed', 'failed', 'cancelled'].includes(data.status)) await refresh()
      } catch {
        // Persisted polling remains authoritative when a keepalive is malformed.
      }
    }
    source.onerror = () => {
      source.close()
      if (eventSource === source) eventSource = null
      schedulePoll(250)
    }
  }

  async function start(id) {
    stop()
    stopped = false
    taskId = id
    loading.value = true
    error.value = null
    try {
      await refresh()
      if (!isTerminal()) {
        await api.resumeResumeMatch(taskId)
        connectSse()
        schedulePoll()
      }
    } catch (e) {
      loading.value = false
      error.value = e.message || '无法恢复匹配任务'
      schedulePoll()
    }
  }

  function stop() {
    stopped = true
    clearConnections()
  }

  onBeforeUnmount(stop)

  return { match, status, stage, progress, error, loading, start, refresh, stop }
}
