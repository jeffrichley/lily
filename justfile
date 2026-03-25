# Justfile for Lily reboot baseline

# Windows uses PowerShell, Unix-like systems use sh
set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]
set shell := ["sh", "-cu"]

# Run all tests
test:
    uv run pytest -n auto

# Run end-to-end tests only
e2e:
    uv run pytest tests/e2e

# Run all tests with coverage report
test-cov:
    uv run pytest --cov=src/lily --cov-report=term-missing --cov-report=html

# Format code (ruff)
format:
    uv run ruff format src tests scripts

# Check formatting only (CI; no write)
format-check:
    uv run ruff format --check src tests scripts

# Lint and auto-fix (ruff)
lint:
    uv run ruff check --fix src tests scripts

# Lint check only (CI; no fix)
lint-check:
    uv run ruff check src tests scripts

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
# CVE-2026-4539 (pygments): no release >2.19.2 on PyPI yet; low-severity local ReDoS.
# Tracked: docs/dev/debt/debt_tracker.md (DEBT-017). Remove --ignore-vuln when upstream ships a fix.
audit:
    uv run pip-audit --ignore-vuln CVE-2026-4539

# Security: static analysis (bandit); config in pyproject.toml
bandit:
    uv run bandit -c pyproject.toml -r src

# Maintainability index (radon); fail if any module below C
radon:
    uv run radon mi src -n C

# Find duplicate code (pylint duplicate-code checker)
find-dupes:
    uv run pylint src/lily --disable=all --enable=duplicate-code --min-similarity-lines=10

# Install pre-commit hooks (run once). Includes commit-msg hook for conventional commits.
pre-commit-install:
    uv run pre-commit install
    uv run pre-commit install --hook-type commit-msg

# Run pre-commit on all files (useful to verify before pushing)
pre-commit:
    uv run pre-commit run --all-files

# Conventional commits: interactive commit (Commitizen)
commit:
    uv run cz commit

# Check that commit message(s) follow conventional commits
commit-check:
    uv run cz check

# Run full quality checks (format, lint, types, complexity, dead code, docs, security, maintainability)
quality: format lint types complexity vulture darglint audit bandit radon find-dupes docstr-coverage docs-check

# Check-only quality lane (CI-safe; no write)
quality-check: format-check lint-check types complexity vulture darglint audit bandit radon find-dupes docstr-coverage docs-check

# Lighter target for day-to-day reboot development
quality-dev: format lint types darglint

# Show one-command project/docs execution status summary.
status:
    uv run python scripts/status_report.py

# Run docs validation plus status summary in one command.
status-ready: docs-check status

# Validate docs frontmatter values and active-doc staleness.
docs-check:
    uv run python scripts/validate_docs_frontmatter.py --max-active-age-days 21

# Auto-add placeholder frontmatter to docs missing frontmatter.
docs-frontmatter-fix:
    uv run python scripts/validate_docs_frontmatter.py --fix --max-active-age-days 21
