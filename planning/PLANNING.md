# 🌸 Lily – PLANNING.md

This document defines the architectural vision, interaction model, persona system, voice capabilities, memory structure, and module extensibility strategy for Lily.

---

## 🎯 1. Vision & Philosophy

Lily is an AI-native personal development assistant designed to:

* Execute structured **skills** and **flows** in markdown-defined workspaces
* Support voice-first, CLI/TUI-based task interaction
* Switch behavior and tone through a **persona** system
* Augment creative, technical, research, and life workflows
* Stay project-aware and context-sensitive through directory annotations

**Not** just a coding bot or prompt executor—Lily is an AI-first operating system for thought and action.

---

## 🏗️ 2. Architectural Overview

### 2.1. Petal Integration

Lily is built on the **Petal** framework (skills + flows + tool interfaces). It leverages Petal’s:

* Flow engine with typed state models
* Decorator-based skill/tool registration
* LangGraph and LangChain integration

### 2.2. Execution Loop

For every task (from CLI, voice, or TUI):

1. Resolve project context (see section 4)
2. Determine skill or flow to run
3. Apply active persona (inject prompt metadata)
4. Execute skill → produce result
5. Save output to `.lily/threads/<task>/result.md`
6. Update task tracker (in `.lily/FEATURES_LIST.md` or `.lily/tasks.db`)

Skills and flows can invoke external tools (via MCP), use memory profiles, or trigger voice replies.

---

## 🧠 3. Persona System

Personas are YAML-defined profiles located in `planning/PERSONAS.yaml`. Each persona defines:

* `name`: e.g., `life`, `research`, `chrona`, `dev`
* `llm_tone`: e.g., "warm & curious", "rigorous & academic"
* `voice_profile`: TTS voice ID (e.g., `iris`, `news_caster`, `mentor_voice`)
* `memory_profile`: link to a strategy defined in `config/memory/`
* `tools`: tool IDs enabled for this persona

Personas affect:

* Prompt phrasing and instruction sets
* Voice style and audio output
* Memory behavior (e.g., journaling vs technical retrieval)
* Flow logic (e.g., summarization depth)

Switch personas with:

```bash
lily persona switch chrona
```

Or infer from `.lily/project.yaml`

---

## 📁 4. Directory & Context Awareness

Lily detects where she is by looking for a `.lily/` directory. The resolution strategy:

* Start from `$PWD`
* Walk upward to root, collecting any `.lily/project.yaml` files
* Merge configs bottom-up with later overrides (project > module > org-wide)

### `.lily/project.yaml` schema:

```yaml
name: chrona-network
persona: chrona
modules:
  - chrona
  - research
skills:
  override:
    summarize: chrona.summarize_transcript
```

This allows for:

* Reusable module declarations
* Project-specific overrides
* Skill scoping via resolution chain:

  1. `.lily/skills/`
  2. `.lily/modules/*/skills/`
  3. `~/.lily/skills/`

---

## 🧩 5. Skill & Flow Registry

All skills must include front matter:

```yaml
---
name: summarize
description: Extracts summary and themes from long text.
personas: [life, research]
tags: [summarization, markdown]
kind: atomic
---
```

Flows live in `flows/*.yaml` or `modules/*/flows/*.yaml`, with structure:

```yaml
name: summarize_and_tweet
steps:
  - skill: summarize
  - skill: write_tweet
```

#### 🔁 Variable Injection Between Steps

Flow steps can reference previous outputs using Jinja-style syntax (`{{ step_id.result }}`). Supported variables:

- `{{ skill_name.result }}` — Output from named step
- `{{ memory.key }}` — Stored memory snapshot
- `{{ input }}` — Initial input passed into flow

Variables are resolved before skill invocation. Invalid or missing references will raise a resolution error.

Lily indexes all skills and flows at runtime. This index powers:

* CLI autocompletion (`lily run s...`)
* TUI skill palette
* GUI flow builder (future)

---

## 🧰 6. Tool Registry & Capability Schema

Each tool used by Lily must be registered and described with metadata, either via `tools/registry.yaml` or Python decorators with docstring metadata blocks.

Tool metadata includes:
- `name`: Unique identifier
- `description`: Short summary
- `inputs`: Expected parameters and types
- `outputs`: Return format or schema
- `personas`: Optional list of compatible personas
- `runtime`: MCP, CLI, API, or in-process Python

Tools are resolved in the same hierarchy as skills (project → module → global), and auto-indexed at startup.

Example YAML snippet:

```yaml
- name: whisperflow
  description: Transcribes audio to markdown text
  inputs: [audio_path]
  outputs: [markdown_transcript]
  runtime: mcp
  personas: [chrona, research]
```

---

## 🔊 7. Voice Interaction

### 7.1 WhisperFlow Input

WhisperFlow is used as a skill input pipeline:

* CLI: `lily voice record` starts capture
* Voice is transcribed → becomes `initial.md`
* Flow starts if recognized (“summarize this video”) or Lily asks for clarification

### 7.2 TTS Output

Output spoken using TTS backend defined in persona:

```yaml
voice_profile: iris
```

All `result.md` can optionally be read aloud, and system messages like "Flow completed" can use short-form synthesis.

---

## 📋 8. Task Lifecycle

Each task has a lifecycle managed via state labels:

```
[📝 todo] → [🔄 in_progress] → [✅ complete]
               ↓
         [♻️ needs_rework]
```

#### ♻️ Rework Triggering and Flow

Each skill or flow step may return a `rework_required: true` flag (either from LLM signal or validator tool). Lily will:
1. Mark the task as `♻️ Needs Rework`
2. Prompt user for correction (via CLI/TUI or voice)
3. Re-run the skill or offer to edit `initial.md`

Rework strategy can be declared in skill metadata:

```yaml
rework_strategy: "manual" | "auto_retry" | "suggest_fix"
```

If auto-retry is used, Lily may use a debug-style pattern to self-correct and reattempt.

Task status is tracked via:

* `.lily/FEATURES_LIST.md`
* TUI board
* Optional `tasks.db` for indexed views

All tasks contain:

* `initial.md`
* `thread.md`
* `result.md`
* `logs/`

---

## 🧠 9. Memory & Context

Memory is persona- and flow-sensitive.
Profiles are defined in `config/memory/*.yaml`:

* `shortform`: ephemeral memory
* `longform`: persistent summaries
* `citation_indexed`: maps citations to content snippets

Memory usage per skill:

* Read-only
* Writable
* Retrospective: re-reads prior `result.md` files for similar flows

---

## 🧩 10. Modules

Each module is a folder with:

```
modules/chrona/
├── skills/
├── flows/
├── memory/
├── config/
```

Modules can:

* Be symlinked or copied into `~/.lily/modules/`
* Declared in `.lily/project.yaml`
* Override skill names via namespacing

Modules must declare a `module.yaml` manifest:

```yaml
name: chrona
version: 0.1.0
includes:
  skills:
    - write_script
    - transcribe_video
  flows:
    - summarize_and_tweet
```

---

## 🧪 11. Execution Modes

Lily can operate in four user-facing modes:

| Mode  | Description                                      |
| ----- | ------------------------------------------------ |
| CLI   | Default terminal execution. `lily run summarize` |
| TUI   | Full terminal UI. Task list + context + palette  |
| Voice | WhisperFlow → Skill Flow → TTS reply             |
| GUI   | Flow builder (future). Drag-and-drop skills      |

#### 📦 Project Export & Archive System

Lily supports exporting `.lily/` project directories as snapshot bundles. Export targets include:
- All `initial.md`, `result.md`, `flow.yaml`, and persona memory
- Optional zip packaging
- Export to `archive/` or user-defined path

CLI command:
```bash
lily export --include result.md --to archive/
```

This supports collaboration, reproducibility, and long-term storage.

---

## 🔐 12. Guardrails (Future)

* Input validation: YAML, Markdown integrity
* Output checks: skill contracts must be fulfilled (non-empty sections, correct headers)
* Rework triggers: failed validations re-invoke skill with "fix mode"

#### ✅ Output Validation Layer

Lily supports post-run validation of `result.md` files.

Validation options:
- Markdown section headers required (e.g., `## Summary`, `## Quotes`)
- Regex checks for key phrases
- Length or format checks
- Tool-based semantic analysis (future)

Each skill may include a validator block in its front matter:

```yaml
validator:
  required_headers: ["## Summary", "## Key Quotes"]
  max_length: 800
  requires: ["AI-generated", "main point"]
```

---

## 🔌 13. Integrations

* 🧠 **WhisperFlow**: transcription engine for CLI and GUI
* 🎙 **Coqui / ElevenLabs**: TTS agents
* 📚 **BibTeX/PDF Parser**: Research document inputs
* 🎬 **Chrona Agents**: Used in `video_flow`, `scriptwriter`, etc.

---

This plan forms the foundation of Lily’s implementation roadmap and guarantees a modular, maintainable, voice-augmented system that is both developer-extensible and life-compatible.
