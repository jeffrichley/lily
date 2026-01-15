# Justfile Targets Contract

**Feature**: Documentation Site Infrastructure  
**Date**: 2026-01-15  
**Type**: Command Interface Contract

## Overview

This contract defines the justfile targets that provide access to MkDocs functionality for documentation site development and building.

## Target: `docs-serve`

**Purpose**: Start local development server for documentation site with live reload

**Command**: `just docs-serve`

**Implementation**:
```just
docs-serve:
    uv run mkdocs serve
```

**Behavior**:
- Starts MkDocs development server (default: http://127.0.0.1:8000)
- Watches docs/ directory for file changes
- Automatically regenerates site when files change
- Serves site at configured port (default 8000)
- Runs until interrupted (Ctrl+C)

**Prerequisites**:
- MkDocs dependencies installed (`uv sync --group docs`)
- `mkdocs.yml` configuration file exists
- `docs/` directory exists with at least `index.md`

**Success Criteria**:
- Server starts without errors
- Site is accessible at http://127.0.0.1:8000
- File changes trigger automatic regeneration
- Browser shows updated content after regeneration

**Error Handling**:
- If mkdocs.yml is invalid: Server fails to start with configuration error
- If docs/ directory missing: Server fails with directory error
- If dependencies missing: `uv run` fails with package not found error

## Target: `docs-build`

**Purpose**: Build static documentation site for deployment

**Command**: `just docs-build`

**Implementation**:
```just
docs-build:
    uv run mkdocs build
```

**Behavior**:
- Reads mkdocs.yml configuration
- Processes all Markdown files in docs/ directory
- Generates static HTML site in `site/` directory
- Creates search index (search/search_index.json)
- Outputs site ready for deployment

**Prerequisites**:
- MkDocs dependencies installed (`uv sync --group docs`)
- `mkdocs.yml` configuration file exists
- `docs/` directory exists with documentation files

**Success Criteria**:
- Build completes without errors
- `site/` directory contains generated HTML files
- All Markdown files are converted to HTML
- Search index is generated
- Site can be opened in browser (file:// or via web server)

**Error Handling**:
- If mkdocs.yml is invalid: Build fails with configuration error
- If Markdown files have syntax errors: Build fails with file-specific error
- If dependencies missing: `uv run` fails with package not found error
- If site/ directory write fails: Build fails with permission error

**Output**:
- `site/` directory with generated static site
- Directory structure mirrors docs/ structure
- All assets (CSS, JS, images) included

## Optional: `docs-clean`

**Purpose**: Remove generated site directory

**Command**: `just docs-clean` (optional, not required by spec)

**Implementation** (if added):
```just
docs-clean:
    rm -rf site/
```

**Behavior**:
- Deletes `site/` directory and all contents
- Useful for clean rebuilds

## Contract Guarantees

1. **Consistency**: Targets use `uv run` to ensure correct dependency versions
2. **Error Visibility**: All errors are displayed to user with clear messages
3. **Standard Workflow**: Targets follow standard MkDocs usage patterns
4. **Integration**: Targets integrate seamlessly with existing justfile structure

## Usage Examples

**Local Development**:
```bash
just docs-serve
# Open http://127.0.0.1:8000 in browser
# Edit docs/*.md files
# Changes appear automatically
```

**Build for Deployment**:
```bash
just docs-build
# site/ directory contains deployable static site
```

