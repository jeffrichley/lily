.PHONY: help docs docs-clean docs-serve docs-linkcheck format lint test test-cov test-cov-check build install-dev checkit v vulture

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-dev:  ## Install development dependencies
	uv pip install -e ".[dev,docs]"

format:  ## Format code with black and ruff
	uv run black .
	uv run ruff check . --fix

lint:  ## Lint code with ruff
	uv run ruff check .

test:  ## Run tests
	uv run pytest tests/ -v

test-cov:  ## Run tests with coverage
	uv run pytest tests/ --cov=src/lily --cov-report=html --cov-report=term --cov-report=xml

test-cov-check:  ## Run tests with coverage and fail if below 80%
	uv run pytest tests/ --cov=src/lily --cov-report=term-missing --cov-fail-under=80

vulture:  ## Find dead code with vulture
	uv run vulture src/ tests/ --min-confidence 80

vulture-all:  ## Find all potential dead code with vulture (lower confidence)
	uv run vulture src/ tests/ --min-confidence 60

docs:  ## Build documentation
	cd docs && make html

docs-clean:  ## Clean documentation build
	cd docs && make clean

docs-serve:  ## Serve documentation locally
	cd docs && python -m http.server 8000 --directory build/html

docs-linkcheck:  ## Check documentation links
	cd docs && make linkcheck

docs-watch:  ## Watch for changes and rebuild documentation
	cd docs && sphinx-autobuild source build/html --port 8001 --open-browser

build:  ## Build the package
	uv build

# Documentation shortcuts
docs-build: docs  ## Alias for docs
docs-view: docs-serve  ## Alias for docs-serve

checkit:
	mypy src/ tests/
	pre-commit run --all-files
	$(MAKE) test-cov-check

precommit-autofix:
	pre-commit run --all-files
	git add .

v:  ## Activate virtual environment (Mac)
	@echo "Starting new shell with virtual environment activated..."
	@exec zsh -c "source .venv/bin/activate && exec zsh"
