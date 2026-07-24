# Frontend — OwlMock

OwlMock 前端是一个 Vue 3 + Vite 应用，负责承载首页、分析工作台、简历管理、GitHub 仓库分析、JD 分析和模拟面试体验。

视觉方向围绕“猫头鹰面试官”展开：黑白手绘线稿、青绿色主色、少量金色提示色，以及适合长时间使用的浅色/深色模式。

## Tech Stack

- **Framework:** Vue 3 (Composition API + `<script setup>`)
- **Build:** Vite 6
- **Styling:** Tailwind CSS 3 + CSS Custom Properties
- **Routing:** Vue Router 4
- **State:** Vue reactive stores (`theme.js`, `tweaks.js`)
- **Language:** JavaScript

## Quick Start

```bash
npm install
npm run dev        # localhost:3000
npm run build      # production build
npm run preview    # preview production build
```

## Pages

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | HomePage | 产品首页 |
| `/analysis/github` | GitHubListPage | 仓库分析列表、新建分析 |
| `/analysis/github/:id` | GitHubOverviewPage | 仓库概览、项目亮点、面试问题 |
| `/analysis/github/:id/deep` | GitHubDeepPage | 深度分析、目录树、代码片段 |
| `/analysis/jd` | JdPage | JD 文字/截图分析与历史管理 |
| `/analysis/jd/tasks/:taskId` | JdTaskPage | JD 异步分析进度 |
| `/analysis/jd/:analysisId` | JdReportPage | JD 结构化分析报告 |
| `/analysis/resume` | ResumePage | 简历库、岗位选择与匹配历史 |
| `/analysis/resume/tasks/:taskId` | ResumeMatchTaskPage | 单岗位匹配进度 |
| `/analysis/resume/batches/:batchId` | ResumeMatchBatchPage | 多岗位匹配对比 |
| `/analysis/resume/:matchId` | ResumeMatchReportPage | 简历匹配报告 |
| `/interview` | InterviewListPage | 面试记录列表、继续/总结/删除 |
| `/interview/config` | InterviewConfigPage | 面试配置 |
| `/interview/:id` | InterviewSessionPage | 文字/语音模拟面试 |
| `/interview/:id/summary` | InterviewSummaryPage | 面试总结与反馈 |

## Directory Structure

```text
src/
├── pages/
│   ├── HomePage.vue
│   ├── InterviewListPage.vue
│   ├── InterviewConfigPage.vue
│   ├── InterviewSessionPage.vue
│   ├── InterviewSummaryPage.vue
│   ├── JdPage.vue
│   ├── ResumePage.vue
│   └── github/
├── components/
│   ├── common/       # OwlLogo、上传、Loading、结果头、错误提示
│   ├── github/       # 仓库卡片、添加仓库、代码片段、目录树
│   ├── interview/    # 文字/语音面试、面试卡片、总结、配置弹窗
│   └── landing/      # 首页各区块
├── composables/      # 语音面试、GitHub 分析、面试配置等逻辑
├── stores/           # 主题与设计微调状态
├── layouts/          # 分析页布局
├── router/           # 路由配置
├── data/             # 面试类型与示例数据
├── api/              # REST / SSE / WebSocket API 客户端
└── assets/styles/    # 全局 CSS 变量与组件基础样式
```

## Feature Modules

### GitHub 分析

- 提交 GitHub 仓库 URL 后创建异步分析任务
- SSE 进度追踪，支持任务重连
- 分析完成后展示概览和深度报告
- 空输入和错误状态有明确反馈

### JD 分析

- 支持粘贴职位描述或上传 PNG/JPEG 岗位截图
- 独立等待、失败和报告三态页面，支持任务恢复
- 输出核心要求、隐含期望、风险点和准备建议
- 历史记录支持单条与批量删除

### 简历匹配

- 支持 PDF、PNG、JPG 上传
- 从简历库复用已上传文件
- 一份简历可以选择多个已分析 JD 并行匹配
- 支持岗位横向对比、单岗位报告、任务恢复和批量删除

### 模拟面试

- 文字模式：SSE 流式回复、Markdown 渲染、历史事件回放
- 语音模式：WebSocket、PCM16 音频、实时转写和手动分轮提交
- 面试记录：继续面试、查看总结、删除记录
- 面试总结：亮点、建议、技术/行为评估

### 设计系统

- CSS 变量驱动主题色、字号、圆角、阴影
- 深色/浅色模式
- `TweaksPanel` 支持实时调整主色、字号、圆角和动画
- 猫头鹰线稿图片在浅色/深色背景下均有适配

## API Integration

前端通过 `src/api/index.js` 访问 FastAPI 后端。

```javascript
// GitHub 分析
api.analyzeGithub(url)
api.getGithubRepos()
api.getGithubRepo(id)
api.getTaskStatus(taskId)
api.getTaskStreamUrl(taskId)

// JD / 简历
api.analyzeJd(text)
api.submitJd(text)
api.submitJdImage(file)
api.getJdAnalyses()
api.getResumes()
api.uploadResume(file)
api.analyzeResume(resumeId, force)
api.deleteResume(resumeId)
api.submitResumeMatchBatch({ resumeId, jdAnalysisIds })
api.getResumeMatchBatch(batchId)

// 面试会话
api.createSession({ profileId, mode, resumeId, githubRepoIds })
api.getSessions({ userId, status, profileId })
api.getSession(sessionId)
api.deleteSession(sessionId)
api.sendSSEMessage(sessionId, text)
api.streamEvents(sessionId)
api.finalizeSession(sessionId)
api.getVoiceWebSocketUrl(sessionId, { profileId, userId, mode })
```

## Event Types

| 事件 | 说明 |
|------|------|
| `assistant.text.delta` | 流式文本片段 |
| `assistant.text.done` | 完整文本回复 |
| `assistant.transcript.delta` | 语音转写片段 |
| `assistant.transcript.done` | 完整语音转写 |
| `assistant.audio.delta` | base64 PCM16 音频帧 |
| `user.text` | 用户文字输入 |
| `user.transcript` | 用户语音转写 |
| `tool.call.start` | 工具调用开始 |
| `tool.call.end` | 工具调用结束 |
| `turn.done` | 本轮结束 |
| `error` | 错误事件 |
