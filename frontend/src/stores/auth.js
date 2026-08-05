import { reactive } from 'vue'

import { api } from '@/api/index.js'

export function createAuthStore(client = api) {
  const store = reactive({
    ready: false,
    loading: false,
    authenticated: false,
    ownerId: null,
    error: '',
    async bootstrap() {
      if (store.ready || store.loading) return store.authenticated
      store.loading = true
      store.error = ''
      try {
        const session = await client.getAuthSession()
        store.authenticated = Boolean(session.authenticated)
        store.ownerId = session.owner_id || null
      } catch (error) {
        store.authenticated = false
        store.ownerId = null
        if (error.status !== 401) store.error = error.message
      } finally {
        store.ready = true
        store.loading = false
      }
      return store.authenticated
    },
    async login(password) {
      store.loading = true
      store.error = ''
      try {
        const session = await client.login(password)
        store.authenticated = true
        store.ownerId = session.owner_id || 'default'
        store.ready = true
        return session
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.loading = false
      }
    },
    async logout() {
      store.loading = true
      try {
        await client.logout()
      } finally {
        store.loading = false
        store.markSignedOut()
      }
    },
    markSignedOut() {
      store.ready = true
      store.authenticated = false
      store.ownerId = null
    },
  })
  return store
}

export const authStore = createAuthStore()

