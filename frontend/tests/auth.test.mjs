import assert from 'node:assert/strict'
import test from 'node:test'
import { createServer } from 'vite'
import { createMemoryHistory } from 'vue-router'

test('auth store bootstraps, signs in, and signs out', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createAuthStore } = await vite.ssrLoadModule('/src/stores/auth.js')

  const calls = []
  const client = {
    async getAuthSession() {
      calls.push('session')
      const error = new Error('Authentication required')
      error.status = 401
      throw error
    },
    async login(password) {
      calls.push(['login', password])
      return { authenticated: true, owner_id: 'default' }
    },
    async logout() {
      calls.push('logout')
      return { authenticated: false }
    },
  }
  const auth = createAuthStore(client)

  await auth.bootstrap()
  assert.equal(auth.ready, true)
  assert.equal(auth.authenticated, false)

  await auth.login('correct-password')
  assert.equal(auth.authenticated, true)
  assert.equal(auth.ownerId, 'default')

  await auth.logout()
  assert.equal(auth.authenticated, false)
  assert.deepEqual(calls, ['session', ['login', 'correct-password'], 'logout'])
})

test('route guard redirects anonymous users and keeps signed-in users out of login', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { resolveAuthNavigation } = await vite.ssrLoadModule('/src/router/authGuard.js')

  const anonymous = {
    ready: false,
    authenticated: false,
    async bootstrap() { this.ready = true },
  }
  const redirect = await resolveAuthNavigation(
    { name: 'projects', fullPath: '/projects', meta: {} },
    anonymous,
  )
  assert.deepEqual(redirect, { name: 'login', query: { redirect: '/projects' } })

  const owner = { ready: true, authenticated: true }
  assert.deepEqual(
    await resolveAuthNavigation({ name: 'login', fullPath: '/login', meta: { public: true } }, owner),
    { name: 'projects' },
  )

  assert.deepEqual(
    await resolveAuthNavigation({ name: 'root', fullPath: '/', meta: {} }, anonymous),
    { name: 'login' },
  )
  assert.deepEqual(
    await resolveAuthNavigation({ name: 'root', fullPath: '/', meta: {} }, owner),
    { name: 'projects' },
  )
})

test('401 handling signs out and preserves the protected destination', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createUnauthorizedRedirect, normalizeAuthRedirect } = await vite.ssrLoadModule('/src/router/authGuard.js')

  assert.equal(normalizeAuthRedirect('/analysis/jd?source=projects'), '/analysis/jd?source=projects')
  assert.equal(normalizeAuthRedirect('//example.com/steal-session'), '/projects')
  assert.equal(normalizeAuthRedirect('https://example.com'), '/projects')

  const auth = {
    authenticated: true,
    markSignedOut() {
      this.authenticated = false
    },
  }
  const replacements = []
  const router = {
    currentRoute: {
      value: { name: 'project-workspace', fullPath: '/projects/project-1?panel=resume' },
    },
    async replace(location) {
      replacements.push(location)
    },
  }

  const handleUnauthorized = createUnauthorizedRedirect(auth, router)
  await handleUnauthorized()

  assert.equal(auth.authenticated, false)
  assert.deepEqual(replacements, [
    { name: 'login', query: { redirect: '/projects/project-1?panel=resume' } },
  ])
})

test('app router protects projects and sends authenticated root visits to projects', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())
  const { createAppRouter } = await vite.ssrLoadModule('/src/router/index.js')

  assert.equal(typeof createAppRouter, 'function')

  const anonymousRouter = createAppRouter({
    history: createMemoryHistory(),
    auth: { ready: true, authenticated: false },
    handleUnauthorized: false,
  })
  await anonymousRouter.push('/projects')
  assert.equal(anonymousRouter.currentRoute.value.name, 'login')
  assert.equal(anonymousRouter.currentRoute.value.query.redirect, '/projects')

  const ownerRouter = createAppRouter({
    history: createMemoryHistory(),
    auth: { ready: true, authenticated: true },
    handleUnauthorized: false,
  })
  await ownerRouter.push('/')
  assert.equal(ownerRouter.currentRoute.value.name, 'projects')
})

test('API sends same-origin credentials and reports structured 401 errors', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())

  const calls = []
  globalThis.fetch = async (url, options) => {
    calls.push([url, options])
    return {
      ok: false,
      status: 401,
      json: async () => ({
        code: 'authentication_required',
        message: 'Please sign in.',
        request_id: 'request-1',
      }),
    }
  }
  const module = await vite.ssrLoadModule(`/src/api/index.js?auth=${Date.now()}`)
  let unauthorized = false
  module.setUnauthorizedHandler(() => { unauthorized = true })

  await assert.rejects(module.api.getProjects(), (error) => {
    assert.equal(error.code, 'authentication_required')
    assert.equal(error.requestId, 'request-1')
    return true
  })
  assert.equal(calls[0][1].credentials, 'same-origin')
  assert.equal(unauthorized, true)
})

test('API normalizes network failures into structured errors', async (t) => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  t.after(() => vite.close())

  globalThis.fetch = async () => {
    throw new TypeError('fetch failed')
  }
  const module = await vite.ssrLoadModule(`/src/api/index.js?network=${Date.now()}`)

  await assert.rejects(module.api.getProjects(), (error) => {
    assert.equal(error.name, 'ApiError')
    assert.equal(error.code, 'network_error')
    assert.equal(error.status, 0)
    return true
  })
})
