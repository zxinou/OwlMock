export async function resolveAuthNavigation(to, auth) {
  if (to.name === 'root') {
    return true
  }
  if (to.meta?.public) {
    if (!auth.ready) return true
    return auth.authenticated ? { name: 'projects' } : true
  }
  if (!auth.ready && typeof auth.bootstrap === 'function') await auth.bootstrap()
  if (!auth.authenticated) {
    return { name: 'login', query: { redirect: to.fullPath || '/projects' } }
  }
  return true
}

export function normalizeAuthRedirect(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) {
    return '/projects'
  }
  return value === '/login' ? '/projects' : value
}

export function createUnauthorizedRedirect(auth, router) {
  return async function redirectUnauthorizedRequest() {
    auth.markSignedOut()

    const current = router.currentRoute.value
    if (!current?.name || current.name === 'login' || current.meta?.public) return

    await router.replace({
      name: 'login',
      query: { redirect: normalizeAuthRedirect(current.fullPath) },
    })
  }
}
