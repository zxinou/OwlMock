export class ApiError extends Error {
  constructor(message, { status = 0, code = 'request_failed', requestId = null, detail = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.detail = detail
  }
}

let unauthorizedHandler = null

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = typeof handler === 'function' ? handler : null
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const isForm = options.body instanceof FormData
  if (options.body && !isForm && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  let response
  try {
    response = await fetch(`/api${path}`, {
      credentials: 'same-origin',
      ...options,
      headers,
    })
  } catch {
    throw new ApiError('无法连接到 OwlMock 服务，请检查网络后重试。', {
      code: 'network_error',
    })
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const message = body.message
      || (typeof body.detail === 'string' ? body.detail : null)
      || (response.status >= 500
        ? '服务暂时无法完成请求，请稍后重试。'
        : '请求未完成，请检查输入后重试。')
    const error = new ApiError(message, {
      status: response.status,
      code: body.code || 'request_failed',
      requestId: body.request_id || response.headers?.get?.('X-Request-ID') || null,
      detail: body.detail,
    })
    if (response.status === 401 && unauthorizedHandler) {
      try {
        await unauthorizedHandler(error)
      } catch {
        // Navigation failures must not replace the original API error.
      }
    }
    throw error
  }
  if (response.status === 204) return null
  return response.json()
}

function json(method, body) {
  return { method, body: JSON.stringify(body) }
}

function upload(path, file) {
  const body = new FormData()
  body.append('file', file)
  return request(path, { method: 'POST', body })
}

export const api = {
  login(password) {
    return request('/auth/login', json('POST', { password }))
  },
  getAuthSession() {
    return request('/auth/session')
  },
  logout() {
    return request('/auth/logout', { method: 'POST' })
  },
  getSystemStatus() {
    return request('/system/status')
  },

  getProjects({ archived = false, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams({
      archived: String(archived),
      limit: String(limit),
      offset: String(offset),
    })
    return request(`/projects?${params}`)
  },
  getProject(projectId) {
    return request(`/projects/${projectId}`)
  },
  createProject(input) {
    return request('/projects', json('POST', input))
  },
  updateProject(projectId, input) {
    return request(`/projects/${projectId}`, json('PATCH', input))
  },
  submitProjectJd(projectId, text) {
    return request(`/projects/${projectId}/jd-analyses`, json('POST', { text }))
  },
  submitProjectJdImage(projectId, file) {
    return upload(`/projects/${projectId}/jd-analyses/image`, file)
  },
  submitProjectResumeMatch(projectId, resumeId) {
    return request(
      `/projects/${projectId}/resume-matches`,
      json('POST', { resume_id: resumeId }),
    )
  },
  createProjectSession(projectId, input) {
    return request(`/projects/${projectId}/sessions`, json('POST', input))
  },

  analyzeGithub(url) {
    return request('/analysis', json('POST', { repo_url: url }))
  },
  getGithubRepos() {
    return request('/analysis')
  },
  getGithubRepo(id) {
    return request(`/analysis/${id}`)
  },
  getGithubDeep(id) {
    return request(`/analysis/${id}`)
  },
  deleteGithubRepo(id) {
    return request(`/analysis/${id}`, { method: 'DELETE' })
  },

  getTaskStatus(taskId) {
    return request(`/tasks/${taskId}`)
  },
  getTaskStreamUrl(taskId) {
    return `/api/tasks/${taskId}/stream`
  },

  analyzeJd(text) {
    return request('/jd/analyze', json('POST', { text }))
  },
  submitJd(text) {
    return request('/jd/analyses', json('POST', { text }))
  },
  analyzeJdImage(file) {
    return upload('/jd/analyze-image', file)
  },
  submitJdImage(file) {
    return upload('/jd/analyses/image', file)
  },
  getJdAnalysis(id) {
    return request(`/jd/analyses/${id}`)
  },
  resumeJdAnalysis(id) {
    return request(`/jd/analyses/${id}/resume`, { method: 'POST' })
  },
  getJdAnalyses() {
    return request('/jd/analyses')
  },
  deleteJdAnalysis(id) {
    return request(`/jd/analyses/${id}`, { method: 'DELETE' })
  },
  deleteJdAnalyses(ids) {
    return request('/jd/analyses/batch', json('DELETE', { ids }))
  },

  getResumes() {
    return request('/resumes')
  },
  getResume(resumeId) {
    return request(`/resumes/${resumeId}`)
  },
  uploadResume(file) {
    return upload('/resumes/upload', file)
  },
  deleteResume(resumeId) {
    return request(`/resumes/${resumeId}`, { method: 'DELETE' })
  },
  analyzeResume(resumeId, force = false) {
    return request(`/resumes/${resumeId}/analyze?force=${force}`, { method: 'POST' })
  },

  submitResumeMatch({ resumeId, jobDescription }) {
    return request('/resume-matches', json('POST', {
      resume_id: resumeId,
      job_description: jobDescription,
    }))
  },
  submitResumeMatchBatch({ resumeId, jdAnalysisIds }) {
    return request('/resume-matches/batch', json('POST', {
      resume_id: resumeId,
      jd_analysis_ids: jdAnalysisIds,
    }))
  },
  getResumeMatchBatch(batchId) {
    return request(`/resume-match-batches/${batchId}`)
  },
  getResumeMatches() {
    return request('/resume-matches')
  },
  getResumeMatch(matchId) {
    return request(`/resume-matches/${matchId}`)
  },
  resumeResumeMatch(matchId) {
    return request(`/resume-matches/${matchId}/resume`, { method: 'POST' })
  },
  deleteResumeMatch(matchId) {
    return request(`/resume-matches/${matchId}`, { method: 'DELETE' })
  },
  deleteResumeMatches(ids) {
    return request('/resume-matches/batch', json('DELETE', { ids }))
  },

  createSession({ profileId, mode = 'text', resumeId = null, githubRepoIds = [] }) {
    return request('/sessions', json('POST', {
      profile_id: profileId,
      mode,
      resume_id: resumeId,
      github_repo_ids: githubRepoIds,
    }))
  },
  getSessions({ status = null, profileId = null } = {}) {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (profileId) params.set('profile_id', profileId)
    const query = params.size ? `?${params}` : ''
    return request(`/sessions${query}`)
  },
  getSession(sessionId) {
    return request(`/sessions/${sessionId}`)
  },
  deleteSession(sessionId) {
    return request(`/sessions/${sessionId}`, { method: 'DELETE' })
  },
  getSessionEvents(sessionId) {
    return request(`/sessions/${sessionId}/events`)
  },
  sendSSEMessage(sessionId, text) {
    return request(`/sessions/${sessionId}/messages`, json('POST', { text }))
  },
  streamEvents(sessionId) {
    return new EventSource(`/api/sessions/${sessionId}/stream`)
  },
  finalizeSession(sessionId) {
    return request(`/sessions/${sessionId}/finalize`, { method: 'POST' })
  },
  getVoiceWebSocketUrl(sessionId, { profileId, mode = 'voice' } = {}) {
    const params = new URLSearchParams({ profile: profileId, mode })
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/voice/${sessionId}?${params}`
  },
}
