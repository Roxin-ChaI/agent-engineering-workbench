[English](README.md) | **简体中文**

# Agent Engineering Workbench

一个通过统一界面集成、运行和检查独立 AI Agent 工程项目的模块化 Web Workbench。

## v0.2.0

v0.2.0 提供两个可实际运行的研究工作区：

- Web Research 使用 [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent)（WRA）v0.2.0。
- Knowledge Research 使用 [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent)（PKRA）v0.4.0。

两个 Agent 均保持独立仓库。Workbench 只通过公共 Python API 和 Adapter 集成，不复制源码，也不通过 subprocess 调用 CLI。v0.1.0 建立 Workbench Shell 与 WRA 集成；v0.2.0 新增 PKRA Knowledge Research。

## 功能

- Web Research 与 Knowledge Research 工作区
- 最终 Answer 与执行状态展示
- 迭代次数、工具调用次数与执行耗时 Metrics
- WRA Agent Activity / Trace replay 与结构化 Sources
- PKRA 空 Activity、Sources / Evidence 状态的友好展示
- English / 中文 UI
- 可持久化偏好的 Dark / Light 主题
- Fake 本地联调模式与正式 Agent 集成

## 路由与 API

Frontend 路由：

- `/`
- `/research/web`
- `/research/knowledge`
- `/context`、`/prompts`、`/resume`、`/github`

Backend Research 接口：

- `POST /api/research/web`
- `POST /api/research/web/stream`
- `POST /api/research/knowledge`
- `POST /api/research/knowledge/stream`

## 架构

```text
Browser
  → Next.js Workbench
  → FastAPI
      → WRAAdapter
          → WRA v0.2.0
      → PKRAAdapter
          → PKRA v0.4.0 ProductionAgentRunner
              → PostgreSQL / pgvector
              → DeepSeek V4 Flash
              → 可选 DDGS Web Search
  → RunResult
  → GUI
```

`WRAAdapter` 与 `PKRAAdapter` 将 Agent 公共结果映射为 Workbench 自有的 `RunResult` contract。Adapter 边界使 Workbench 业务逻辑不依赖 Agent 内部实现。PKRA 通过公共 Production Runner API 完成装配，Workbench 不导入其私有 Runtime 模块。

## 依赖

- WRA 固定到稳定 Git tag `v0.2.0`。
- PKRA 及其生产 Embedding extra 固定到稳定 Git tag `v0.4.0`。
- 正常安装 Workbench 不需要本地 PKRA checkout；editable install 仅是可选开发覆盖方式。

## Knowledge Research 行为

用户可通过 `/research/knowledge` 提交已索引知识相关问题。PKRA 通过标准 `RunResult` contract 返回 Answer 与 Metrics。其当前公共结果 contract 尚未提供可无损映射的 Activity Trace 或结构化 Source/Evidence URL，因此成功运行目前会返回：

```text
trace = []
sources = []
```

这些空字段是已知 contract limitation，不表示执行失败。

## SSE 语义

两个研究工作区使用相同的运行后 replay 协议：

```text
started
→ 同步执行 Agent
→ replay 可用 trace
→ completed / stopped / error
```

两个接口当前都不是原生实时 Token/Tool streaming。由于 PKRA 暂无已映射 trace，Knowledge Research 成功时通常为 `started → completed`。

## 技术栈

- Python 3.12 与 FastAPI
- Next.js、React、TypeScript 与 Tailwind CSS
- DeepSeek V4 Flash（`deepseek-v4-flash`）
- PKRA 使用 PostgreSQL / pgvector，并可选启用 DDGS
- web-research-agent v0.2.0
- production-knowledge-research-agent v0.4.0

## 质量基线

- Backend：126 tests passed
- Ruff：PASS
- mypy strict：PASS
- pip check：PASS
- Frontend ESLint：PASS
- TypeScript：PASS

已完成 Fake Knowledge GUI E2E、PKRA Production Runner knowledge-only 与 web-enabled、Workbench Real Knowledge REST、Workbench Real Knowledge GUI 验证。每次执行耗时均为实际测量值，不合并为固定基线。

## 已知限制

- PKRA 结构化 Sources/Evidence 当前未映射到 Workbench。
- PKRA Activity Trace 当前未映射到 Workbench。
- SSE 在同步执行完成后 replay 可用事件，当前尚不支持原生实时 Token/Tool streaming。

## 文档

- [需求](docs/requirements.md)
- [架构](docs/architecture.md)
- [本地开发](docs/local-development.md)
