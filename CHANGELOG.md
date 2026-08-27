# Changelog

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
