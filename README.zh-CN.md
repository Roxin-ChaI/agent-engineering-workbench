[English](README.md) | **简体中文**

# Agent Engineering Workbench

一个通过统一界面集成、运行和检查独立 AI 工程项目的模块化 Web Workbench。

## v0.6.1

v0.6.1 提供六个工作区：

- Web Research 使用 [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent)（WRA）v0.2.0。
- Knowledge Research 使用 [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent)（PKRA）v0.4.0。
- Context Lab 使用 [`context-window-compressor`](https://github.com/Roxin-ChaI/context-window-compressor)（CWC）v0.1.0。
- GitHub Review 使用 [`ai-github-reviewer`](https://github.com/Roxin-ChaI/ai-github-reviewer) v0.2.0。
- Resume Optimization 使用 [`ai-resume-optimizer`](https://github.com/Roxin-ChaI/ai-resume-optimizer) v0.2.1。
- Prompt Experiment 使用 [`prompt-engineering-workbench`](https://github.com/Roxin-ChaI/prompt-engineering-workbench) v0.2.0。

所有集成项目均保持独立仓库或服务。Workbench 只使用稳定公共边界，不复制源码，也不通过 subprocess 调用 CLI。v0.1.0 建立 Workbench Shell 并接入 WRA，v0.2.0 新增 PKRA Knowledge Research，v0.3.0 新增 Context Lab，v0.4.0 新增只读 GitHub Review，v0.4.1 新增人类可读的简历 provenance，v0.5.0 新增受控 Prompt Experiment，v0.6.0 新增由 Prompt Vault API v0.2.0 支持的 Prompt Library。

## 功能

- Web Research 与 Knowledge Research 工作区
- Answer、执行状态、Metrics、Activity 与 Sources 展示
- Context Lab 消息历史 JSON 编辑器与 Before / After 对照
- 压缩策略、目标 Token Budget 与最大 Token Budget 控件
- 估算 Token 缩减、压缩率、策略与耗时 Metrics
- 只读审查公开 GitHub Pull Request，展示 PR Overview、Summary、Findings、Test Gaps、Maintainability、Assessment 与 Markdown Review
- 简历优化、结构化职位要求评估与感知章节的证据 provenance
- 受控 Prompt Experiment，支持 variant 选择、确定性成功条件、结构化评估与指标
- 由 Prompt Vault API v0.2.0 支持的 Prompt Library List、Search、Save、Load、Update 与 Delete
- 可折叠导航栏，并持久化展开或紧凑布局偏好
- English / 中文 UI
- 可持久化偏好的 Dark / Light 主题
- Fake 本地联调模式与正式集成

## 路由与 API

Frontend 路由：

- `/`
- `/research/web`
- `/research/knowledge`
- `/context`
- `/github`
- `/resume`
- `/prompts`

Backend 接口：

- `POST /api/research/web`
- `POST /api/research/web/stream`
- `POST /api/research/knowledge`
- `POST /api/research/knowledge/stream`
- `POST /api/context/compress`
- `POST /api/github/review`
- `POST /api/resume/optimize`
- `POST /api/prompts/experiment`
- `POST /api/prompts/library`
- `GET /api/prompts/library`
- `GET /api/prompts/library/search?q=...`
- `GET /api/prompts/library/{prompt_id}`
- `PUT /api/prompts/library/{prompt_id}`
- `DELETE /api/prompts/library/{prompt_id}`

两个 Research 工作区提供 REST 与 SSE 边界。Context Lab、GitHub Review、Resume Optimization、Prompt Experiment 与 Prompt Library 仅使用 REST，均不提供 SSE 接口。

## 架构

```text
Browser
  → Next.js Workbench
  → FastAPI
      → WRAAdapter → WRA v0.2.0
      → PKRAAdapter → PKRA v0.4.0 ProductionAgentRunner
          → PostgreSQL / pgvector
          → DeepSeek V4 Flash
          → 可选 DDGS Web Search
      → CWCAdapter → CWC v0.1.0 public compress()
      → GitHubReviewerAdapter
          → AI GitHub Reviewer v0.2.0 public runner
          → anonymous GitHub REST GET
          → DeepSeek V4 Flash
      → ResumeOptimizerAdapter
          → AI Resume Optimizer v0.2.1 public runner
          → DeepSeek V4 Flash
      → PromptExperimentAdapter
          → Prompt Engineering Workbench v0.2.0 public factory/runner
          → DeepSeek V4 Flash
          → 确定性评估
      → PromptVaultHttpClient
          → Prompt Vault API v0.2.0 HTTP contract
          → SQLAlchemy 持久化
  → Workbench 自有结果 contract
  → GUI
```

Research Adapter 将 Agent 公共结果映射为 Workbench 自有 `RunResult`。Context Lab、GitHub Review、Resume Optimization、Prompt Experiment 与 Prompt Library 使用各自独立的 Workbench contract；集成边界负责转换公共结构化结果，Frontend 仅依赖 Workbench TypeScript contract。Workbench 不导入各项目私有实现，也不直接访问 Prompt Vault 数据库。

## 依赖

- WRA 固定到稳定 Git tag `v0.2.0`。
- PKRA 及其生产 Embedding extra 固定到稳定 Git tag `v0.4.0`。
- CWC 固定到稳定 Git tag `v0.1.0`。
- AI GitHub Reviewer 固定到稳定 Git tag `v0.2.0`。
- AI Resume Optimizer 固定到稳定 Git tag `v0.2.1`。
- Prompt Engineering Workbench 固定到稳定 Git tag `v0.2.0`。
- 正常安装无需本地 WRA、PKRA、CWC、Reviewer、Resume Optimizer 或 Prompt Engineering Workbench checkout；editable install 仅用于可选开发覆盖。
- Prompt Vault API v0.2.0 是独立 HTTP 服务/运行时依赖，不是 Workbench Python package 依赖。

## Context Lab

Context Lab 接收：

- 消息历史 JSON 数组；
- `no_compression`、`truncation` 或 `windowed`；
- 目标 Token Budget；
- 最大 Token Budget。

界面展示 Original Messages、Compressed Messages、Estimated Original Tokens、Estimated Compressed Tokens、Estimated Tokens Saved、Compression Ratio、Strategy 与 Duration。API contract 还返回压缩管线是否执行，以及被压缩和原样保留的输入消息数量。

Token 数值由 CWC 离线计数器确定性估算，并非 Provider Tokenizer 的精确计数。CWC 在本地离线运行，无需 API Key，也不依赖网络；Adapter 调用 CWC 公共 `compress()` API。

CWC v0.1.0 中，`compression_applied=true` 表示已达到压缩阈值并执行压缩管线，不保证最终消息或估算 Token 数一定变化。

当硬预算不可满足（例如受保护的 fixed/recent 消息本身超过最大预算）时，错误边界为：

```text
CWC TokenBudgetError
→ Workbench Context domain error
→ HTTP 422
```

## GitHub Review

GitHub Review 接收公开 Pull Request URL，返回 Workbench 自有结构化结果，包括 PR Overview、Summary、Findings、Test Gaps、Maintainability、Assessment 与 Markdown Review。每个 Finding 包含 severity、file path、location、issue、evidence 与 recommendation。

```text
Browser
→ POST /api/github/review
→ GitHubReviewerAdapter
→ AI GitHub Reviewer v0.2.0 public runner
→ anonymous GitHub REST GET
→ DeepSeek V4 Flash
→ Workbench 自有结构化结果
→ UI
```

该集成严格只读：仅支持公开 PR，只发送匿名 GitHub REST GET；不使用 GitHub Token，不评论、不提交 Review、不执行 Approve/Request Changes、不 Merge/Close、不修改仓库，也不执行 PR 代码。UI 中的 Assessment 只是模型结果展示，不是 GitHub action。

该接口仅提供 REST。非法 PR URL 返回 HTTP 422，上游或 Review 协议失败返回 HTTP 502，未知内部失败返回安全的 HTTP 500。

## 简历 Provenance 集成

Resume Optimization 展示结构化职位要求引用及支持每项评估的简历证据。职位要求卡片使用人类可读的描述、重要性和匹配状态；证据卡片优先展示章节标题与对应原文摘录。内部 requirement/source-block ID 仍用于确定性关联，但默认 UI 不展示。

Provenance 来自 AI Resume Optimizer v0.2.1。证据由解析后简历的 `SourceBlock` 数据确定性映射，并保持原始来源顺序；它不是模型重新生成的解释、推断来源、模糊匹配，也不是从优化后简历反推的内容。缺少 provenance 的旧响应仍通过非破坏性 fallback 保持兼容。

## Prompt Experiment 工作区

Prompt Experiment 是用于单次受控实验的浏览器工作区：每个请求包含一个 `PromptBundle`、一个任务和一个用户选择的 variant。支持上游六个公共 variant：`baseline`、`tone_trump`、`tone_casual`、`wiki_random`、`no_tool_desc` 与 `all_ablations`；不会自动运行六方案对比。GUI 仅暴露 `max_steps` 与 `seed`。

成功条件支持要求最终响应、精确响应、必须/禁止出现的响应子串，以及必须/禁止使用的工具名。当前工作区没有可调用 tool handler，因此 required-tool 条件 fail closed。全部条件通过时 `reward = 1.0`、`completed = true`；任一条件失败时 `reward = 0.0`、`completed = false`。评估失败仍是正常 HTTP 200 实验结果，不是 HTTP 错误、语义质量分、事实性评分或 LLM-as-a-Judge 结论。

Production 请求通过 Prompt Engineering Workbench v0.2.0 公共 factory：每个请求创建 runner、恰好运行一次并恰好关闭一次。默认模型为 `deepseek-v4-flash`；Provider Secret 只留在 Backend，不进入 Browser contract。

## Prompt Library 工作区

`/prompts` 工作区将 Prompt Experiment 与可复用 Prompt Library 组合在一起。Library 保存 `title`、prompt `content`、`wiki_rules` 与 `tags`，并通过 Workbench 自有 API 支持 List、Search、Save、Load、Update 与 Delete。加载条目时，`content` 映射到 Experiment 的 `system_prompt`，`wiki_rules` 映射到 Experiment 的 `wiki_rules`；当前 task、success criteria、所选 variant、`max_steps` 与 `seed` 保持不变。

```text
Browser
→ Workbench Prompt Library API
→ PromptVaultHttpClient
→ Prompt Vault API v0.2.0
→ SQLAlchemy 持久化
```

Browser 不直接调用 Prompt Vault。Workbench 不导入 Prompt Vault 应用内部实现，也不访问其数据库。`PROMPT_VAULT_BASE_URL` 与 `PROMPT_VAULT_TIMEOUT_SECONDS` 仅属于 Backend 配置；Prompt Vault 数据库凭据绝不进入 Frontend。

Workbench 将 Prompt Library validation failure 映射为 HTTP 422，缺失条目映射为 404，Prompt Vault transport/service failure 安全映射为 502，未知内部失败安全映射为 500。Mutation 不自动重试。Prompt Vault 离线时，Prompt Library 安全返回 HTTP 502，同时 Prompt Experiment 仍可使用。

## Research 行为与 SSE 语义

PKRA 通过 `RunResult` 返回 Answer 与 Metrics，但当前公共结果没有可无损映射的 Activity Trace 或结构化 Source/Evidence URL。因此 Knowledge 成功运行目前返回 `trace = []` 与 `sources = []`；这是已知 contract limitation，不表示执行失败。

两个 Research Stream 使用相同的运行后 replay 协议：

```text
started
→ 同步执行 Agent
→ replay 可用 trace
→ completed / stopped / error
```

两个接口当前均不提供原生实时 Token/Tool streaming。

## 技术栈

- Python 3.12 与 FastAPI
- Next.js、React、TypeScript 与 Tailwind CSS
- DeepSeek V4 Flash（`deepseek-v4-flash`）
- PKRA 使用 PostgreSQL / pgvector，并可选启用 DDGS
- web-research-agent v0.2.0
- production-knowledge-research-agent v0.4.0
- context-window-compressor v0.1.0
- ai-github-reviewer v0.2.0
- ai-resume-optimizer v0.2.1
- prompt-engineering-workbench v0.2.0
- 独立 HTTP 服务 Prompt Vault API v0.2.0
- 公开 Pull Request 的匿名 GitHub REST GET

## 质量基线

- Backend：520 tests passed
- GitHub Review focused tests：67 passed
- Prompt Library focused Fake E2E：12 tests passed
- Ruff：PASS
- mypy：PASS
- pip check：PASS
- Frontend ESLint：PASS
- TypeScript：PASS
- Frontend tests：34 passed
- Next.js 16.3.1 v0.6.1 production build：PASS（TypeScript、page data、10/10 static pages 与 `/prompts` generation 均通过；Node v24.14.0、npm 11.9.0）
- Prompt Library 人工视觉验证：PASS（English/中文、Light/Dark、desktop/mobile 布局）

Fake GUI 已验证三种策略、非法 JSON 在 POST 前拦截、双语/主题与 Browser Console clean。真实 REST/GUI 已验证 no-op（`45 → 45`、节省 0、`compression_applied=false`、HTTP 200）、truncation（`114 → 69`、节省 45 个估算 Token、压缩率约 60.5%、`compressed_message_count=1`、HTTP 200）、TokenBudgetError → HTTP 422 与 Console clean。Duration 为每次运行的实测值，不作为固定 benchmark。

GitHub Review Fake GUI 已验证 PR 42（2 个 Findings）、PR 43（空 Findings）、PR 500 → HTTP 502、非法 URL → HTTP 422、空输入拦截、English/中文、Light/Dark、响应式布局与 Console clean。针对公开 PR `openai/openai-python#3357` 的真实 REST/GUI 验证已通过：结构化 metadata、2 个 Findings、Assessment、Test Gaps、Maintainability、Markdown Review、单次业务 POST HTTP 200、Console clean，且 GitHub write 为 NONE。

Resume Provenance 真实 GUI 已通过 production app 验证：单次 HTTP 200 请求、人类可读职位要求描述、importance/status、感知章节的 evidence excerpt、machine ID 默认隐藏、English/中文、Light/Dark、响应式布局与 Console clean。

Prompt Workspace 确定性 Fake E2E 通过 pytest/TestClient 与本地浏览器验证覆盖成功、失败条件、required-tools guard、variant/request fidelity、输入校验、production isolation 与零 DeepSeek 调用。Real Prompt Workspace E2E 已在 production mode 使用 `deepseek-v4-flash` 通过：单次 Prompt POST 返回 HTTP 200、reward 1.0、completed true、全部条件通过、tool calls 0、Console clean、Provider Secret 边界安全、request-scoped lifecycle 正确，并完成双语/主题/响应式验证。

Prompt Library 确定性 Fake E2E 覆盖 initial list、Save、Search、Load fidelity、Update、显式清空规则、Delete、上游错误隔离、mutation failure、request fidelity、Prompt Experiment regression、production isolation、secret protection 与无自动重试。Real Prompt Library E2E 已通过真实 Prompt Vault API v0.2.0 服务、真实 Workbench Backend、真实 Frontend、SQLAlchemy 与临时 SQLite：验证 Save/Search/Load/Update/Delete、显式清空 `wiki_rules`、Prompt Vault 离线时安全 HTTP 502 隔离、重启后持久化、browser secret boundary、无 mutation retry、cleanup 与 clean console。

## 已知限制

- Context Token 数值为估算值，并非精确 Tokenizer 计数。
- `compression_applied=true` 表示压缩管线执行，不一定代表输出变化。
- Context HTTP 422 响应含有用的预算详情，但当前 Frontend 仅显示 `Unable to compress this context.`。
- Workbench 不暴露 CWC 私有 partition/change 原因。
- Context Lab 当前没有 persistence 或 SSE。
- PKRA 结构化 Sources/Evidence 与 Activity Trace 当前未映射。
- Research SSE 在同步执行后 replay 可用事件，尚无原生实时 streaming。
- Prompt Experiment 每次只运行一个任务和一个所选 variant，不提供自动对比矩阵。
- Prompt Library 暂无 pagination、authentication/multi-user workflow、prompt history/version history、experiment-result persistence 或 template-variable system。
- Prompt Experiment 没有任意 callable tools；required-tool 条件 fail closed。
- Prompt 评估是确定性二元评估，无部分得分，也没有语义 LLM judge。

## 文档

- [需求](docs/requirements.md)
- [架构](docs/architecture.md)
- [本地开发](docs/local-development.md)
