# Changelog

## v0.6.1

### Prompt Library Layout

- Fixed desktop action controls being compressed below their intrinsic content width.
- Fixed Chinese Update and Clear labels wrapping one character per line.
- Balanced the Save/Update and Search/Clear control groups while preserving responsive wrapping.
- Verified the layout in English and Chinese, Light and Dark themes, and desktop through mobile widths.

### GitHub Review Diagnostics

- Added safe server-side failure diagnostics with a failure category, root exception type, and optional integer upstream status.
- Diagnostics never record exception messages, response bodies, URLs, headers, or API keys, and the existing HTTP response contract remains unchanged.
- The diagnostics were validated while investigating a runtime provider/network routing failure; this release does not claim to fix provider connectivity.

### Verification

- 520 Backend tests, including 67 focused GitHub Review tests, and 34 Frontend tests pass.
- Ruff, mypy across 66 source files, pip check, Frontend ESLint, and TypeScript pass.
- Next.js 16.3.1 production build: PASS, including `/prompts`.
- Prompt Library manual visual verification: PASS.

## v0.6.0

### Prompt Library

- Added Workbench-owned Prompt Library contracts and stable REST endpoints for List, Search, Save, Get, Update, and Delete.
- Added `PromptVaultHttpClient` with strict upstream success-status handling and fail-closed response validation.
- Added a typed Frontend client and Prompt Library UI inside `/prompts`.
- Loading a saved bundle updates only Experiment `system_prompt` and `wiki_rules`, preserving task, criteria, selected variant, `max_steps`, and `seed`.

### Architecture

- Integrated Prompt Vault API v0.2.0 as an independent HTTP service/runtime dependency.
- Browser requests terminate at Workbench-owned APIs; the Browser never calls Prompt Vault directly.
- Workbench does not import Prompt Vault internals or access its SQLAlchemy database.
- Prompt Vault base URL and timeout remain Backend-only configuration; database credentials never enter Frontend contracts.

### Reliability

- Prompt Library validation, not-found, upstream, and internal failures map to safe Workbench HTTP 422, 404, 502, and 500 boundaries.
- Upstream malformed responses and transport failures fail closed without exposing raw Prompt Vault errors.
- Mutation requests are not automatically retried.
- Prompt Vault downtime is isolated to Prompt Library; Prompt Experiment remains available.

### Verification

- 517 Backend tests, 12 focused Prompt Library Fake E2E tests, and 33 Frontend tests pass.
- Ruff, mypy, pip check, Frontend ESLint, and TypeScript pass.
- Next.js 16.3.1 production build: PASS with Node v24.14.0 and npm 11.9.0, including TypeScript, page data, 10/10 static pages, and `/prompts`.
- Real Prompt Library E2E: PASS through Prompt Vault API v0.2.0, the production Workbench Backend, the real Frontend, SQLAlchemy, and temporary SQLite. Save/Search/Load/Update/Delete, explicit rule clearing, safe offline HTTP 502 isolation, restart persistence, Browser secret boundaries, no mutation retry, cleanup, and a clean console were verified.

### Compatibility

- Existing Prompt Experiment behavior and `POST /api/prompts/experiment` remain unchanged.
- Loading a Library item preserves all non-bundle Experiment inputs.
- Prompt Vault remains outside the Workbench repository and is consumed only through its v0.2.0 HTTP contract.

### Known Limitations

- No Prompt Library pagination.
- No authentication or multi-user Prompt Vault workflow.
- No prompt history/version history, experiment-result persistence, or template-variable system.

## v0.5.0

### Added

- Added Prompt Engineering Workbench v0.2.0 as a stable production dependency.
- Added Workbench-owned Prompt Experiment contracts, `PromptExperimentAdapter`, and `POST /api/prompts/experiment`.
- Added Prompt frontend contracts/client and an interactive controlled-experiment workspace.
- Added deterministic Fake Prompt integration and focused Fake E2E coverage with zero DeepSeek calls.
- Added a collapsible sidebar with 240 px expanded and 72 px compact layouts, persisted preference, preserved navigation, and responsive content expansion.

### Changed

- Prompt form examples now use placeholder semantics instead of submitted default values.

### Validation

- Real Prompt Workspace E2E: PASS in production mode with `deepseek-v4-flash`, one HTTP 200 Prompt POST, reward 1.0, completed true, all criteria passed, zero tool calls, protected secrets, correct lifecycle, and verified GUI/i18n/theme/responsive behavior.
- 423 Backend tests, 10 focused Fake Prompt E2E tests, and 4 Frontend static tests pass.
- Ruff, mypy, pip check, Frontend ESLint, and TypeScript pass.
- The v0.5.0 Next.js production build requires manual verification because the Codex sandbox blocks Turbopack port binding with `EPERM`.

### Known Limitations

- One task and one selected variant per execution; no automatic multi-run comparison.
- No Prompt Vault persistence/history or variables/template engine.
- No arbitrary callable tools; required-tool criteria fail closed.
- Deterministic binary evaluation only; no partial credit or semantic LLM judge.

## v0.4.1

### Added

- Added resume provenance integration.
- Added structured requirement display.
- Added evidence-aware resume analysis UI.

### Compatibility

- Existing resume optimization flow remains compatible.
- Legacy responses without provenance remain supported.

### Validation

- Real backend E2E PASS.
- Real frontend GUI E2E PASS.
- Resume provenance rendering verified.
- 311 Backend tests passing; Ruff, mypy, pip check, Frontend ESLint, TypeScript, and production build passing.
