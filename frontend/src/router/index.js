import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/pages/HomePage.vue'),
    meta: { title: 'OwlMock — AI 求职助手' },
  },
  {
    path: '/interview',
    name: 'interview-list',
    component: () => import('@/pages/InterviewListPage.vue'),
    meta: { title: '模拟面试 — OwlMock' },
  },
  {
    path: '/interview/config',
    name: 'interview-config',
    component: () => import('@/pages/InterviewConfigPage.vue'),
    meta: { title: '面试配置 — OwlMock' },
  },
  {
    path: '/interview/:id/summary',
    name: 'interview-summary',
    component: () => import('@/pages/InterviewSummaryPage.vue'),
    meta: { title: '面试总结 — OwlMock' },
  },
  {
    path: '/interview/:id',
    name: 'interview-session',
    component: () => import('@/pages/InterviewSessionPage.vue'),
    meta: { title: '模拟面试 — OwlMock' },
  },
  {
    path: '/analysis/github',
    component: () => import('@/layouts/GitHubLayout.vue'),
    meta: { title: 'GitHub 源码分析 — OwlMock' },
    children: [
      { path: '', name: 'github-list', component: () => import('@/pages/github/GitHubListPage.vue') },
      { path: ':id', name: 'github-overview', component: () => import('@/pages/github/GitHubOverviewPage.vue'), meta: { title: '仓库概览 — OwlMock' } },
      { path: ':id/deep', name: 'github-deep', component: () => import('@/pages/github/GitHubDeepPage.vue'), meta: { title: '深度分析 — OwlMock' } },
    ],
  },
  {
    path: '/analysis/jd',
    name: 'jd',
    component: () => import('@/pages/JdPage.vue'),
    meta: { title: 'JD 智能分析 — OwlMock', contentWidth: 'default' },
  },
  {
    path: '/analysis/jd/tasks/:taskId',
    name: 'jd-task',
    component: () => import('@/pages/jd/JdTaskPage.vue'),
    meta: { title: 'JD 分析进度 — OwlMock', contentWidth: 'narrow' },
  },
  {
    path: '/analysis/jd/:analysisId',
    name: 'jd-report',
    component: () => import('@/pages/jd/JdReportPage.vue'),
    meta: { title: 'JD 分析报告 — OwlMock', contentWidth: 'wide' },
  },
  {
    path: '/analysis/resume',
    name: 'resume',
    component: () => import('@/pages/ResumePage.vue'),
    meta: { title: '简历匹配分析 — OwlMock', contentWidth: 'default' },
  },
  {
    path: '/analysis/resume/tasks/:taskId',
    name: 'resume-match-task',
    component: () => import('@/pages/resume/ResumeMatchTaskPage.vue'),
    meta: { title: '简历匹配进度 — OwlMock', contentWidth: 'narrow' },
  },
  {
    path: '/analysis/resume/batches/:batchId',
    name: 'resume-match-batch',
    component: () => import('@/pages/resume/ResumeMatchBatchPage.vue'),
    meta: { title: '岗位匹配对比 — OwlMock', contentWidth: 'wide' },
  },
  {
    path: '/analysis/resume/legacy/:resumeId',
    name: 'resume-legacy-report',
    component: () => import('@/pages/resume/ResumeLegacyReportPage.vue'),
    meta: { title: '旧版简历分析 — OwlMock', contentWidth: 'default' },
  },
  {
    path: '/analysis/resume/:matchId',
    name: 'resume-match-report',
    component: () => import('@/pages/resume/ResumeMatchReportPage.vue'),
    meta: { title: '简历匹配报告 — OwlMock', contentWidth: 'wide' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  document.title = to.meta.title || 'OwlMock'
})

export default router
