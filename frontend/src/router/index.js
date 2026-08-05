import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
} from 'vue-router'

import { setUnauthorizedHandler } from '@/api/index.js'
import { authStore } from '@/stores/auth.js'
import { createUnauthorizedRedirect, resolveAuthNavigation } from './authGuard.js'

export const routes = [
  {
    path: '/',
    name: 'root',
    component: () => import('@/pages/projects/ProjectListPage.vue'),
    meta: { title: 'OwlMock', appShell: true, section: '岗位项目' },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { title: '登录 - OwlMock', public: true },
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('@/pages/projects/ProjectListPage.vue'),
    meta: { title: '岗位项目 - OwlMock', appShell: true, section: '岗位项目' },
  },
  {
    path: '/projects/new',
    name: 'project-create',
    component: () => import('@/pages/projects/ProjectCreatePage.vue'),
    meta: { title: '新建岗位 - OwlMock', appShell: true, section: '岗位项目' },
  },
  {
    path: '/projects/:projectId/jd/tasks/:taskId',
    name: 'project-jd-task',
    component: () => import('@/pages/jd/JdTaskPage.vue'),
    meta: { title: 'JD 分析进度 - OwlMock', section: '岗位项目' },
  },
  {
    path: '/projects/:projectId/resume/tasks/:taskId',
    name: 'project-resume-task',
    component: () => import('@/pages/resume/ResumeMatchTaskPage.vue'),
    meta: { title: '简历匹配进度 - OwlMock', section: '岗位项目' },
  },
  {
    path: '/projects/:projectId',
    name: 'project-workspace',
    component: () => import('@/pages/projects/ProjectWorkspacePage.vue'),
    meta: { title: '岗位工作台 - OwlMock', appShell: true, section: '岗位项目' },
  },
  {
    path: '/interview',
    name: 'interview-list',
    component: () => import('@/pages/InterviewListPage.vue'),
    meta: { title: '模拟面试 - OwlMock' },
  },
  {
    path: '/interview/config',
    name: 'interview-config',
    component: () => import('@/pages/InterviewConfigPage.vue'),
    meta: { title: '面试配置 - OwlMock' },
  },
  {
    path: '/interview/:id/summary',
    name: 'interview-summary',
    component: () => import('@/pages/InterviewSummaryPage.vue'),
    meta: { title: '面试总结 - OwlMock' },
  },
  {
    path: '/interview/:id',
    name: 'interview-session',
    component: () => import('@/pages/InterviewSessionPage.vue'),
    meta: { title: '模拟面试 - OwlMock' },
  },
  {
    path: '/analysis/github',
    component: () => import('@/layouts/GitHubLayout.vue'),
    meta: { title: 'GitHub 源码分析 - OwlMock' },
    children: [
      { path: '', name: 'github-list', component: () => import('@/pages/github/GitHubListPage.vue') },
      { path: ':id', name: 'github-overview', component: () => import('@/pages/github/GitHubOverviewPage.vue'), meta: { title: '仓库概览 - OwlMock' } },
      { path: ':id/deep', name: 'github-deep', component: () => import('@/pages/github/GitHubDeepPage.vue'), meta: { title: '深度分析 - OwlMock' } },
    ],
  },
  {
    path: '/analysis/jd',
    name: 'jd',
    component: () => import('@/pages/JdPage.vue'),
    meta: { title: 'JD 智能分析 - OwlMock', contentWidth: 'default' },
  },
  {
    path: '/analysis/jd/tasks/:taskId',
    name: 'jd-task',
    component: () => import('@/pages/jd/JdTaskPage.vue'),
    meta: { title: 'JD 分析进度 - OwlMock', contentWidth: 'narrow' },
  },
  {
    path: '/analysis/jd/:analysisId',
    name: 'jd-report',
    component: () => import('@/pages/jd/JdReportPage.vue'),
    meta: { title: 'JD 分析报告 - OwlMock', contentWidth: 'wide' },
  },
  {
    path: '/analysis/resume',
    name: 'resume',
    component: () => import('@/pages/ResumePage.vue'),
    meta: { title: '简历匹配分析 - OwlMock', contentWidth: 'default' },
  },
  {
    path: '/analysis/resume/tasks/:taskId',
    name: 'resume-match-task',
    component: () => import('@/pages/resume/ResumeMatchTaskPage.vue'),
    meta: { title: '简历匹配进度 - OwlMock', contentWidth: 'narrow' },
  },
  {
    path: '/analysis/resume/batches/:batchId',
    name: 'resume-match-batch',
    component: () => import('@/pages/resume/ResumeMatchBatchPage.vue'),
    meta: { title: '岗位匹配对比 - OwlMock', contentWidth: 'wide' },
  },
  {
    path: '/analysis/resume/legacy/:resumeId',
    name: 'resume-legacy-report',
    component: () => import('@/pages/resume/ResumeLegacyReportPage.vue'),
    meta: { title: '旧版简历分析 - OwlMock', contentWidth: 'default' },
  },
  {
    path: '/analysis/resume/:matchId',
    name: 'resume-match-report',
    component: () => import('@/pages/resume/ResumeMatchReportPage.vue'),
    meta: { title: '简历匹配报告 - OwlMock', contentWidth: 'wide' },
  },
]

function createDefaultHistory() {
  return typeof window === 'undefined' ? createMemoryHistory() : createWebHistory()
}

export function createAppRouter({
  history = createDefaultHistory(),
  auth = authStore,
  handleUnauthorized = true,
} = {}) {
  const router = createRouter({
    history,
    routes,
    scrollBehavior() {
      return { top: 0 }
    },
  })

  router.beforeEach(async (to) => {
    const decision = await resolveAuthNavigation(to, auth)
    if (decision !== true) return decision

    if (typeof document !== 'undefined') {
      document.title = to.meta.title || 'OwlMock'
    }
    return true
  })

  if (handleUnauthorized) {
    setUnauthorizedHandler(createUnauthorizedRedirect(auth, router))
  }

  return router
}

export default createAppRouter({ handleUnauthorized: typeof window !== 'undefined' })
