export async function resolveAuthNavigation(to, auth) {
  if (!auth.ready && typeof auth.bootstrap === 'function') await auth.bootstrap()

  if (to.name === 'root') {
    return auth.authenticated ? { name: 'projects' } : { name: 'login' }
  }
  if (to.meta?.public) {
    return to.name === 'login' && auth.authenticated ? { name: 'projects' } : true
  }
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
    if (!current?.name || current.name === 'login') return

    await router.replace({
      name: 'login',
      query: { redirect: normalizeAuthRedirect(current.fullPath) },
    })
  }
}
