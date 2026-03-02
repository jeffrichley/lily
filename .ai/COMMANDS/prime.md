---
description: Prime agent with codebase understanding
---

# Prime: Load Project Context

## Objective

Build comprehensive understanding of the codebase by analyzing structure, documentation, and key files.

## Process

### 1. Analyze Project Structure

List all tracked files:
!`git ls-files`

Show directory structure:
On Linux, run: `tree -L 3 -I 'node_modules|__pycache__|.git|dist|build'`

### 2. Read Core Documentation

- Read spec docs from `.ai/SPECS/*/PRD.md` (if present) and any package-local `docs/PRD.md` files relevant to active work
- Read `AGENTS.md` and `.ai/RULES.md` for project-specific rules and conventions
- Read README files at project root and major directories
- Read any architecture documentation

### 3. Runtime Command Sanity Check

Confirm core developer/runtime commands available for this repo type:
- `uv` availability and package workflow compatibility
- `just` task runner availability
- language runtime invocation policy (`uv run python` preferred, `python3` fallback)
- any project-critical binaries (for example `ffmpeg`, `ffprobe`, `docker`, `node`, `go`)

### 4. Identify Key Files

Based on the structure, identify and read:
- Main entry points (main.py, index.ts, app.py, etc.)
- Core configuration files (pyproject.toml, package.json, tsconfig.json)
- Key model/schema definitions
- Important service or controller files

### 5. Understand Current State

Check recent activity:
!`git log -10 --oneline`

Check current branch and status:
!`git status`

## Output Report

Provide a concise summary covering:

### Project Overview
- Purpose and type of application
- Primary technologies and frameworks
- Current version/state

### Architecture
- Overall structure and organization
- Key architectural patterns identified
- Important directories and their purposes

### Tech Stack
- Languages and versions
- Frameworks and major libraries
- Build tools and package managers
- Testing frameworks

### Core Principles
- Code style and conventions observed
- Documentation standards
- Testing approach

### Current State
- Active branch
- Recent changes or development focus
- Any immediate observations or concerns
- Runtime/tooling readiness notes (what is available/missing)

**Make this summary easy to scan - use bullet points and clear headers.**
