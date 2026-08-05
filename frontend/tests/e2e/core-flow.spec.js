import { expect, test } from '@playwright/test'

const project = {
  id: 'project-frontend',
  title: 'Frontend Engineer',
  company: 'Owl Labs',
  location: 'Remote',
  updated_at: '2026-08-05T00:00:00Z',
}

async function fulfillJson(route, payload, status = 200) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  })
}

test('lets visitors browse OwlMock before creating an account', async ({ page }) => {
  const apiRequests = []
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/')) apiRequests.push(request.url())
  })
  await page.goto('/')

  await expect(page).toHaveURL('/')
  await expect(page.getByRole('heading', { name: '把每个目标岗位，变成一套可持续的准备过程' })).toBeVisible()
  await expect(page.getByText('账户数据彼此隔离，免费开始使用')).toBeVisible()
  await expect.poll(() => apiRequests).toEqual([])

  await page.getByRole('link', { name: '创建我的工作台' }).click()
  await expect(page).toHaveURL('/register')
  await expect(page.getByRole('heading', { name: '创建 OwlMock 账户' })).toBeVisible()
})

test('signs in, opens protected projects, and signs out', async ({ page }) => {
  let authenticated = false

  await page.route((url) => url.pathname.startsWith('/api/'), async (route) => {
    const request = route.request()
    const url = new URL(request.url())

    if (url.pathname === '/api/auth/session') {
      if (authenticated) {
        await fulfillJson(route, {
          authenticated: true,
          user: { id: 'user-1', email: 'person@example.com', display_name: 'Person' },
        })
      } else {
        await fulfillJson(route, { code: 'unauthenticated', message: 'Sign in required.' }, 401)
      }
      return
    }

    if (url.pathname === '/api/auth/login' && request.method() === 'POST') {
      expect(request.postDataJSON()).toEqual({ email: 'person@example.com', password: 'test-password' })
      authenticated = true
      await fulfillJson(route, {
        authenticated: true,
        user: { id: 'user-1', email: 'person@example.com', display_name: 'Person' },
      })
      return
    }

    if (url.pathname === '/api/auth/logout' && request.method() === 'POST') {
      authenticated = false
      await fulfillJson(route, { authenticated: false })
      return
    }

    if (url.pathname === '/api/projects') {
      expect(url.searchParams.get('archived')).toBe('false')
      await fulfillJson(route, { items: [project], total: 1 })
      return
    }

    await fulfillJson(route, { code: 'unexpected_request', message: url.pathname }, 500)
  })

  await page.goto('/login')
  await expect(page).toHaveURL('/login')
  await expect(page.getByRole('heading', { name: '登录 OwlMock' })).toBeVisible()

  await page.getByLabel('邮箱').fill('person@example.com')
  await page.locator('#password').fill('test-password')
  await page.getByRole('button', { name: '进入工作台' }).click()

  await expect(page).toHaveURL('/projects')
  await expect(page.getByRole('heading', { name: '把每个目标岗位，变成一套可持续的准备过程' })).toBeVisible()
  await expect(page.getByText('Frontend Engineer', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: '退出登录' }).click()
  await expect(page).toHaveURL('/login')
  await expect(page.getByRole('heading', { name: '登录 OwlMock' })).toBeVisible()
})
