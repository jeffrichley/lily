# Feature: seedling-copier-template

Create a reusable Copier template for lightweight Python project bootstrapping, with optional CLI generation modes and no Lily-specific runtime contracts.

## Feature Description

Build a new template project at `~/workspace/tools/seedling` that can generate Python projects with optional CLI scaffolding:
- `cli_mode: none | command | repl`
- minimal Typer code only when CLI mode is enabled
- project script name configurable so users invoke via `uv run <project_cli_name>`
- optional `.ai` workflow docs (generic only), excluding Lily-specific planning history

The template must remain small and adaptable across different project styles.

## User Story

As a developer starting a new project,
I want a Copier template that can generate either no CLI, a simple command CLI, or a simple REPL CLI,
So that I get only the scaffolding I need without opinionated runtime contracts.

## Problem Statement

Previous direction pulled in too much Lily-specific architecture (deterministic envelopes, command routing internals). That is overly prescriptive for a general-purpose starter template and conflicts with the goal of minimal generation.

## Solution Statement

Create `seedling` with a minimal, mode-driven generation model:
1. Ask a single core CLI question: `cli_mode`.
2. Generate no Typer app for `none`.
3. Generate a Typer app with one `hello` command for `command`.
4. Generate a Typer app with a `repl` command loop (and optional `hello`) for `repl`.
5. Add `[project.scripts]` only when CLI mode is `command` or `repl`.
6. Keep `.ai` docs optional and generic (`COMMANDS`, `REF`, `RULES`, `HUMAN_RUNBOOK`) with no `.ai/PLANS` carryover.

## Feature Metadata

**Feature Type**: New Capability (developer tooling template)  
**Estimated Complexity**: Medium  
**Primary Systems Affected**: `~/workspace/tools/seedling` (new repo)  
**Dependencies**: Copier, uv, pytest, typer (conditional), optional rich

## Branch Setup (Required)

For implementation in the target template repo (`~/workspace/tools/seedling`), branch strategy is optional and can follow that repo's conventions.

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `AGENTS.md` - repo-level workflow constraints and scope boundaries.
- `.ai/RULES.md` - non-negotiables about planning/validation discipline.
- `.ai/COMMANDS/plan.md` - planning structure requirements.
- `.ai/REF/plan-authoring.md` - required plan skeleton fields.

### New Files to Create

In `~/workspace/tools/seedling`:
- `copier.yml`
- `README.md`
- `template/pyproject.toml.jinja`
- `template/README.md.jinja`
- `template/src/{{ package_name }}/__init__.py.jinja`
- `template/src/{{ package_name }}/cli.py.jinja` (conditional for `command`/`repl`)
- `template/tests/unit/test_cli.py.jinja` (conditional for `command`/`repl`)
- `template/.ai/*` (conditional, generic only)
- `tests/generation/test_copy_matrix.py`

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Copier: Creating a template](https://copier.readthedocs.io/en/latest/creating/)
- [Copier: Configuring a template](https://copier.readthedocs.io/en/latest/configuring/)

### Patterns to Follow

**Minimal CLI Pattern:**
- `none`: no Typer app, no CLI tests, no `project.scripts` entry.
- `command`: Typer app with `hello` command.
- `repl`: Typer app with `repl` command loop (simple stdin loop), plus optional `hello` command.

**Script Name Pattern:**
- Ask for `cli_name`.
- For CLI-enabled modes, generate `[project.scripts] {{ cli_name }} = "{{ package_name }}.cli:app"`.

**Template Scope Pattern:**
- Do not generate deterministic result envelope types.
- Do not generate slash-command parser/router framework.
- Keep generated files intentionally few.

**AI Docs Pattern (Optional):**
- `include_ai_workflow: true|false`
- If true, include generic `.ai/COMMANDS`, `.ai/REF`, `.ai/RULES.md`, `.ai/HUMAN_RUNBOOK.md`.
- Never include `.ai/PLANS/*` from Lily.

---

## IMPLEMENTATION PLAN

- [x] Phase 1: Define Copier questionnaire and conditional file matrix
- [x] Phase 2: Implement minimal project template files per `cli_mode`
- [x] Phase 3: Add optional generic `.ai` docs bundle
- [x] Phase 4: Add generation matrix tests (`none`, `command`, `repl`)
- [x] Phase 5: Validate generated outputs and document usage

### Intent Lock: Phase 1

**Source of truth**:
- Copier docs (`creating`, `configuring`)

**Must**:
- define `cli_mode` with allowed values `none|command|repl`
- define `cli_name`, `project_name`, `project_slug`, `package_name`
- define `include_ai_workflow`

**Must Not**:
- do not add questions for deterministic runtime contracts

**Acceptance criteria**:
- `copier.yml` validates and conditionally renders files by mode

**Non-goals**:
- advanced plugin/task automation

**Required tests/gates**:
- render smoke with each mode

### Intent Lock: Phase 2

**Source of truth**:
- this plan's minimal CLI pattern

**Must**:
- generate no CLI code for `none`
- generate Typer `hello` command for `command`
- generate Typer `repl` loop for `repl`
- add `project.scripts` only when CLI mode is enabled

**Must Not**:
- do not generate envelope/parser/runtime abstraction layers

**Acceptance criteria**:
- generated outputs match file matrix exactly for each mode

**Non-goals**:
- rich rendering policy frameworks

**Required tests/gates**:
- matrix assertions on generated file presence/absence

### Intent Lock: Phase 3

**Source of truth**:
- optional AI workflow requirement from user feedback

**Must**:
- include generic `.ai` docs only when enabled
- include `COMMANDS`, `REF`, `RULES`, `HUMAN_RUNBOOK`

**Must Not**:
- do not copy Lily `.ai/PLANS` files
- do not include Lily-specific historical process content

**Acceptance criteria**:
- `.ai` folder toggles on/off cleanly by template option

**Non-goals**:
- full AI governance stack from Lily

**Required tests/gates**:
- generation matrix includes `include_ai_workflow=true/false` checks

### Intent Lock: Phase 4

**Source of truth**:
- generated output contracts from phases 1-3

**Must**:
- test all `cli_mode` values
- verify script entry behavior by mode
- verify CLI help for enabled modes

**Must Not**:
- do not rely only on one-mode smoke tests

**Acceptance criteria**:
- tests pass for all mode combinations in scope

**Non-goals**:
- end-to-end CI pipeline testing in template repo

**Required tests/gates**:
- `uv run pytest tests/generation/test_copy_matrix.py`

### Intent Lock: Phase 5

**Source of truth**:
- generated template behavior and README instructions

**Must**:
- provide copy/paste quickstart commands
- include example generation commands for all three modes

**Must Not**:
- do not claim features outside minimal template scope

**Acceptance criteria**:
- README clearly documents mode behavior and resulting files

**Non-goals**:
- packaging/publishing automation

**Required tests/gates**:
- manual command walkthrough in README is runnable

## STEP-BY-STEP TASKS

### Phase 1

- **CREATE** `copier.yml` with required questions and defaults.
- **DEFINE** conditional rendering rules for CLI and `.ai` bundles.

### Phase 2

- **CREATE** minimal template files for base project.
- **ADD** conditional `cli.py` and CLI tests for `command|repl` modes only.
- **ADD** conditional `project.scripts` stanza in `pyproject.toml`.
- **UPDATE** `repl` mode to use `textual` for REPL runtime instead of plain `input()` loop.

## Plan Patch

### 2026-03-03 — Repl Backend Change Request

Scope adjustment requested during execution:
- Replace plain stdin loop in `cli_mode=repl` with a Textual-backed REPL surface.

Impact:
- `template/repl/pyproject.toml.jinja` adds `textual` dependency.
- `template/repl/src/{{ package_name }}/cli.py.jinja` launches a minimal `Textual` app in `repl` command.
- `template/repl/README.md.jinja` documents Textual usage.

### 2026-03-03 — Full Commands + Status-Sync Structure

Scope adjustment requested during execution:
- Include the full `.ai/COMMANDS` set in generated projects (genericized), not only the minimal subset.
- Adopt status-sync style file structure in generated projects so status workflows are first-class.

Impact:
- Expand template `.ai/COMMANDS` bundle to include all command docs from Lily command surface (genericized).
- Add status-sync documentation surfaces under `docs/dev/`:
  - `docs/dev/status.md`
  - `docs/dev/roadmap.md`
  - `docs/dev/debt/debt_tracker.md`
  - `docs/dev/plans/README.md`
- Add project commands/scripts for status flow:
  - `just status`
  - `just docs-check`
  - `just status-ready`
  - `scripts/status_report.py`
  - `scripts/validate_docs_frontmatter.py`
- Keep `.ai/PLANS/*` excluded.

### 2026-03-03 — Collapse Mode-Split Template Layout

Scope adjustment requested during execution:
- Replace duplicated `template/none`, `template/command`, and `template/repl` trees with a single `template/` root.

Impact:
- Use Jinja conditionals in shared files (`README`, `pyproject`, `cli.py`, `test_cli.py`) for mode differences.
- Use Copier `_tasks` to prune CLI files for `cli_mode=none`.
- Keep one shared status-sync docs/scripts bundle and one shared `.ai` command bundle.
- Preserve existing behavior for all modes and `include_ai_workflow` toggle.

### Phase 3

- **CREATE** generic `.ai` docs templates.
- **ADD** include/exclude logic for `.ai` bundle.
- **ENSURE** `.ai/PLANS/*` is never generated.

### Phase 4

- **CREATE** `tests/generation/test_copy_matrix.py`.
- **ASSERT** file matrix and CLI invocation behavior for each mode.

### Phase 5

- **UPDATE** template README with mode-specific usage examples.
- **RUN** generation checks and record outcomes.

## Required Tests and Gates

Template repo gates:
- `uv run pytest tests/generation/test_copy_matrix.py`

Generated project checks:
- `none` mode:
  - no `src/<package>/cli.py`
  - no `[project.scripts]` entry
- `command` mode:
  - `uv run <cli_name> hello`
- `repl` mode:
  - `uv run <cli_name> repl`

Optional workflow checks:
- with `include_ai_workflow=false`: no `.ai/` directory
- with `include_ai_workflow=true`: `.ai/COMMANDS`, `.ai/REF`, `.ai/RULES.md`, `.ai/HUMAN_RUNBOOK.md`

## Definition of Visible Done

A human can directly verify:
1. Copier asks for `cli_mode` and supports `none`, `command`, `repl`.
2. `none` mode generates no CLI app and no script entry.
3. `command` mode generates a Typer CLI with a working `hello` command.
4. `repl` mode generates a Typer CLI with a working `repl` command.
5. `.ai` docs are optional and generic; no Lily plan files are included.

## Input/Resource Provenance

- Requirements provenance: user clarifications in this discussion.
- Mechanics provenance: official Copier docs.
- No Lily domain code or plan artifacts are intended for template output.

## Execution Report

### 2026-03-03 — Phase 1

- Completion status: Completed (Phase 1 only)
- Files created in `~/workspace/tools/seedling`:
  - `copier.yml`
  - `README.md`
  - `template/` (placeholder directory for upcoming template files)
- Phase tasks completed:
  - Created Copier questionnaire with required fields:
    - `project_name`, `project_slug`, `package_name`
    - `cli_mode` (`none|command|repl`)
    - conditional `cli_name` (`when: cli_mode != none`)
    - `include_ai_workflow`
  - Defined conditional rendering toggles:
    - `cli_enabled = cli_mode != none`
    - `cli_has_repl = cli_mode == repl`
- Commands run and outcomes:
  - `uvx copier copy . <tmp-none> ... -d cli_mode=none ...` -> pass
  - `uvx copier copy . <tmp-command> ... -d cli_mode=command ...` -> pass
  - `uvx copier copy . <tmp-repl> ... -d cli_mode=repl ...` -> pass
- Notes:
  - Template file implementation is intentionally deferred to Phase 2.

### 2026-03-03 — Phase 2

- Completion status: Completed (Phase 2 only)
- Files created/updated in `~/workspace/tools/seedling`:
  - `copier.yml` (updated to mode-specific `_subdirectory`)
  - `template/none/README.md.jinja`
  - `template/none/pyproject.toml.jinja`
  - `template/none/src/{{ package_name }}/__init__.py.jinja`
  - `template/command/README.md.jinja`
  - `template/command/pyproject.toml.jinja`
  - `template/command/src/{{ package_name }}/__init__.py.jinja`
  - `template/command/src/{{ package_name }}/cli.py.jinja`
  - `template/command/tests/unit/test_cli.py.jinja`
  - `template/repl/README.md.jinja`
  - `template/repl/pyproject.toml.jinja`
  - `template/repl/src/{{ package_name }}/__init__.py.jinja`
  - `template/repl/src/{{ package_name }}/cli.py.jinja`
  - `template/repl/tests/unit/test_cli.py.jinja`
- Acceptance evidence:
  - `none` mode render: `pyproject.toml` has no `[project.scripts]`; no `src/<package>/cli.py`.
  - `command` mode render: CLI file/test generated; `uv run <cli_name> hello` succeeds.
  - `repl` mode render: CLI file/test generated; `uv run <cli_name> --help` lists `hello` and `repl`.
  - `repl` command implementation now uses `Textual` app runtime instead of plain stdin loop.
- Commands run and outcomes:
  - `uvx copier copy . <tmp-none> ... -d cli_mode=none ...` -> pass
  - `uvx copier copy . <tmp-command> ... -d cli_mode=command ...` -> pass
  - `uvx copier copy . <tmp-repl> ... -d cli_mode=repl ...` -> pass
  - `uv run commandapp hello` (generated command-mode project) -> pass
  - `uv run replapp --help` (generated repl-mode project) -> pass
  - `uv run repltext --help` (generated repl-mode project with textual backend) -> pass
  - `uv run repltext hello` (generated repl-mode project with textual backend) -> pass

### 2026-03-03 — Phase 3

- Completion status: Completed (Phase 3 only)
- Files created/updated in `~/workspace/tools/seedling`:
  - `copier.yml` (kept `_tasks` toggle for `.ai` removal when disabled)
  - `template/<mode>/.ai/COMMANDS/*` full generic command bundle for `none|command|repl`
  - `template/<mode>/.ai/COMMANDS/_shared/*` shared checklists for `none|command|repl`
  - `.ai/REF/README.md`
  - `.ai/RULES.md`
  - `.ai/HUMAN_RUNBOOK.md`
  - `template/<mode>/docs/README.md`
  - `template/<mode>/docs/dev/status.md`
  - `template/<mode>/docs/dev/roadmap.md`
  - `template/<mode>/docs/dev/debt/debt_tracker.md`
  - `template/<mode>/docs/dev/plans/README.md`
  - `template/<mode>/scripts/status_report.py`
  - `template/<mode>/scripts/validate_docs_frontmatter.py`
  - `template/<mode>/justfile`
- Acceptance evidence:
  - `include_ai_workflow=true` render includes `.ai/COMMANDS`, `.ai/REF`, `.ai/RULES.md`, `.ai/HUMAN_RUNBOOK.md`.
  - `include_ai_workflow=false` render removes `.ai` directory via post-copy task.
  - generated projects include status-sync docs structure under `docs/dev/` in all modes.
  - generated projects provide `just docs-check`, `just status`, and `just status-ready`.
  - No `.ai/PLANS` present in either render.
- Commands run and outcomes:
  - `uvx copier copy ... -d include_ai_workflow=true` -> pass
  - `uvx copier copy ... -d include_ai_workflow=false` -> pass
  - Presence/absence assertions for `.ai` and `.ai/PLANS` -> pass
  - `just status-ready` in generated projects (`include_ai_workflow=true` and `false`) -> pass
  - `just test` in generated projects (`command` and `none`) -> pass

### 2026-03-03 — Template Consolidation Execution

- Completion status: Completed (layout consolidation)
- Changes:
  - Collapsed template structure to single `template/` root.
  - Updated `copier.yml`:
    - `_subdirectory: template`
    - `_tasks` retains `.ai` toggle and adds `cli_mode=none` pruning task for `cli.py` and `test_cli.py`.
  - Replaced mode-specific duplicated files with shared conditionals:
    - `template/README.md.jinja`
    - `template/pyproject.toml.jinja`
    - `template/src/{{ package_name }}/cli.py.jinja`
    - `template/tests/unit/test_cli.py.jinja`
    - `template/tests/unit/test_smoke.py.jinja`
- Validation evidence:
  - `none` mode: no `cli.py`, no `[project.scripts]`, `just status-ready`, `just test` -> pass
  - `command` mode: `uv run <cli_name> hello`, `just status-ready`, `just test` -> pass
  - `repl` mode: help lists `hello` + `repl`, `just status-ready`, `just test` -> pass
  - `include_ai_workflow=false`: `.ai` removed while docs/status surfaces remain -> pass

### 2026-03-03 — Phase 4

- Completion status: Completed (Phase 4 only)
- Files created/updated in `~/workspace/tools/seedling`:
  - `tests/generation/test_copy_matrix.py`
- Acceptance evidence:
  - Matrix coverage implemented for `cli_mode=none|command|repl`.
  - `none` assertions: no `src/<package>/cli.py`, no `tests/unit/test_cli.py`, no `[project.scripts]`.
  - `command` assertions: script entry exists and `uv run <cli_name> hello --name matrix` succeeds.
  - `repl` assertions: script entry exists, root help includes `repl`, and `repl --help` works.
  - AI toggle assertions: `include_ai_workflow=true` includes `.ai` core bundle; `false` removes `.ai`; `.ai/PLANS` absent.
- Commands run and outcomes:
  - `uv run --with pytest --with copier pytest tests/generation/test_copy_matrix.py -q` -> pass (`4 passed`)

### 2026-03-03 — Phase 5

- Completion status: Completed (Phase 5 only)
- Files created/updated in `~/workspace/tools/seedling`:
  - `README.md`
- Acceptance evidence:
  - Added copy/paste quickstart and non-interactive generation commands for:
    - `cli_mode=none`
    - `cli_mode=command`
    - `cli_mode=repl`
  - Added documented minimal-profile example (`justfile_targets=[]`, `include_ai_workflow=false`).
  - Walkthrough commands from README executed successfully against fresh temp outputs.
- Commands run and outcomes:
  - `uv run --with copier copier copy . /tmp/seedling-none ... -d cli_mode=none ...` -> pass
  - `(cd /tmp/seedling-none && uv run pytest -q)` -> pass
  - `uv run --with copier copier copy . /tmp/seedling-command ... -d cli_mode=command ...` -> pass
  - `(cd /tmp/seedling-command && uv run commanddemo hello --name matrix)` -> pass
  - `uv run --with copier copier copy . /tmp/seedling-repl ... -d cli_mode=repl ...` -> pass
  - `(cd /tmp/seedling-repl && uv run repldemo --help)` -> pass
  - `(cd /tmp/seedling-repl && uv run repldemo repl --help)` -> pass
  - `uv run --with copier copier copy . /tmp/seedling-minimal ... -d justfile_targets='[]' -d include_ai_workflow=false ...` -> pass
  - `uv run --with pytest --with copier pytest tests/generation/test_copy_matrix.py -q` -> pass (`5 passed`)
