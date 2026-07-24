# OwlMock 模型路由

项目按任务类型选择模型，profile YAML 是默认配置，`backend/.env` 可以临时覆盖单个场景。

| 场景 | 默认主模型 | 默认备用模型 | 原因 |
| --- | --- | --- | --- |
| 简历分析 | `dashscope/qwen3.5-omni-plus` | `zhipu/glm-4.6v-flash` | 需要识别 PDF/图片中的版式和内容 |
| 简历与岗位匹配 | `dashscope/qwen3.5-omni-plus` | `zhipu/glm-4.6v-flash` | 对一份简历批量评估多个已分析岗位 |
| JD 分析 | `dashscope/qwen3.5-omni-plus-2026-03-15` | `zhipu/glm-4.6v-flash` | 文本理解和结构化 JSON 输出 |
| 面试官、总结 | `dashscope/qwen3.5-omni-plus-2026-03-15` | `zhipu/glm-4.6v-flash` | 对话质量、工具调用和中文表达 |
| GitHub 仓库分析 | `dashscope/qwen3.5-omni-plus-2026-03-15` | `zhipu/glm-4.6v-flash` | 长上下文和工具链协作 |
| 实时语音 | `dashscope_realtime/qwen3.5-omni-flash-realtime` | 无文本 fallback | 需要保持实时双向音频连接 |

主模型只有在供应商返回可重试错误（例如限流或 5xx）时才会切到备用模型。参数错误、模型名称错误等不可重试错误不会重复消耗额度。

## 按场景覆盖

环境变量中的 profile ID 把连字符改成下划线并转为大写。当前代码仍兼容历史 `CAPYMOCK_` 前缀，例如：

```dotenv
CAPYMOCK_RESUME_ANALYZER_PROVIDER=zhipu
CAPYMOCK_RESUME_ANALYZER_MODEL=glm-4.6v-flash
CAPYMOCK_RESUME_ANALYZER_FALLBACK_PROVIDER=dashscope
CAPYMOCK_RESUME_ANALYZER_FALLBACK_MODEL=qwen3.5-omni-plus
```

可覆盖的字段是 `PROVIDER`、`MODEL`、`TEMPERATURE`，备用模型字段在前面加 `FALLBACK_`。未设置时继续使用对应 YAML 中的值。
