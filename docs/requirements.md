# Requirements

## Project Goal

`Agent Engineering Workbench` provides a unified Web UI, API, and adapter boundary for independently maintained AI engineering projects.

Version history:

- v0.1.0: Workbench Shell and WRA Web Research integration.
- v0.2.0: PKRA Knowledge Research integration while retaining WRA.
- v0.3.0: Context Lab and CWC integration while retaining both Research workspaces.
- v0.4.0: Read-only GitHub Review integration while retaining all prior workspaces.
- v0.4.1: Human-readable Resume requirement and evidence provenance using AI Resume Optimizer v0.2.1.
- v0.5.0: Controlled Prompt Experiment workspace using Prompt Engineering Workbench v0.2.0.
- v0.6.0: Prompt Library integration using Prompt Vault API v0.2.0 as an independent HTTP service.

## v0.6.0 Scope

### Backend

- Python 3.12 and FastAPI Backend.
- Workbench-owned immutable Context request/result DTOs, separate from Research `RunResult`.
- `CWCAdapter` using CWC v0.1.0 public APIs.
- Formal CWC dependency fixed to Git tag `v0.1.0`.
- `POST /api/context/compress` with no Context SSE endpoint.
- Translation of public CWC `TokenBudgetError` into a Workbench Context domain error and HTTP 422.
- Deterministic Fake Context dependency override for local GUI integration.
- Existing WRA and PKRA REST/SSE behavior remains available.
- Workbench-owned GitHub Review request/result DTOs, independent of Reviewer internals.
- `GitHubReviewerAdapter` using AI GitHub Reviewer v0.2.0 public Python APIs.
- Formal Reviewer dependency fixed to Git tag `v0.2.0`.
- `POST /api/github/review` with no GitHub Review SSE endpoint.
- Categorized invalid-input, upstream/protocol, and safe internal error boundaries.
- Request-scoped public Reviewer runner lifecycle with guaranteed close.
- Deterministic Fake GitHub Review dependency override for local GUI integration.
- Workbench-owned Resume request/result DTOs with additive requirement and evidence provenance.
- `ResumeOptimizerAdapter` using AI Resume Optimizer v0.2.1 public Python APIs.
- Formal Resume Optimizer dependency fixed to Git tag `v0.2.1`.
- `POST /api/resume/optimize` with request-scoped runner lifecycle and temporary-file cleanup.
- Legacy Resume results without provenance remain compatible.
- Workbench-owned Prompt Experiment request/result DTOs independent of upstream Python models.
- `PromptExperimentAdapter` using Prompt Engineering Workbench v0.2.0 public APIs.
- Formal Prompt Engineering dependency fixed to Git tag `v0.2.0`.
- `POST /api/prompts/experiment` with request-scoped runner creation, one execution, and guaranteed close.
- Deterministic Fake Prompt dependency override with zero DeepSeek calls.
- Workbench-owned Prompt Library request/result DTOs independent of Prompt Vault internals.
- `PromptVaultHttpClient` using Prompt Vault API v0.2.0's stable HTTP contract.
- Prompt Library List, Search, Save, Get, Update, and Delete endpoints under `/api/prompts/library`.
- Stable Prompt Library HTTP error mapping: validation 422, not found 404, upstream 502, internal 500.
- Strict upstream status/contract handling, no automatic mutation retry, and request-scoped HTTP client cleanup.
- Deterministic Fake Prompt Library dependency override without Prompt Vault or DeepSeek calls.

### Frontend

- Context TypeScript request/result contract independent of Python and CWC types.
- `compressContext()` REST client.
- `/context` Context Lab route and navigation.
- Editable message-history JSON.
- `no_compression`, `truncation`, and `windowed` strategy selection.
- Distinct target and maximum token-budget controls.
- Original / Compressed message comparison.
- Estimated original, compressed, and saved token Metrics; compression ratio, strategy, and duration.
- English / Chinese text and Dark / Light theme compatibility.
- Client-side invalid JSON handling, loading protection, and a stable request error state.
- Dedicated GitHub Review TypeScript contract and REST client.
- `/github` workspace and navigation for a public Pull Request URL.
- PR Overview, Summary, Findings, Test Gaps, Maintainability, Assessment, and Markdown Review presentation.
- Finding severity, file path, location, issue, evidence, and recommendation.
- Empty Findings and categorized error states, without any GitHub write controls.
- Dedicated Resume TypeScript contract and multipart REST client.
- `/resume` workspace with structured analysis and optimized-resume presentation.
- Human-readable requirement description, importance, and match status.
- Section-aware evidence excerpts with machine IDs hidden from the normal UI.
- `/prompts` workspace with one prompt bundle, one task, one selected variant, deterministic criteria, final response, binary evaluation, and stable step/tool metrics.
- Six selectable upstream variants without automatic multi-variant comparison.
- Prompt form examples use placeholder semantics; the shared sidebar supports persisted expanded and compact layouts.
- Prompt Library List, Search, Save, Load, Update, and Delete inside `/prompts`.
- Loading a saved bundle changes only `system_prompt` and `wiki_rules`, preserving task, criteria, selected variant, `max_steps`, and `seed`.

### Integrated Projects

- `web-research-agent` v0.2.0.
- `production-knowledge-research-agent` v0.4.0.
- `context-window-compressor` v0.1.0.
- `ai-github-reviewer` v0.2.0.
- `ai-resume-optimizer` v0.2.1.
- `prompt-engineering-workbench` v0.2.0.
- Prompt Vault API v0.2.0 as a separate HTTP service/runtime dependency.

All projects remain independent repositories or services. Workbench uses stable public Python or HTTP boundaries; it does not copy source, invoke project CLIs through subprocesses, import the Prompt Vault application, or access the Prompt Vault database directly.

## Context Contract and Behavior

The request contains ordered messages, `target_token_budget`, `max_token_budget`, and one supported strategy. The result contains original/compressed messages, estimated token counts, estimated tokens saved, compression ratio, strategy, duration, `compression_applied`, compressed message count, and preserved message count.

Token counts are estimates, not exact provider-tokenizer counts. CWC runs locally and offline without an API key, database, model provider, or network call. `CWCAdapter` invokes public CWC `compress()` and translates the public result without recomputing Metrics.

In CWC v0.1.0, `compression_applied=true` means the threshold was reached and the compression pipeline executed; it does not guarantee that output messages or estimated token counts changed.

If protected fixed/recent messages cannot fit the maximum budget, the boundary is:

```text
CWC TokenBudgetError
→ Workbench Context domain error
→ HTTP 422
```

Unexpected exceptions are not converted into client validation failures.

## Research Contract and Streaming Boundaries

Research Frontends depend only on the Workbench `RunResult` contract. PKRA currently maps Answer, Iterations, Tool Calls, and Duration but has no lossless structured Activity Trace or Source/Evidence URL contract; successful Knowledge runs therefore return `trace = []` and `sources = []`.

WRA and PKRA use synchronous run boundaries. Research SSE emits `started`, executes the agent, replays available Trace afterward, then emits `completed`, `stopped`, or `error`. It is not native real-time Token/Tool streaming.

## GitHub Review Contract and Safety

GitHub Review accepts `{ "pr_url": "https://github.com/owner/repository/pull/123" }` and returns a Workbench-owned structured result. The production chain uses `GitHubReviewerAdapter` and AI GitHub Reviewer v0.2.0's public runner; it does not import private Reviewer modules or invoke a CLI subprocess.

The integration supports public PRs only and is read-only: anonymous GitHub REST GET, no GitHub token, no comments, no submitted review, no approve/request-changes action, no merge/close, no repository mutation, and no execution of PR code. Assessment is model output displayed by the UI, not a GitHub action.

Invalid PR URLs return HTTP 422, categorized upstream/review protocol failures return HTTP 502, and unknown internal failures return a safe HTTP 500 response. GitHub Review uses REST only.

## Resume Provenance Contract

Resume Optimization accepts one PDF or DOCX resume and a job-description string. `ResumeOptimizerAdapter` invokes the AI Resume Optimizer v0.2.1 public runner and maps its structured result into Workbench-owned DTOs without importing private modules or parsing exported files.

Each requirement assessment preserves legacy `requirement_id` and `source_block_ids` while optionally adding a human-readable requirement reference and ordered evidence records. Evidence contains kind, location, source excerpt, and section references. It is mapped deterministically from parsed `SourceBlock` data, not generated, inferred, fuzzy-matched, or reconstructed from the optimized resume. The UI displays requirement descriptions and evidence excerpts while keeping machine IDs hidden by default.

## Prompt Experiment Contract

Prompt Experiment accepts one prompt bundle, one task, one selected variant, deterministic success criteria, and only `max_steps`/`seed` options. Supported criteria cover a required final response, exact response, required/forbidden response substrings, and required/forbidden tool names. The current workspace exposes no callable tool handlers, so required-tool criteria fail closed.

All criteria passing yields reward 1.0 and `completed=true`; any failure yields reward 0.0 and `completed=false`. Failed evaluation remains a successful HTTP 200 experiment result. It is not an HTTP failure, semantic/factual quality score, or LLM-as-a-Judge result. Production uses the upstream v0.2.0 public factory with `deepseek-v4-flash`; provider secrets stay outside the browser contract.

## Prompt Library Contract

Prompt Library stores `title`, prompt `content`, `wiki_rules`, and `tags` through Workbench-owned contracts. Browser requests terminate at the Workbench API; `PromptVaultHttpClient` translates them to Prompt Vault API v0.2.0's stable HTTP contract. Prompt Vault remains a separate service and owns SQLAlchemy persistence.

Loading a Library item maps `content` to Experiment `system_prompt` and stored rules to Experiment `wiki_rules`. It must not change task, success criteria, selected variant, `max_steps`, or `seed`. Update preserves stored rules when `wiki_rules` is omitted and clears them when an explicit empty list is sent.

Workbench validates its HTTP shape and maps Library failures to stable safe responses: invalid input 422, missing item 404, Prompt Vault transport/service or malformed-contract failure 502, and unexpected internal failure 500. Mutation requests are never automatically retried. If Prompt Vault is unavailable, Prompt Library returns safe 502 responses while Prompt Experiment remains available. Prompt Vault base URL, timeout, database URL, and database credentials are never part of the Browser contract.

## Validation Baseline

- 517 Backend tests pass.
- 12 focused Prompt Library Fake E2E tests pass.
- Ruff, mypy, and pip check pass.
- Frontend ESLint and TypeScript checks pass.
- 33 Frontend tests pass.
- Fake Context GUI covers all three strategies, invalid JSON blocking before POST, bilingual UI, themes, and a clean browser console.
- Real Context REST/GUI covers no-op `45 → 45`, actual `114 → 69` truncation, TokenBudgetError → HTTP 422, and a clean browser console.
- The final v0.3.0 Next.js production build has passed release verification.
- The v0.4.0 Next.js 16.3.1 production build passed, including TypeScript, static page generation, and the `/github` route.
- The v0.4.1 Next.js 16.3.1 production build passed, including TypeScript, static page generation, and the `/resume` route.
- The v0.5.0 production build passed release verification.
- The v0.6.0 Next.js 16.3.1 production build passed with Node v24.14.0 and npm 11.9.0, including TypeScript, page data, 10/10 static pages, and `/prompts`.
- Fake GitHub Review GUI covers PR 42, PR 43 empty Findings, PR 500 → HTTP 502, invalid URL → HTTP 422, empty-input blocking, bilingual UI, themes, responsive layout, and a clean console.
- Real GitHub Review REST/GUI against public PR `openai/openai-python#3357` covers structured metadata, two Findings, Assessment, Test Gaps, Maintainability, Markdown Review, one HTTP 200 business POST, a clean console, and no GitHub writes.
- Real Resume GUI validation covers one production HTTP 200 request, requirement description/importance/status, section-aware evidence excerpts, hidden machine IDs, bilingual UI, themes, responsive layout, and a clean console.
- Prompt Workspace Fake E2E covers success, failed criteria, required-tools guarding, variant/request fidelity, input validation, production isolation, and zero DeepSeek calls.
- Real Prompt Workspace E2E covers production mode, `deepseek-v4-flash`, one HTTP 200 Prompt POST, reward 1.0, completed true, all criteria passed, zero tool calls, protected secrets, correct lifecycle, and bilingual/theme/responsive GUI behavior.
- Prompt Library Fake E2E covers List, Save, Search, Load fidelity, Update, explicit clear, Delete, upstream isolation, request fidelity, production isolation, protected secrets, Prompt Experiment regression, and no automatic retry.
- Real Prompt Library E2E covers Prompt Vault API v0.2.0, production Workbench Backend, real Frontend, temporary SQLite, CRUD/search/load, explicit rule clearing, safe offline HTTP 502 isolation, restart persistence, Browser secret boundaries, no mutation retry, cleanup, and a clean console.

## Non Goals

- Context persistence or Context SSE.
- File upload or per-message token counts.
- Exact provider-tokenizer integration.
- Exposing private CWC partition/change reasons.
- LLM-based Context summarization or external API calls.
- Fabricating PKRA Activity Trace or parsing Sources/Evidence from Answer text.
- Native real-time Research Token/Tool streaming.
- Copying or reimplementing WRA, PKRA, or CWC internals.
- GitHub comments, submitted reviews, approve/request-changes actions, merge/close, repository mutation, GitHub App/OAuth, webhook handling, GitHub Review SSE, or execution of PR code.
- User accounts, cloud deployment, persisted Research history, multi-agent orchestration, or MCP integration.
- Prompt Library pagination, authentication/multi-user workflow, prompt history/version history, experiment-result persistence, or template variables.
- Arbitrary callable tools, multi-run comparison, partial-credit evaluation, or semantic LLM judging.

## Known UX Limitation

The Context API returns useful budget detail with HTTP 422, but the current Frontend displays only `Unable to compress this context.` This is a documented LOW finding, not a release blocker.
