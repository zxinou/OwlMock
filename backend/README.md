# Backend — OwlMock API

AI 求职助手后端，基于 FastAPI + ReAct Agent + Realtime Voice 架构。

## Tech Stack

- **Runtime:** Python 3.13+
- **Framework:** FastAPI
- **Database:** SQLite (aiosqlite) + SQLAlchemy 2.0
- **Package Manager:** uv
- **LLM Providers:** DashScope Qwen、智谱 GLM（文本）；DashScope Qwen-Omni（语音）
- **Observability:** Langfuse (OpenTelemetry SDK v4)

## Deployment operations

The root `Dockerfile` builds the frontend and serves it from the FastAPI process.
For a local production-style deployment, use the Compose file in this directory:

```bash
cp .env.example .env
# Edit .env before starting: OWLMOCK_SESSION_SECRET is required in production.
docker compose up --build -d
docker compose logs -f app
```

OwlMock uses public email/password accounts. Set a stable, random
`OWLMOCK_SESSION_SECRET` (for example, `openssl rand -hex 32`). Changing that
secret invalidates current signed cookies. Keep `OWLMOCK_COOKIE_SECURE=true` on
HTTPS deployments, and use `false` only for local HTTP development.
`OWLMOCK_ALLOW_REGISTRATION=true` lets visitors create accounts. To bridge old
single-owner data, set `OWLMOCK_BOOTSTRAP_EMAIL` and `OWLMOCK_ADMIN_PASSWORD`
together; startup creates the `default` account once. Email verification and
password recovery are not included in this no-paid-provider beta.

For Railway, deploy this repository using the root `railway.toml` and Dockerfile,
then mount a persistent Railway volume at `/data` and set:

```dotenv
OWLMOCK_DATA_DIR=/data
OWLMOCK_SESSION_SECRET=replace-with-a-random-32-byte-secret
OWLMOCK_ALLOW_REGISTRATION=true
OWLMOCK_COOKIE_SECURE=true
OWLMOCK_AUTH_RATE_LIMIT=8
OWLMOCK_AUTH_RATE_WINDOW_SECONDS=300
TRACER=noop
```

Railway supplies `PORT`. Provider credentials such as `DASHSCOPE_API_KEY` and
`ZHIPU_API_KEY` are optional until the associated analysis features are used.
Keep Railway at one replica while this release uses SQLite, and attach the same
`/data` volume to every deployment. Do not provide a GitHub token that can read
private repositories to a public untrusted deployment.

### Upgrade, backup, and restore

Back up before changing an image or deploying a new release:

```bash
docker compose exec app python -m management backup
# Output: {"status":"ok","archive":"/data/backups/owlmock-<timestamp>.zip"}
docker compose build --pull
docker compose up -d
```

The archive contains a consistent SQLite snapshot and managed user data. Restore
only while the app is stopped:

```bash
docker compose stop app
docker compose run --rm app python -m management restore /data/backups/owlmock-<timestamp>.zip
docker compose up -d app
```

For a non-Docker installation, use the same CLI with explicit paths:

```bash
uv run python -m management backup --data-dir /srv/owlmock/data --output /srv/owlmock/backups/owlmock.zip
uv run python -m management restore /srv/owlmock/backups/owlmock.zip --data-dir /srv/owlmock/data
```

The restore command checks the archive manifest, checksums, SQLite integrity, and
schema revision before installation. A successful restore prints JSON containing
`status`, `restored_files`, and `schema_revision`.

### Proxy and troubleshooting

Place one HTTPS reverse proxy in front of port 8000 so the SPA, `/api`, and `/ws`
remain same-origin. The production command accepts standard forwarded headers. Set
`OWLMOCK_COOKIE_SECURE=true` when TLS terminates at that proxy. If health checks or
requests fail, inspect `docker compose logs -f app` and
`curl http://127.0.0.1:8000/api/health/live`. A readiness failure usually means
the session secret or persistent `/data` volume is missing; lost login sessions
usually mean the session secret changed;
missing data after a redeploy usually means the `/data` volume was not retained.

## Project Structure

```
backend/
├── agent/                  # Agent 核心
│   ├── loop.py                 # ReActAgent — Reason-Act-Observe 循环
│   ├── realtime_agent.py       # RealtimeAgent — 双泵语音 Agent
│   ├── factory.py              # AgentFactory — 创建文本/语音 Agent
│   ├── state.py                # AgentState 状态机
│   ├── profile.py              # AgentProfile + RealtimeConfig Pydantic 模型
│   ├── profile_loader.py       # 从 YAML 加载 profile
│   ├── context/
│   │   ├── builder.py          # ContextBuilder — 拼装 system prompt + 历史
│   │   ├── compactor.py        # ContextCompactor — LLM 压缩老消息
│   │   └── skill_loader.py     # SkillLoader — 加载 SKILL.md
│   └── llm/
│       ├── base.py             # BaseLLM / BaseRealtimeLLM 抽象类
│       ├── events.py           # LLMEvent 事件类型
│       ├── factory.py          # LLMFactory 注册表
│       ├── providers/          # 文本 LLM provider
│       │   ├── openai_compatible.py  # OpenAI 兼容基类
│       │   ├── dashscope_compat.py   # DashScope 适配器
│       │   └── zhipu.py              # 智谱 GLM 适配器
│       └── realtime/           # 实时语音 LLM provider
│           ├── base.py             # RealtimeSession 抽象类
│           ├── events.py           # 14 种实时事件 dataclass
│           └── dashscope_realtime.py # DashScope Qwen-Omni 适配器
├── api/                    # FastAPI 路由
│   ├── app.py                  # FastAPI app + lifespan
│   ├── sessions.py             # 会话 CRUD + 总结生成
│   ├── chat.py                 # SSE 流式对话端点
│   ├── ws.py                   # WebSocket 语音模式
│   ├── github_analysis.py      # GitHub 分析任务
│   ├── jd_analysis.py          # JD 文字/图片异步分析
│   ├── resume_analysis.py      # 简历上传与分析
│   ├── resume_matches.py       # 简历与已分析岗位匹配
│   ├── tasks.py                # 异步任务进度 API
│   ├── schemas.py              # FrontendEvent + 请求/响应模型
│   └── deps.py                 # 依赖注入
├── config/
│   ├── settings.py             # pydantic-settings 读 .env
│   └── agents/                 # Agent Profile YAML
│       ├── interviewer-technical.yaml      # 技术面试官
│       ├── interviewer-behavior.yaml       # 行为面试官
│       ├── interviewer-comprehensive.yaml  # 综合面试官
│       ├── jd-analyzer.yaml                # JD 分析
│       ├── resume-analyzer.yaml            # 简历分析
│       ├── resume-matcher.yaml             # 简历岗位匹配
│       ├── repo-analyzer.yaml              # 仓库分析
│       ├── summary-generator.yaml          # 总结生成
│       └── mid-summary-injector.yaml       # 语音中注入摘要
├── data/
│   ├── prompt/                 # 系统提示词 (.md)
│   └── skill/                  # 技能定义 (SKILL.md)
├── service/
│   ├── session_service.py      # 会话管理
│   ├── task_service.py         # 异步任务管理
│   ├── repo_indexer.py         # Repository Index / Context
│   ├── jd_report.py            # JD 结构化报告
│   ├── resume_match_report.py  # 简历匹配报告
│   ├── resume_media.py         # PDF/图片处理（PyMuPDF）
│   └── summary_utils.py        # 总结工具（fallback 检测）
├── storage/
│   ├── db/                     # SQLAlchemy
│   │   ├── models.py               # ORM 模型（sessions, repo_analyses, resumes）
│   │   └── engine.py               # 异步 engine + session 工厂
│   ├── session/
│   │   └── store.py            # JSONL 会话事件存储
│   └── memory/
│       └── store.py            # 分层 Markdown 记忆存储
├── tool/
│   ├── base.py                 # @tool 装饰器、ToolContext、ToolResult
│   ├── registry.py             # ToolRegistry 显式注册
│   ├── executor.py             # ToolExecutor 并发执行
│   ├── sandbox.py              # 沙箱路径校验
│   └── builtins/               # 内建工具
│       ├── clone_repo.py           # Git 仓库克隆
│       ├── list_directory.py       # 目录列表
│       ├── read_file.py            # 文件读取
│       ├── search_code.py          # 代码搜索（ripgrep）
│       ├── save_repo_analysis.py   # 保存分析结果
│       ├── read_repo_context.py    # 读取统一仓库上下文
│       ├── read_resume.py          # 读取简历
│       ├── query_github_analysis.py # 查询分析结果
│       ├── read_skill.py           # 读取技能定义
│       └── save_real_question.py   # 保存真实面试题
├── trace/
│   ├── __init__.py
│   └── observability.py        # Langfuse 集成（tracing + spans）
├── tests/                      # 测试
└── migrate_add_audio_columns.py # 数据库迁移脚本
```

## API 设计

### 通信模式

| 模式 | 协议 | 用途 | 端点 |
|------|------|------|------|
| **Chat** | HTTP POST | 同步请求-响应 | `POST /api/sessions/{id}/chat` |
| **Stream** | SSE | 流式推送事件 | `POST /api/sessions/{id}/messages` + `GET /api/sessions/{id}/stream` |
| **Voice** | WebSocket | 实时语音面试 | `WS /ws/voice/{session_id}` |
| **Task** | HTTP + SSE | 长时间任务进度 | `POST /api/analysis` + `GET /api/tasks/{id}/stream` |

### 会话 API

```
POST   /api/sessions                    # 创建会话
GET    /api/sessions                    # 列表 + 筛选 + 排序
GET    /api/sessions/{id}               # 单条详情
DELETE /api/sessions/{id}               # 删除面试记录 + 事件日志
GET    /api/sessions/{id}/events        # 事件回放
POST   /api/sessions/{id}/finalize      # 生成总结 + 写入记忆
```

### Chat API

```
POST   /api/sessions/{id}/chat          # 同步聊天
POST   /api/sessions/{id}/messages      # 发送消息（触发 agent）
GET    /api/sessions/{id}/stream        # SSE 流式接收事件
POST   /api/sessions/{id}/interrupt     # 中断 agent
```

### 分析 API

```
POST   /api/analysis                    # 提交 GitHub 仓库分析
GET    /api/analysis                    # 列表所有分析
GET    /api/analysis/{id}               # 单条分析结果
POST   /api/jd/analyze                  # JD 文本分析
POST   /api/jd/analyses                 # 提交异步 JD 文本任务
POST   /api/jd/analyses/image           # 提交异步 JD 图片任务
GET    /api/jd/analyses                 # JD 历史记录
POST   /api/resumes/upload              # 上传简历（PDF/图片）
GET    /api/resumes                     # 简历列表
GET    /api/resumes/{id}                # 简历详情 + 分析结果
DELETE /api/resumes/{id}                # 删除简历
POST   /api/resumes/{id}/analyze        # 触发简历分析
POST   /api/resume-matches/batch         # 一份简历批量匹配多个 JD
GET    /api/resume-match-batches/{id}    # 批量匹配进度与结果
```

### 任务 API

```
GET    /api/tasks/{id}                  # 查询任务状态
GET    /api/tasks/{id}/stream           # SSE 进度流
POST   /api/tasks/{id}/cancel           # 取消任务
```

## 核心设计

### ReAct Agent Loop

仿照 Claude Code 的核心架构：

| 模块 | 说明 |
|------|------|
| **ReActAgent** | Reason → Act → Observe 循环，支持迭代推理与工具调用 |
| **AgentState** | 状态机：IDLE → THINKING → STREAMING_TEXT → EXECUTING_TOOLS → AGGREGATING |
| **ContextBuilder** | 拼装 system prompt + skill 摘要 + 历史消息 + 简历 + 记忆 |
| **ContextCompactor** | 超过 token 阈值时用 LLM 总结老消息 |
| **ToolExecutor** | 并发执行工具，支持超时、失败隔离、cancel_token |
| **SessionStore** | JSONL append-only 持久化，支持 replay |

### Realtime Voice Agent

双泵架构，桥接客户端 WebSocket 与实时语音 LLM：

```
客户端 WebSocket ←→ RealtimeAgent ←→ 实时 LLM（DashScope Qwen-Omni）
       音频帧                  双向泵                  音频 + 转写 + 工具调用
```

特性：
- **手动分轮** — 当前面试 profile 使用 `vad_mode: none`，点击“回答完毕”后才提交本轮音频
- **可配置 VAD** — Provider 仍支持 semantic/server/none，便于扩展其他语音交互
- **MidSummary** — 每 7 分钟注入上下文摘要，防止长会话遗忘
- **成本控制** — 15 分钟会话上限 + 不活跃超时检测
- **文字转语音** — 支持从文字面试无缝切换到语音面试

### Agent Profiles

通过 YAML 配置不同角色的 agent：

| Profile | 用途 | 模式 |
|---------|------|------|
| `interviewer-technical` | 技术面试官（算法、系统设计、项目深度） | 文字 + 语音 |
| `interviewer-behavior` | 行为面试官（STAR 方法、软技能） | 文字 + 语音 |
| `interviewer-comprehensive` | 综合面试官（技术 + 行为） | 文字 + 语音 |
| `jd-analyzer` | 岗位描述分析 | 文字 |
| `resume-analyzer` | 简历分析（多模态） | 文字 |
| `resume-matcher` | 简历与一个或多个已分析岗位匹配 | 文字 + 多模态 |
| `repo-analyzer` | GitHub 仓库分析（含工具链） | 文字 |
| `summary-generator` | 面试总结生成 | 文字 |
| `mid-summary-injector` | 语音会话中注入摘要 | 文字（子 agent） |

### LLM Providers

**文本模式**（继承 `OpenAICompatibleLLM`）：
- `dashscope` — 阿里 DashScope
- `zhipu` — 智谱 GLM OpenAI 兼容接口

**语音模式**（实现 `BaseRealtimeLLM` + `RealtimeSession`）：
- `dashscope_realtime` — DashScope Qwen-Omni Realtime

### 工具系统

| 工具 | 说明 |
|------|------|
| `clone_repo` | Git 仓库克隆到沙箱 |
| `list_directory` | 列出目录结构 |
| `read_file` | 读取文件内容 |
| `search_code` | 代码搜索（ripgrep） |
| `save_repo_analysis` | 保存仓库分析结果 |
| `read_repo_context` | 读取 `repo_index.json` 形成的统一仓库上下文 |
| `read_resume` | 读取用户简历 |
| `query_github_analysis` | 查询 GitHub 分析结果 |
| `read_skill` | 读取技能定义 |
| `save_real_question` | 保存真实面试题到 REAL_QUES.md |

所有文件工具通过 `sandbox.py` 进行路径校验，防止越权访问。

### 记忆系统

分层 Markdown 记忆存储，跨会话持久化：

```
<root>/<user_id>/user.md                    — 用户画像（跨简历共享）
<root>/<user_id>/<resume_id>/CAPY_NOTE.md  — 简历级面试笔记（历史文件名，内容为猫头鹰面试官记忆）
<root>/<user_id>/<resume_id>/REAL_QUES.md  — 真实面试题记录
```

面试总结生成时自动写入面试官观察笔记和 `user_md`；面试过程中 agent 可通过 `save_real_question` 工具记录用户提到的真实面试题。

### 双层事件协议

- **LLMEvent** — Python 内部 sum type（TextDelta / ToolCallStart / Done 等）
- **FrontendEvent** — 前端 JSON 协议（assistant.text.delta / tool.call.start / user.audio.chunk 等）

## 前端集成指南

### 文字面试（SSE 流式）

```javascript
// 发送消息
await fetch(`/api/sessions/${sessionId}/messages`, {
  method: 'POST',
  body: JSON.stringify({ text: '介绍一下自己' })
})

// 接收 SSE 事件
const es = new EventSource(`/api/sessions/${sessionId}/stream`)
es.onmessage = (e) => {
  const event = JSON.parse(e.data)
  // event.type: assistant.text.delta | assistant.text.done | tool.call.start | ...
}
```

### 语音面试（WebSocket）

```javascript
const ws = new WebSocket(
  `ws://localhost:8000/ws/voice/${sessionId}?profile=interviewer-technical&user_id=default`
)

// 发送音频帧（PCM16 base64）
ws.send(JSON.stringify({ type: 'user.audio.chunk', payload: { audio: pcm16Base64 } }))

// 接收事件
ws.onmessage = (e) => {
  const event = JSON.parse(e.data)
  // event.type: assistant.audio.delta | assistant.transcript.done | ...
}
```

### GitHub 分析（异步任务）

```javascript
// 提交任务
const { task_id } = await fetch('/api/analysis', {
  method: 'POST',
  body: JSON.stringify({ repo_url: 'https://github.com/...' })
}).then(r => r.json())

// 监听进度
const es = new EventSource(`/api/tasks/${task_id}/stream`)
es.onmessage = (e) => {
  const { status, progress, message } = JSON.parse(e.data)
}
```

## 开发规范

- 使用 uv 管理依赖：`uv add <package>`
- 类型注解必须完整
- 使用 async/await
- 测试放在 `tests/` 对应模块下
- 使用 ruff 进行 lint 检查

## 常用命令

```bash
# 运行
uv run uvicorn api.app:app --reload

# 测试
uv run pytest

# Lint
uv run ruff check . --fix

# 类型检查
uv run mypy backend
```

## 环境变量

参考 `.env.example`：

| 变量 | 说明 |
|------|------|
| `DASHSCOPE_API_KEY` | DashScope API 密钥（文本 + 语音） |
| `ZHIPU_API_KEY` | 智谱 GLM API 密钥（备用文本模型） |
| `TRACER` | `noop` 或 `langfuse` |
| `SQLITE_PATH` | SQLite 数据库路径 |
| `JSONL_ROOT` | JSONL 会话文件根目录 |
| `MEMORY_ROOT` | 记忆文件根目录 |
| `RESUME_ROOT` | 简历文件存储路径 |
| `VOICE_DEFAULT_SESSION_MINUTES` | 语音会话最大时长（默认 15） |
| `VOICE_INACTIVITY_TIMEOUT_SECONDS` | 语音不活跃超时（默认 300） |

> **注意**：sessions 表包含 `audio_seconds_in` / `audio_seconds_out` 列（语音面试用）。项目无 Alembic 迁移，升级后请运行 `python migrate_add_audio_columns.py`。
