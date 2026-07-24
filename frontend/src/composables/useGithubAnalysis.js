import { ref } from 'vue'
import { api } from '@/api/index.js'

// Module-scope shared state
const repos = ref([])
const currentRepo = ref(null)
const loading = ref(false)
const error = ref(null)
const phase = ref('idle')
const progress = ref(0)
const progressMessage = ref('')
const ACTIVE_TASK_KEY = 'owlmock.github.activeTaskId'

function loadActiveTaskId() {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(ACTIVE_TASK_KEY)
}

const activeTaskId = ref(loadActiveTaskId())

let eventSource = null

function closeSSE() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

function setActiveTaskId(taskId) {
  activeTaskId.value = taskId || null
  if (typeof window === 'undefined') return
  if (taskId) {
    window.localStorage.setItem(ACTIVE_TASK_KEY, taskId)
  } else {
    window.localStorage.removeItem(ACTIVE_TASK_KEY)
  }
}

function resetProgress() {
  phase.value = 'idle'
  progress.value = 0
  progressMessage.value = ''
  setActiveTaskId(null)
}

function connectSSE(taskId) {
  return new Promise((resolve, reject) => {
    closeSSE()
    const url = api.getTaskStreamUrl(taskId)
    const es = new EventSource(url)
    eventSource = es

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.progress != null) progress.value = data.progress
        if (data.message && data.message !== 'keepalive') {
          progressMessage.value = data.message
        }

        if (data.status === 'completed' || data.status === 'done') {
          closeSSE()
          resolve(data)
        } else if (data.status === 'failed') {
          closeSSE()
          reject(new Error(data.message || '分析失败'))
        }
      } catch {
        // ignore parse errors (keepalive etc.)
      }
    }

    es.onerror = async () => {
      closeSSE()
      try {
        const task = await api.getTaskStatus(taskId)
        if (task.progress != null) progress.value = task.progress
        if (task.message) progressMessage.value = task.message
        if (task.status === 'completed' || task.status === 'done') {
          resolve(task)
          return
        }
        if (task.status === 'failed') {
          reject(new Error(task.error || task.message || '分析失败'))
          return
        }
        const analysis = await api.getGithubRepo(taskId)
        if (analysis?.url && ['pending', 'running'].includes(analysis.status)) {
          await api.analyzeGithub(analysis.url)
        }
        setTimeout(() => {
          connectSSE(taskId).then(resolve).catch(reject)
        }, 1500)
      } catch {
        setTimeout(() => {
          connectSSE(taskId).then(resolve).catch(reject)
        }, 2500)
      }
    }
  })
}

async function withLoading(fn) {
  loading.value = true
  error.value = null
  try {
    return await fn()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

export function useGithubAnalysis() {
  function fetchRepos() {
    return withLoading(async () => {
      repos.value = await api.getGithubRepos()
    })
  }

  function fetchRepo(id) {
    return withLoading(async () => {
      if (currentRepo.value?.id !== id) currentRepo.value = null
      currentRepo.value = await api.getGithubRepo(id)
    })
  }

  function fetchDeepAnalysis(id) {
    return fetchRepo(id)
  }

  function deleteRepo(id) {
    return withLoading(async () => {
      await api.deleteGithubRepo(id)
      repos.value = repos.value.filter((repo) => repo.id !== id)
      if (currentRepo.value?.id === id) {
        currentRepo.value = null
      }
    })
  }

  async function analyzeNewRepo(url) {
    error.value = null
    closeSSE()

    // Phase 1: Submit
    phase.value = 'submitting'
    progress.value = 0
    progressMessage.value = '正在提交分析请求...'

    let result
    try {
      result = await api.analyzeGithub(url)
    } catch (e) {
      phase.value = 'error'
      error.value = e.message
      return null
    }

    const taskId = result.id || result.task_id
    setActiveTaskId(taskId)

    // Cached result — already done
    if (result.status === 'done') {
      phase.value = 'fetching'
      progress.value = 1
      progressMessage.value = '加载缓存结果...'
      try {
        currentRepo.value = await api.getGithubRepo(taskId)
        await fetchRepos()
        phase.value = 'done'
        resetProgress()
        return { id: taskId }
      } catch (e) {
        phase.value = 'error'
        error.value = e.message
        return null
      }
    }

    // Phase 2: Analyzing via SSE (runs in background)
    phase.value = 'analyzing'
    progress.value = 0.05
    progressMessage.value = '正在初始化分析...'

    connectSSE(taskId)
      .then(async () => {
        phase.value = 'fetching'
        progressMessage.value = '正在加载分析结果...'
        try {
          currentRepo.value = await api.getGithubRepo(taskId)
          await fetchRepos()
          phase.value = 'done'
        } catch (e) {
          phase.value = 'error'
          error.value = e.message
        } finally {
          setActiveTaskId(null)
        }
      })
      .catch((e) => {
        phase.value = 'error'
        error.value = e.message
        setActiveTaskId(null)
      })

    // Return immediately so caller can navigate
    return { id: taskId }
  }

  async function reconnectTask(taskId) {
    if (!taskId) return false
    setActiveTaskId(taskId)

    try {
      const task = await api.getTaskStatus(taskId)
      if (task.status === 'completed' || task.status === 'done') {
        phase.value = 'fetching'
        currentRepo.value = await api.getGithubRepo(taskId)
        phase.value = 'done'
        setActiveTaskId(null)
        return true
      }
      if (task.status === 'failed') {
        phase.value = 'error'
        error.value = task.error || '分析失败'
        setActiveTaskId(null)
        return false
      }

      // Still running — reconnect SSE
      phase.value = 'analyzing'
      progress.value = task.progress || 0
      progressMessage.value = '正在继续分析...'

      connectSSE(taskId)
        .then(async () => {
          phase.value = 'fetching'
          try {
            currentRepo.value = await api.getGithubRepo(taskId)
            await fetchRepos()
            phase.value = 'done'
          } catch (e) {
            phase.value = 'error'
            error.value = e.message
          } finally {
            setActiveTaskId(null)
          }
        })
        .catch((e) => {
          phase.value = 'error'
          error.value = e.message
          setActiveTaskId(null)
        })

      return true
    } catch {
      setActiveTaskId(null)
      return false
    }
  }

  return {
    repos,
    currentRepo,
    loading,
    error,
    phase,
    progress,
    progressMessage,
    activeTaskId,
    fetchRepos,
    fetchRepo,
    fetchDeepAnalysis,
    deleteRepo,
    analyzeNewRepo,
    reconnectTask,
    closeSSE,
  }
}
