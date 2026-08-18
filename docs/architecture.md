# Architecture

## Overall Architecture

```text
Browser
→ Next.js Frontend
→ Workbench FastAPI
→ Adapter boundary
    ├── WRAAdapter → WRA v0.2.0
    └── PKRAAdapter → PKRA v0.4.0 ProductionAgentRunner
                         → PostgreSQL / pgvector
                         → DeepSeek V4 Flash
                         → optional DDGS Web Search
→ RunResult
→ GUI
```

Workbench 只负责 UI、Integration、Presentation 与 API 边界。WRA 和 PKRA 保持独立仓库；Workbench 不复制其源码、不重新实现 Runtime，也不通过 CLI/subprocess 调用它们。

## Frontend

Frontend 使用 Next.js、React、TypeScript 与 Tailwind CSS。`/research/web` 和 `/research/knowledge` 复用统一 Research Workspace 展示 Answer、Status、Activity、Metrics 与 Sources / Evidence，并分别调用对应的 REST/SSE Client。

Frontend 只理解 Workbench DTO，不依赖 WRA、PKRA、DeepSeek、LangGraph 或数据库类型。

## Backend API

FastAPI 提供：

- `POST /api/research/web`
- `POST /api/research/web/stream`
- `POST /api/research/knowledge`
- `POST /api/research/knowledge/stream`

Router 通过 FastAPI Dependency 注入 `WorkbenchAdapter`，只调用 `adapter.run(query)` 并返回 `RunResult`。Router 不创建 Agent、模型、搜索工具或数据库资源。

## Adapter Boundary

`WRAAdapter` 将 WRA 公共 DTO 映射为 `RunResult`，包括 Answer、Trace、Metrics 与可从结构化搜索 Observation 获得的 Sources。

`PKRAAdapter` 只依赖最小 Runner/Result Protocol，将 PKRA 公共 `AgentRunResult` 映射为 Answer 与 Metrics。它使用 `perf_counter()` 测量完整 runner 执行耗时。PKRA 当前公共 contract 不提供可无损映射的 Activity Trace 或结构化 Source/Evidence URL，因此 Adapter 明确返回 `trace = []` 与 `sources = []`，不从 Messages 或自然语言 Answer 猜测数据。

## PKRA Production Composition

PKRA 的 production wiring 只使用其公共 API：

```text
Workbench Settings
→ AgentRunnerConfig
→ create_agent_runner()
→ ProductionAgentRunner
→ PKRAAdapter
```

生命周期由 request-scoped yield dependency 管理：

```text
create runner
→ yield PKRAAdapter
→ adapter.run()
→ finally runner.close()
```

每个请求拥有独立 Runner 生命周期；成功或异常路径均执行 `close()`。Workbench business logic 不依赖 PKRA private internals，不创建 LangGraph、Repository、Embedding、DDGS 或 Session 私有对象。PKRA 公共 Production Runner 是唯一 production integration boundary。

## Model and Infrastructure Boundaries

默认 Provider 为 DeepSeek，默认模型为 `deepseek-v4-flash`。配置由 Workbench Settings 传入集成项目的公共 factory/composition API，不硬编码 API Key。

PKRA Knowledge Research 需要 Backend 可访问的 PostgreSQL/pgvector 与预索引数据。DDGS Web Search 由 `PKRA_ENABLE_WEB_SEARCH` 控制。Fake dev server 使用 dependency overrides，不创建真实 PKRA Runner，也不访问数据库、DeepSeek 或 DDGS。

## SSE Semantics

Web Research 与 Knowledge Research 使用统一 SSE contract：

```text
started
→ synchronous agent execution
→ replay available RunResult.trace
→ completed / stopped / error
```

当前不是原生实时 Token/Tool streaming。WRA 返回后可 replay 已映射 Trace；PKRA 当前 `trace` 为空，因此成功的 Knowledge Research 通常只产生 `started → completed`。未来集成项目若提供原生事件 API，可在不改变 Frontend SSE contract 的前提下升级事件产生方式。

## Version Scope

- v0.1.0：Workbench Shell + WRA。
- v0.2.0：新增 PKRA Production Runner、Knowledge REST/SSE、Knowledge Frontend Workspace 与 Fake Integration。
