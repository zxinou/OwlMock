import { reactive } from 'vue'

import { api } from '@/api/index.js'

export function createProjectsStore(client = api) {
  const store = reactive({
    items: [],
    total: 0,
    current: null,
    loading: false,
    saving: false,
    error: '',
    async load(options = {}) {
      store.loading = true
      store.error = ''
      store.items = []
      store.total = 0
      try {
        const payload = await client.getProjects(options)
        store.items = payload.items
        store.total = payload.total
        return payload
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.loading = false
      }
    },
    async loadProject(projectId) {
      store.loading = true
      store.error = ''
      store.current = null
      try {
        store.current = await client.getProject(projectId)
        return store.current
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.loading = false
      }
    },
    async createFromText({ title, company, location, jdText }) {
      store.saving = true
      store.error = ''
      try {
        const project = await client.createProject({ title, company, location })
        let task
        try {
          task = await client.submitProjectJd(project.id, jdText)
        } catch (error) {
          error.projectId = project.id
          store.current = project
          store.items.unshift(project)
          store.total += 1
          throw error
        }
        store.items.unshift(project)
        store.total += 1
        return { project, taskId: task.task_id, task }
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.saving = false
      }
    },
    async createFromImage({ title, company, location, file }) {
      store.saving = true
      store.error = ''
      try {
        const project = await client.createProject({ title, company, location })
        let task
        try {
          task = await client.submitProjectJdImage(project.id, file)
        } catch (error) {
          error.projectId = project.id
          store.current = project
          store.items.unshift(project)
          store.total += 1
          throw error
        }
        store.items.unshift(project)
        store.total += 1
        return { project, taskId: task.task_id, task }
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.saving = false
      }
    },
    async update(projectId, input) {
      const updated = await client.updateProject(projectId, input)
      const index = store.items.findIndex((item) => item.id === projectId)
      if (index >= 0) store.items[index] = { ...store.items[index], ...updated }
      if (store.current?.id === projectId) store.current = { ...store.current, ...updated }
      return updated
    },
    async archive(projectId) {
      const updated = await store.update(projectId, { archived: true })
      store.items = store.items.filter((item) => item.id !== projectId)
      store.total = Math.max(0, store.total - 1)
      return updated
    },
    async startResumeMatch(projectId, resumeId) {
      store.saving = true
      store.error = ''
      try {
        return await client.submitProjectResumeMatch(projectId, resumeId)
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.saving = false
      }
    },
    async submitJd(projectId, { text = '', file = null } = {}) {
      store.saving = true
      store.error = ''
      try {
        return file
          ? await client.submitProjectJdImage(projectId, file)
          : await client.submitProjectJd(projectId, text)
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.saving = false
      }
    },
    async startInterview(projectId, input) {
      store.saving = true
      store.error = ''
      try {
        return await client.createProjectSession(projectId, input)
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.saving = false
      }
    },
  })
  return store
}

export const projectsStore = createProjectsStore()
