[English](README.md) | **简体中文**

# Agent Engineering Workbench

一个通过统一界面集成、运行和检查独立 AI 工程项目的模块化 Web Workbench。

## v0.3.0

v0.3.0 提供三个工作区：

- Web Research 使用 [`web-research-agent`](https://github.com/Roxin-ChaI/web-research-agent)（WRA）v0.2.0。
- Knowledge Research 使用 [`production-knowledge-research-agent`](https://github.com/Roxin-ChaI/production-knowledge-research-agent)（PKRA）v0.4.0。
- Context Lab 使用 [`context-window-compressor`](https://github.com/Roxin-ChaI/context-window-compressor)（CWC）v0.1.0。

三个项目均保持独立仓库。Workbench 仅通过公共 Python API 与 Adapter 边界集成，不复制源码，也不通过 subprocess 调用 CLI。v0.1.0 建立 Workbench Shell 并接入 WRA，v0.2.0 新增 PKRA Knowledge Research，v0.3.0 新增 Context Lab。

## 功能

- Web Research 与 Knowledge Research 工作区
- Answer、执行状态、Metrics、Activity 与 Sources 展示
- Context Lab 消息历史 JSON 编辑器与 Before / After 对照
- 压缩策略、目标 Token Budget 与最大 Token Budget 控件
- 估算 Token 缩减、压缩率、策略与耗时 Metrics
- English / 中文 UI
- 可持久化偏好的 Dark / Light 主题
- Fake 本地联调模式与正式集成

## 路由与 API

Frontend 路由：

- `/`
- `/research/web`
- `/research/knowledge`
- `/context`
- `/prompts`、`/resume` 与 `/github`

Backend 接口：

- `POST /api/research/web`
- `POST /api/research/web/stream`
- `POST /api/research/knowledge`
- `POST /api/research/knowledge/stream`
- `POST /api/context/compress`

两个 Research 工作区提供 REST 与 SSE 边界。Context Lab 仅使用 REST，不提供 Context SSE 接口。

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
  → Workbench 自有结果 contract
  → GUI
```

Research Adapter 将 Agent 公共结果映射为 Workbench 自有 `RunResult`。Context Lab 使用独立的 Context Request/Result DTO，由 `CWCAdapter` 与 CWC 公共 API 相互转换。Workbench 不导入各项目私有实现。

## 依赖

- WRA 固定到稳定 Git tag `v0.2.0`。
- PKRA 及其生产 Embedding extra 固定到稳定 Git tag `v0.4.0`。
- CWC 固定到稳定 Git tag `v0.1.0`。
- 正常安装无需本地 WRA、PKRA 或 CWC checkout；editable install 仅用于可选开发覆盖。

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

## 质量基线

- Backend：168 tests passed
- Ruff：PASS
- mypy strict：PASS
- pip check：PASS
- Frontend ESLint：PASS
- TypeScript：PASS
- Next.js production build：PASS

Fake GUI 已验证三种策略、非法 JSON 在 POST 前拦截、双语/主题与 Browser Console clean。真实 REST/GUI 已验证 no-op（`45 → 45`、节省 0、`compression_applied=false`、HTTP 200）、truncation（`114 → 69`、节省 45 个估算 Token、压缩率约 60.5%、`compressed_message_count=1`、HTTP 200）、TokenBudgetError → HTTP 422 与 Console clean。Duration 为每次运行的实测值，不作为固定 benchmark。

## 已知限制

- Context Token 数值为估算值，并非精确 Tokenizer 计数。
- `compression_applied=true` 表示压缩管线执行，不一定代表输出变化。
- Context HTTP 422 响应含有用的预算详情，但当前 Frontend 仅显示 `Unable to compress this context.`。
- Workbench 不暴露 CWC 私有 partition/change 原因。
- Context Lab 当前没有 persistence 或 SSE。
- PKRA 结构化 Sources/Evidence 与 Activity Trace 当前未映射。
- Research SSE 在同步执行后 replay 可用事件，尚无原生实时 streaming。

## 文档

- [需求](docs/requirements.md)
- [架构](docs/architecture.md)
- [本地开发](docs/local-development.md)
