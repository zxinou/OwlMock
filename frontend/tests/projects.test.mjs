import assert from 'node:assert/strict'
import test from 'node:test'
import { createServer } from 'vite'

test('project store loads, creates a JD draft, recovers detail, and archives', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createProjectsStore } = await vite.ssrLoadModule('/src/stores/projects.js')

  const calls = []
  const project = { id: 'project-1', title: 'Senior Frontend Engineer' }
  const client = {
    async getProjects() {
      calls.push('list')
      return { items: [project], total: 1 }
    },
    async createProject(input) {
      calls.push(['create', input])
      return project
    },
    async submitProjectJd(projectId, text) {
      calls.push(['jd', projectId, text])
      return { task_id: 'jd-task-1', status: 'pending' }
    },
    async getProject(projectId) {
      calls.push(['detail', projectId])
      return { ...project, steps: [{ key: 'job', status: 'in_progress' }] }
    },
    async updateProject(projectId, input) {
      calls.push(['update', projectId, input])
      return { ...project, archived_at: '2026-08-05T00:00:00' }
    },
  }
  const projects = createProjectsStore(client)

  await projects.load()
  assert.equal(projects.total, 1)

  const created = await projects.createFromText({
    title: 'Senior Frontend Engineer',
    company: 'Owl Labs',
    location: 'Remote',
    jdText: 'Build reliable and accessible Vue applications for global users.',
  })
  assert.equal(created.taskId, 'jd-task-1')
  assert.equal(created.project.id, 'project-1')

  await projects.loadProject('project-1')
  assert.equal(projects.current.steps[0].status, 'in_progress')

  await projects.archive('project-1')
  assert.equal(projects.items.length, 0)
  assert.equal(calls.filter((call) => Array.isArray(call) && call[0] === 'jd').length, 1)
})

test('project store exposes actionable errors and clears stale project state', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createProjectsStore } = await vite.ssrLoadModule('/src/stores/projects.js')

  const client = {
    async getProject() {
      const error = new Error('Project not found')
      error.code = 'not_found'
      throw error
    },
  }
  const projects = createProjectsStore(client)
  projects.current = { id: 'stale' }

  await assert.rejects(projects.loadProject('missing'))
  assert.equal(projects.current, null)
  assert.equal(projects.error, 'Project not found')

  const listClient = {
    async getProjects() {
      throw new Error('Unable to load archived projects')
    },
  }
  const listStore = createProjectsStore(listClient)
  listStore.items = [{ id: 'stale-active' }]
  listStore.total = 1
  await assert.rejects(listStore.load({ archived: true }))
  assert.deepEqual(listStore.items, [])
  assert.equal(listStore.total, 0)
})

test('failed JD submission preserves one recoverable project draft for retry', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createProjectsStore } = await vite.ssrLoadModule('/src/stores/projects.js')

  let creates = 0
  let submissions = 0
  const client = {
    async createProject(input) {
      creates += 1
      return { id: 'draft-1', ...input }
    },
    async submitProjectJd(projectId) {
      submissions += 1
      if (submissions === 1) throw new Error('Provider temporarily unavailable')
      return { task_id: 'retry-task', project_id: projectId }
    },
  }
  const projects = createProjectsStore(client)

  await assert.rejects(
    projects.createFromText({ title: 'Role', company: null, location: null, jdText: 'A complete job description for testing.' }),
    (error) => error.projectId === 'draft-1',
  )
  const retried = await projects.submitJd('draft-1', { text: 'A complete job description for testing.' })

  assert.equal(retried.task_id, 'retry-task')
  assert.equal(creates, 1)
})

test('project store creates image drafts, starts resume matches, and creates project sessions', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createProjectsStore } = await vite.ssrLoadModule('/src/stores/projects.js')

  const calls = []
  const file = { name: 'job.png' }
  const client = {
    async createProject(input) {
      calls.push(['create', input])
      return { id: 'project-image', ...input }
    },
    async submitProjectJdImage(projectId, uploaded) {
      calls.push(['image', projectId, uploaded])
      return { task_id: 'jd-image-task', status: 'pending' }
    },
    async submitProjectResumeMatch(projectId, resumeId) {
      calls.push(['match', projectId, resumeId])
      return { task_id: 'match-task', status: 'pending' }
    },
    async createProjectSession(projectId, input) {
      calls.push(['session', projectId, input])
      return { id: 'session-1', status: 'active', ...input }
    },
  }
  const projects = createProjectsStore(client)

  const draft = await projects.createFromImage({
    title: 'Platform Engineer',
    company: 'Harbor',
    location: 'Hong Kong',
    file,
  })
  assert.equal(draft.taskId, 'jd-image-task')

  const match = await projects.startResumeMatch('project-image', 'resume-1')
  assert.equal(match.task_id, 'match-task')

  const session = await projects.startInterview('project-image', {
    profile_id: 'interviewer-technical',
    mode: 'text',
    github_repo_ids: [],
  })
  assert.equal(session.id, 'session-1')
  assert.deepEqual(calls.at(-1), [
    'session',
    'project-image',
    { profile_id: 'interviewer-technical', mode: 'text', github_repo_ids: [] },
  ])
})

test('workspace view model derives focus, next action, score, and interview history', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createWorkspaceViewModel } = await vite.ssrLoadModule(
    '/src/components/projects/workspaceViewModel.js',
  )

  const project = {
    id: 'project-1',
    title: 'Senior Frontend Engineer',
    company: 'Owl Labs',
    location: 'Remote',
    current_jd: {
      id: 'jd-1',
      status: 'completed',
      result: {
        job: { summary: 'Build accessible Vue applications.' },
        requirements: { must_have: ['Vue 3', 'Accessibility', 'Testing'] },
        interview: { focus: ['System design', 'Frontend performance'] },
      },
    },
    current_resume: { id: 'resume-1', file_name: 'resume.pdf' },
    latest_match: {
      id: 'match-1',
      score: 86,
      result: { gaps: [{ requirement: 'Web performance evidence' }] },
    },
    recent_sessions: [
      { id: 'session-1', mode: 'text', status: 'completed', turn_count: 5 },
    ],
    steps: [
      { key: 'job', status: 'completed' },
      { key: 'resume', status: 'completed' },
      { key: 'interview', status: 'completed' },
    ],
  }

  const view = createWorkspaceViewModel(project)
  assert.equal(view.score, 86)
  assert.equal(view.nextAction.key, 'interview')
  assert.equal(view.focusItems[0], 'System design')
  assert.equal(view.summary, 'Build accessible Vue applications.')
  assert.equal(view.interviews[0].id, 'session-1')

  const empty = createWorkspaceViewModel({})
  assert.equal(empty.score, null)
  assert.equal(empty.nextAction.key, 'interview')

  const archived = createWorkspaceViewModel({ archived_at: '2026-08-05T00:00:00', steps: [] })
  assert.equal(archived.readOnly, true)
})

test('project routes expose list, create, workspace, and recoverable task URLs', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { routes } = await vite.ssrLoadModule('/src/router/index.js')

  const byName = Object.fromEntries(routes.filter((route) => route.name).map((route) => [route.name, route]))
  assert.equal(byName.projects.path, '/projects')
  assert.equal(byName['project-create'].path, '/projects/new')
  assert.equal(byName['project-workspace'].path, '/projects/:projectId')
  assert.equal(byName['project-jd-task'].path, '/projects/:projectId/jd/tasks/:taskId')
  assert.equal(byName['project-resume-task'].path, '/projects/:projectId/resume/tasks/:taskId')
})

test('interview configuration creates a project-scoped session when project context exists', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createConfiguredSession } = await vite.ssrLoadModule('/src/composables/useInterviewConfig.js')

  const calls = []
  const client = {
    async updateProject(projectId, input) {
      calls.push(['update', projectId, input])
      return { id: projectId, current_resume_id: input.current_resume_id }
    },
    async createProjectSession(projectId, input) {
      calls.push([projectId, input])
      return { session_id: 'session-project' }
    },
    async createSession() {
      throw new Error('global session should not be used')
    },
  }
  const result = await createConfiguredSession(client, {
    projectId: 'project-1',
    profileId: 'interviewer-technical',
    mode: 'voice',
    resumeId: 'resume-1',
    githubRepoIds: ['repo-1'],
  })

  assert.equal(result.session_id, 'session-project')
  assert.deepEqual(calls[0], ['update', 'project-1', { current_resume_id: 'resume-1' }])
  assert.deepEqual(calls[1], ['project-1', {
    profile_id: 'interviewer-technical',
    mode: 'voice',
    github_repo_ids: ['repo-1'],
  }])
})
