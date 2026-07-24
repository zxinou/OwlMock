/**
 * API service layer
 * GitHub analysis uses real backend; other endpoints use mock adapter.
 */

import { mockAdapter } from './mock.js'

// Mock adapter for non-GitHub endpoints
async function mockRequest(path, options = {}) {
  await new Promise((r) => setTimeout(r, 2000))
  return mockAdapter(path, options)
}

// Real API call to FastAPI backend
async function realRequest(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const rawDetail = typeof body?.detail === 'string' ? body.detail : ''
    const looksTechnical = /LLM|invalid JSON|traceback|stack trace|API error/i.test(rawDetail)
    const detail = looksTechnical || !rawDetail
      ? (res.status >= 500 ? '分析服务暂时没有完成，请稍后重试' : '请求没有完成，请检查输入后重试')
      : rawDetail
    throw new Error(detail)
  }
  if (res.status === 204) {
    return null
  }
  return res.json()
}

export const api = {
  // GitHub analysis (real backend)
  analyzeGithub(url) {
    return realRequest('/analysis', {
      method: 'POST',
      body: JSON.stringify({ repo_url: url }),
    })
  },

  getGithubRepos() {
    return realRequest('/analysis')
  },

  getGithubRepo(id) {
    return realRequest(`/analysis/${id}`)
  },

  getGithubDeep(id) {
    return realRequest(`/analysis/${id}`)
  },

  deleteGithubRepo(id) {
    return realRequest(`/analysis/${id}`, { method: 'DELETE' })
  },

  // Task progress (real backend)
  getTaskStatus(taskId) {
    return realRequest(`/tasks/${taskId}`)
  },

  getTaskStreamUrl(taskId) {
    return `/api/tasks/${taskId}/stream`
  },

  // JD analysis (real backend)
  analyzeJd(text) {
    return realRequest('/jd/analyze', {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
  },

  submitJd(text, userId = 'default') {
    return realRequest('/jd/analyses', {
      method: 'POST',
      body: JSON.stringify({ text, user_id: userId }),
    })
  },

  async analyzeJdImage(file, userId = 'default') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userId)
    const res = await fetch('/api/jd/analyze-image', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Analyze failed: ${res.status}` }))
      throw new Error(err.detail || `Analyze failed: ${res.status}`)
    }
    return res.json()
  },

  async submitJdImage(file, userId = 'default') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userId)
    const res = await fetch('/api/jd/analyses/image', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Analyze failed: ${res.status}` }))
      throw new Error(err.detail || `Analyze failed: ${res.status}`)
    }
    return res.json()
  },

  getJdAnalysis(id) {
    return realRequest(`/jd/analyses/${id}`)
  },

  resumeJdAnalysis(id) {
    return realRequest(`/jd/analyses/${id}/resume`, { method: 'POST' })
  },

  getJdAnalyses(userId = 'default') {
    return realRequest(`/jd/analyses?user_id=${encodeURIComponent(userId)}`)
  },

  deleteJdAnalysis(id) {
    return realRequest(`/jd/analyses/${id}`, { method: 'DELETE' })
  },

  deleteJdAnalyses(ids, userId = 'default') {
    return realRequest('/jd/analyses/batch', {
      method: 'DELETE',
      body: JSON.stringify({ ids, user_id: userId }),
    })
  },

  // Resume CRUD (real backend)
  getResumes(userId = 'default') {
    return realRequest(`/resumes?user_id=${encodeURIComponent(userId)}`)
  },

  getResume(resumeId) {
    return realRequest(`/resumes/${resumeId}`)
  },

  async uploadResume(file, userId = 'default') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', userId)
    const res = await fetch('/api/resumes/upload', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `Upload failed: ${res.status}` }))
      throw new Error(err.detail || `Upload failed: ${res.status}`)
    }
    return res.json()
  },

  deleteResume(resumeId) {
    return realRequest(`/resumes/${resumeId}`, { method: 'DELETE' })
  },

  analyzeResume(resumeId, force = false) {
    return realRequest(`/resumes/${resumeId}/analyze?force=${force}`, {
      method: 'POST',
    })
  },

  // Resume to JD matching (real backend)
  submitResumeMatch({ resumeId, jobDescription, userId = 'default' }) {
    return realRequest('/resume-matches', {
      method: 'POST',
      body: JSON.stringify({
        resume_id: resumeId,
        job_description: jobDescription,
        user_id: userId,
      }),
    })
  },

  submitResumeMatchBatch({ resumeId, jdAnalysisIds, userId = 'default' }) {
    return realRequest('/resume-matches/batch', {
      method: 'POST',
      body: JSON.stringify({
        resume_id: resumeId,
        jd_analysis_ids: jdAnalysisIds,
        user_id: userId,
      }),
    })
  },

  getResumeMatchBatch(batchId, userId = 'default') {
    return realRequest(`/resume-match-batches/${batchId}?user_id=${encodeURIComponent(userId)}`)
  },

  getResumeMatches(userId = 'default') {
    return realRequest(`/resume-matches?user_id=${encodeURIComponent(userId)}`)
  },

  getResumeMatch(matchId) {
    return realRequest(`/resume-matches/${matchId}`)
  },

  resumeResumeMatch(matchId) {
    return realRequest(`/resume-matches/${matchId}/resume`, { method: 'POST' })
  },

  deleteResumeMatch(matchId) {
    return realRequest(`/resume-matches/${matchId}`, { method: 'DELETE' })
  },

  deleteResumeMatches(ids, userId = 'default') {
    return realRequest('/resume-matches/batch', {
      method: 'DELETE',
      body: JSON.stringify({ ids, user_id: userId }),
    })
  },

  // Interview sessions (real backend)
  createSession({ profileId, mode = 'text', resumeId = null, githubRepoIds = [] }) {
    return realRequest('/sessions', {
      method: 'POST',
      body: JSON.stringify({
        profile_id: profileId,
        mode,
        resume_id: resumeId,
        github_repo_ids: githubRepoIds,
      }),
    })
  },

  getSessions({ userId = 'default', status = null, profileId = null } = {}) {
    const params = new URLSearchParams({ user_id: userId })
    if (status) params.set('status', status)
    if (profileId) params.set('profile_id', profileId)
    return realRequest(`/sessions?${params.toString()}`)
  },

  getSession(sessionId) {
    return realRequest(`/sessions/${sessionId}`)
  },

  deleteSession(sessionId) {
    return realRequest(`/sessions/${sessionId}`, { method: 'DELETE' })
  },

  getSessionEvents(sessionId) {
    return realRequest(`/sessions/${sessionId}/events`)
  },

  sendSSEMessage(sessionId, text) {
    return realRequest(`/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    })
  },

  streamEvents(sessionId) {
    return new EventSource(`/api/sessions/${sessionId}/stream`)
  },

  finalizeSession(sessionId) {
    return realRequest(`/sessions/${sessionId}/finalize`, {
      method: 'POST',
    })
  },

  getVoiceWebSocketUrl(sessionId, { profileId, userId = 'default', mode = 'voice' } = {}) {
    const params = new URLSearchParams({
      profile: profileId,
      user_id: userId,
      mode,
    })
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/voice/${sessionId}?${params.toString()}`
  },
}
