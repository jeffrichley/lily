# Quality upgrade ideas (from chrona-network comparison)

Comparison of **chrona-network** quality setup vs **lily**. Items below are things lily could add or tighten; no changes have been applied.

---

## 1. Pre-commit hooks

**Chrona:** `.pre-commit-config.yaml` with:
- `pre-commit-hooks`: check-added-large-files, check-merge-conflict, trailing-whitespace, end-of-file-fixer, check-case-conflict, check-docstring-first, check-illegal-windows-names, check-json, check-toml, check-yaml, debug-statements, detect-private-key
- `pygrep-hooks`: python-check-blanket-noqa
- `ruff` + `ruff-format` (scoped to `packages|apps`; for lily would be `src|tests` or `.`)
- `yesqa` (remove obsolete noqa)
- `commitizen` on commit-msg (optional)

**Lily:** None.

**Action:** Add `.pre-commit-config.yaml` and document `pre-commit install` (and optionally `--hook-type commit-msg`) in README or justfile.

---

## 2. GitHub Actions CI

**Chrona:** `.github/workflows/ci.yml` — matrix (ubuntu, macos, windows × py3.13), then: ruff check, ruff format --check, mypy, pytest with coverage (--cov-fail-under=80), pip-audit, xenon, vulture, darglint, bandit, radon.

**Lily:** No `.github/` workflows.

**Action:** Add `.github/workflows/ci.yml` that runs at least: ruff check, ruff format --check, mypy, pytest with coverage. Optionally add pip-audit and other checks once they are in the project.

---

## 3. Dependabot

**Chrona:** `.github/dependabot.yml` — weekly updates for `uv` and `github-actions`.

**Lily:** None.

**Action:** Add `.github/dependabot.yml` for uv (and github-actions if CI is added).

---

## 4. Pull request template

**Chrona:** `.github/pull_request_template.md` — summary, type of change, scope, how tested, reviewer focus, checklist (e.g. `just quality` passes, tests, docs).

**Lily:** None.

**Action:** Add `.github/pull_request_template.md` tailored to lily (e.g. `just quality`, tests, scope).

---

## 5. Ruff configuration

**Chrona:** Full `[tool.ruff]` in pyproject: line-length 88, target-version py313, src/exclude, format (quote-style, indent-style, etc.), lint select (E, F, I, N, B, Q, SIM, C90, ARG, TID, UP, PL, PERF, D, ANN, RUF), per-file-ignores for tests (docstrings, magic values) and specific files, pydocstyle convention google, flake8-tidy-imports ban-relative-imports.

**Lily:** No `[tool.ruff]`; ruff runs with defaults.

**Action:** Add `[tool.ruff]` (and optionally `[tool.ruff.format]` / `[tool.ruff.lint]`) to `pyproject.toml` with src = `["src", "tests"]`, select rules, and per-file-ignores for `tests/**` (e.g. relax D* and PLR2004).

---

## 6. Pyright

**Chrona:** Root `pyrightconfig.json` and `[tool.pyright]` in pyproject (venvPath, stubPath, typeCheckingMode basic, reportMissingImports error, executionEnvironments for packages).

**Lily:** No Pyright.

**Action:** Optional. Add `pyright` to dev deps and `[tool.pyright]` (and/or `pyrightconfig.json`) if you want IDE/CI type checking in addition to mypy.

---

## 7. Mypy strictness and plugins

**Chrona:** `strict = true`, `plugins = ["pydantic.mypy"]`, `warn_return_any`, `warn_unused_ignores`, and `[[tool.mypy.overrides]]` for third-party modules without stubs.

**Lily:** `disallow_untyped_defs = false`, no pydantic plugin, no overrides.

**Action:** Enable `pydantic.mypy` plugin (lily uses pydantic). Consider tightening to `strict = true` or stepwise (e.g. `disallow_untyped_defs = true`) and adding overrides for any untyped deps.

---

## 8. Coverage thresholds and report

**Chrona:** `fail_under = 80`, `show_missing = true`, `[tool.coverage.html] directory = "htmlcov"`.

**Lily:** No `fail_under`, no `show_missing`, no html directory set.

**Action:** Add `fail_under` (e.g. 80) and `show_missing = true` under `[tool.coverage.report]`; optionally set html directory. Ensure CI runs coverage with `--cov-fail-under=...` if CI is added.

---

## 9. Complexity (Xenon)

**Chrona:** Dev dep `xenon`, `[tool.xenon]` max-absolute B, max-modules/max-average A; CI and justfile run `xenon`.

**Lily:** None.

**Action:** Optional. Add `xenon` to dev deps, `[tool.xenon]` in pyproject, and a `just complexity` (and include in `just quality` / CI if desired).

---

## 10. Dead code (Vulture)

**Chrona:** Dev dep `vulture`, `[tool.vulture]` paths, exclude, min_confidence 80, ignore_names for protocol/interface names.

**Lily:** None.

**Action:** Optional. Add `vulture` and config; add `just vulture` and optionally to CI/quality.

---

## 11. Docstring correctness (Darglint)

**Chrona:** Dev dep `darglint`; CI and justfile run `darglint -s google -z full` on source dirs.

**Lily:** None.

**Action:** Optional. Add `darglint` and run on `src/lily` (e.g. `-s google`); add to `just quality` / CI if you want docstring-args consistency.

---

## 12. Security (Bandit + pip-audit)

**Chrona:** Dev deps `bandit[toml]`, `pip-audit`; `[tool.bandit]` exclude_dirs and skips (e.g. B101 for assert in tests); CI runs both; justfile has `audit` and `bandit`.

**Lily:** None.

**Action:** Optional. Add `pip-audit` and `bandit` to dev deps; add `just audit` and `just bandit`; run in CI if you want security gates.

---

## 13. Maintainability (Radon)

**Chrona:** Dev deps `radon`; CI runs `radon mi ... -n C` (maintainability index).

**Lily:** None.

**Action:** Optional. Add `radon` and a radon step in CI or `just quality` for maintainability metrics.

---

## 14. Commit convention (Commitizen)

**Chrona:** Dev dep `commitizen`, `[tool.commitizen]` (conventional commits, version in pyproject); commit-msg hook; `just commit` / `just commit-check`; Release Please workflow (optional).

**Lily:** None.

**Action:** Optional. Add Commitizen and commit-msg hook if you want enforced conventional commits and optional release automation.

---

## 15. Justfile quality targets

**Chrona:** `just quality` = lint, format-check, typecheck, complexity, vulture, darglint, bandit, radon, test (no auto-fix). `just quality-fix` = lint-fix, format, then same checks. Separate `lint` / `lint-fix` / `format` / `format-check` / `typecheck` / `test` / `test-cov` / `test-fast` / `audit` / `bandit` / `complexity` / `vulture` / `darglint` / `radon`; `pre-commit-install` and `pre-commit-run`.

**Lily:** `just quality` runs ruff format (fix), ruff check --fix, mypy (all fix-in-place; no “check only” gate). `just test` and `just test-cov`.

**Action:** Add `format-check` (ruff format --check) and a “check only” quality path (e.g. `just quality-check`) that does not modify files; keep `just quality` or `just quality-fix` for fix + run checks. Add any of the optional justfile commands (audit, bandit, complexity, vulture, darglint, radon, pre-commit-install, pre-commit-run) if you add those tools.

---

## 16. AGENTS.md / contributor rules

**Chrona:** `AGENTS.md` with rules for imports, typing (mypy, protocols), security (bandit), tests (tmp_path, import-mode), tooling workflow (just quality-fix), darglint, etc.

**Lily:** None.

**Action:** Optional. Add `AGENTS.md` (or similar) with project-specific rules for typing, testing, and running quality so humans and agents stay consistent.

---

## 17. Pytest options

**Chrona:** addopts: `-v`, `--tb=short`, `--strict-markers`, `-n auto` (xdist), `--import-mode=importlib`; minversion 8; filterwarnings for benchmark; pythonpath for workspace packages.

**Lily:** testpaths, pythonpath, markers; no addopts, no strict-markers, no xdist.

**Action:** Consider `--strict-markers` and, if tests grow, `-n auto` and `--import-mode=importlib`. Add minversion if you rely on a minimum pytest version.

---

## 18. Type stubs

**Chrona:** `stubs/` for docker, pytest_benchmark, skia, soundfile, typer; pyright/mypy stubPath/mypy_path.

**Lily:** None.

**Action:** Add stubs only if you have untyped dependencies that need them; otherwise use `types-*` packages or mypy overrides.

---

## 19. Editor / IDE

**Chrona:** `.vscode/settings.json` with Python interpreter path and `python.analysis.extraPaths` for workspace packages; `.devcontainer` for containerized dev.

**Lily:** No .vscode or .devcontainer in the listing.

**Action:** Optional. Add `.vscode/settings.json` (e.g. interpreter, extraPaths for `src`) and/or .devcontainer if you standardize on them.

---

## 20. Docstring coverage (docstr-coverage)

**Chrona:** Dev dep `docstr-coverage` (not wired in the snippets seen; can be run manually or in CI).

**Lily:** None.

**Action:** Optional. Add `docstr-coverage` and a target/CI step if you want to enforce docstring coverage on public API.

---

## Summary table

| Area              | Chrona-network                    | Lily (current)              |
|-------------------|-----------------------------------|-----------------------------|
| Pre-commit        | Yes (hooks, ruff, yesqa, commitizen) | No                          |
| CI                | Yes (multi-OS, full quality gate) | No                          |
| Dependabot        | Yes                               | No                          |
| PR template       | Yes                               | No                          |
| Ruff config       | Full (rules, per-file, pydocstyle) | Defaults only               |
| Pyright           | Yes                               | No                          |
| Mypy              | Strict, pydantic plugin, overrides | Relaxed, no plugin/overrides |
| Coverage          | fail_under 80, show_missing       | No threshold, no show_missing |
| Xenon             | Yes                               | No                          |
| Vulture           | Yes                               | No                          |
| Darglint          | Yes                               | No                          |
| Bandit / pip-audit| Yes                               | No                          |
| Radon             | Yes                               | No                          |
| Commitizen        | Yes                               | No                          |
| Justfile          | quality (check-only) + quality-fix | quality (fix only)          |
| AGENTS.md         | Yes                               | No                          |
| Pytest            | strict-markers, xdist, importlib  | Basic                       |
| Stubs             | Yes (stubs/)                      | No                          |

---

*Do not execute adding:* this file is a planning list only; implement items as needed.
