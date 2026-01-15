# Justfile for Lily project

# Run all tests
test:
    uv run pytest

# Run all tests with coverage report
test-cov:
    uv run pytest --cov=src/lily --cov-report=term-missing --cov-report=html

# Run quality checks: ruff format (auto-fix), ruff check with auto-fix, and mypy
quality:
    uv run ruff format .
    uv run ruff check --fix .
    uv run mypy src/lily

# Serve documentation site locally
docs-serve:
    uv run mkdocs serve

# Build documentation site
docs-build:
    uv run mkdocs build

# Clean generated documentation site
docs-clean:
    rm -rf site/

