import { reactive } from 'vue'

import { api } from '@/api/index.js'

export function createAuthStore(client = api) {
  const store = reactive({
    ready: false,
    loading: false,
    authenticated: false,
    user: null,
    userId: null,
    ownerId: null,
    error: '',
    applySession(session) {
      store.authenticated = Boolean(session?.authenticated)
      store.user = session?.user || null
      store.userId = store.user?.id || null
      // Kept as a compatibility alias for code written before public accounts.
      store.ownerId = store.userId
    },
    async bootstrap() {
      if (store.ready || store.loading) return store.authenticated
      store.loading = true
      store.error = ''
      try {
        const session = await client.getAuthSession()
        store.applySession(session)
      } catch (error) {
        store.markSignedOut()
        if (error.status !== 401) store.error = error.message
      } finally {
        store.ready = true
        store.loading = false
      }
      return store.authenticated
    },
    async register(input) {
      store.loading = true
      store.error = ''
      try {
        const session = await client.register(input)
        store.applySession(session)
        store.ready = true
        return session
      } catch (error) {
        store.error = error.message
        throw error
      } finally {
        store.loading = false
      }
    },
    async login(input) {
      store.loading = true
      store.error = ''
      try {
        const session = await client.login(input)
        store.applySession(session)
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
      store.user = null
      store.userId = null
      store.ownerId = null
    },
  })
  return store
}

export const authStore = createAuthStore()
