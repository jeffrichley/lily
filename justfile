# Justfile for Lily project

# Windows uses PowerShell, Unix-like systems use sh
set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]
set shell := ["sh", "-cu"]

# Run all tests
test:
    uv run pytest

# Run personality quality gates (Gate C / Phase 7)
eval-gates:
    uv run pytest tests/unit/evals/test_baseline.py tests/unit/evals/test_phase7_quality.py

# Regression eval lane (frozen contracts)
eval-regression:
    uv run pytest tests/unit/evals/test_baseline.py tests/unit/evals/test_phase7_quality.py

# Capability eval lane (memory migration behaviors)
eval-capability:
    uv run pytest tests/unit/evals/test_memory_migration_quality.py

# Performance eval lane (memory migration perf thresholds)
eval-performance:
    uv run pytest tests/unit/evals/test_memory_performance.py

# Run all tests with coverage report
test-cov:
    uv run pytest --cov=src/lily --cov-report=term-missing --cov-report=html

# Format code (ruff)
format:
    uv run ruff format .

# Check formatting only (CI; no write)
format-check:
    uv run ruff format --check .

# Lint and auto-fix (ruff)
lint:
    uv run ruff check --fix .

# Lint check only (CI; no fix)
lint-check:
    uv run ruff check .

# Type-check (mypy)
types:
    uv run mypy -p lily

# Complexity check (xenon): max-absolute B, max-modules A, max-average A
complexity:
    uv run xenon -b B -m A -a A src

# Dead-code check (vulture); config in pyproject.toml
vulture:
    uv run vulture

# Docstring correctness (darglint), Google style, full strictness
darglint:
    uv run darglint -s google -z full src

# Docstring coverage on public API (skip private, magic, __init__)
docstr-coverage:
    uv run docstr-coverage src --skip-private --skip-magic --skip-init -v 2

# Security: dependency vulnerabilities (pip-audit)
audit:
    uv run pip-audit

# Security: static analysis (bandit); config in pyproject.toml
bandit:
    uv run bandit -c pyproject.toml -r src

# Maintainability index (radon); fail if any module below C
radon:
    uv run radon mi src -n C

# Find duplicate code (pylint duplicate-code checker)
find-dupes:
    uv run pylint src/lily --disable=all --enable=duplicate-code --min-similarity-lines=10

# Conventional commits: interactive commit (Commitizen)
commit:
    uv run cz commit

# Check that commit message(s) follow conventional commits
commit-check:
    uv run cz check

# Install commit-msg hook to enforce conventional commits (run once). Requires scripts/install_commit_msg_hook.py.
# commit-hook-install:
#     uv run python scripts/install_commit_msg_hook.py

# Install pre-commit hooks (run once). Includes commit-msg hook for conventional commits.
pre-commit-install:
    uv run pre-commit install
    uv run pre-commit install --hook-type commit-msg

# Run pre-commit on all files (useful to verify before pushing)
pre-commit:
    uv run pre-commit run --all-files

# Run all quality checks (format, lint, types, complexity, vulture, darglint, audit, bandit, radon)
quality: format lint types complexity vulture darglint audit bandit radon find-dupes docstr-coverage

# Same gates as quality but check-only (no format write, no lint fix). Use in CI so PR fails if not clean.
quality-check: format-check lint-check types complexity vulture darglint audit bandit radon find-dupes docstr-coverage

# CI-ready aggregate gates: static checks + eval thresholds.
ci-gates: quality-check eval-gates

# Memory migration CI gate target.
memory-migration-gates: quality-check eval-regression eval-capability eval-performance

# Generate Phase 7 memory observability snapshot artifact.
memory-metrics-snapshot:
    uv run python scripts/generate_memory_metrics_snapshot.py

# --- Lighter targets for day-to-day dev ---
# Recommended while developing: format + lint + types. Fast except mypy; catches most issues.
quality-dev: format lint types darglint

# Run interactive CLI REPL (slash-command testing)
repl:
    uv run lily repl
