# Architecture

## Overall Architecture

v0.1.0 采用以下固定调用链：

`Browser → Frontend → Workbench Backend → Adapter Layer → WRA → Model Abstraction → DeepSeek Adapter → deepseek-v4-flash`

Workbench 只负责 UI、Integration、Presentation 和 API 边界。它不得复制或重新实现 WRA 的 Agent Runtime、LangChain Runtime、Web Search 或模型逻辑。

## Frontend

Frontend 使用 Next.js、React、TypeScript 和 Tailwind CSS，提供 Workbench Web UI 基础壳层、Sidebar 与 Web Research 页面，并展示 Web Research 运行结果、Agent Activity / Trace、Metrics 和基础错误状态。

## Backend

Workbench Backend 使用 Python 3.12 和 FastAPI。它负责 API 边界、请求校验、集成编排、响应标准化和基础错误处理，不承载 WRA 的运行时或模型逻辑。

Frontend 与 Backend 使用 REST 通信，并通过 `/api/research/web/stream` 定义 SSE 事件传输边界。当前 WRA 公共 `run()` 是同步、非原生流式接口，因此 v0.1.0 先发送 `started`，再完整执行 WRA；WRA 返回后按顺序 replay `RunResult.trace`，最后发送唯一的 `completed`、`stopped` 或 `error` 事件。这不是 native real-time Tool/Agent streaming。若后续 WRA 暴露原生 event/stream API，可在不改变 Frontend SSE contract 的前提下升级为实时事件。Workbench 业务层不得直接依赖 DeepSeek SDK 或具体模型类。

## Adapter Layer

Workbench Adapter Layer 定义稳定、统一的接入契约。WRA Adapter 将 Workbench 请求转换为 WRA 可接受的输入，并将 WRA 输出转换为 Workbench 的标准响应。

Adapter 必须隔离 Workbench 与 WRA 的内部数据结构，避免内部实现泄漏到 Frontend 或 Backend，并为后续其他项目接入保留统一扩展点。

## Model Abstraction

模型接入定义统一的 Model Provider / Model Client 抽象边界。DeepSeek Adapter 是该抽象在 v0.1.0 中唯一的 Provider 实现；默认 Provider 为 DeepSeek，默认模型为 `deepseek-v4-flash`。

Provider 与模型名称必须通过配置传入，不得散落硬编码。模型实例必须通过统一工厂或依赖注入创建，使 WRA 的模型使用方只依赖抽象契约。后续替换其他模型时，不应修改 Workbench 核心业务逻辑。

v0.1.0 不实现 OpenAI、Anthropic 等其他 Provider，仅保留扩展边界。具体模型调用仍属于 WRA 的模型逻辑，Workbench 不复制或重写该逻辑。

## Integrated Projects

v0.1.0 只接入 `web-research-agent`。WRA 保持独立，其 Agent Runtime、LangChain Runtime、Web Search 和模型逻辑均由 WRA 自身拥有和实现。

PKRA、Context Window Compressor、LLM Context Explorer、GitHub Reviewer、Resume Optimizer、Prompt Vault、Prompt Engineering Workbench、多 Agent 和 MCP 均不在 v0.1.0 范围内。用户系统、云部署与持久化运行历史同样不在本版本范围内。

## Data Flow

1. Browser 中的用户操作进入 Frontend。
2. Frontend 通过 REST 或 SSE 请求 Workbench Backend；SSE 请求先收到 `started`。
3. Workbench Backend 将标准请求交给 WRA Adapter。
4. WRA Adapter 转换请求并同步调用 WRA，而不复制其内部运行逻辑。
5. WRA 通过 Model Abstraction 获取 Model Client；统一工厂或依赖注入根据配置创建 DeepSeek Adapter，并使用 `deepseek-v4-flash`。
6. WRA 返回后，Adapter Layer 标准化结果、Activity / Trace、Metrics 或错误；SSE 按顺序 replay trace，再发送 terminal event。
7. Frontend 使用同一 SSE contract 完成展示；当前 replay 语义可在 WRA 支持原生 streaming 后升级为实时事件。
