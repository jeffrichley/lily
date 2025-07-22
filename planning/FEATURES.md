# 🌸 Lily – FEATURES.md

This document enumerates all major and minor features that Lily will support, grouped by subsystem. Each feature includes a rich description, status indicator, supported personas, and tags for implementation scope and categorization. These features span Lily’s core AI orchestration engine, user interfaces, modular extension system, voice interaction pipeline, research augmentation tools, and media generation workflows.

---

## ✅ CORE SYSTEM

### 🧠 Skill Execution Engine

**Description:**
Lily can run individual skills defined as markdown prompt files, supporting structured front matter (name, tags, description, personas) and templated AI prompts. A skill may use the current project’s context, memory state, and persona to shape how the LLM responds. Skills are resolved from multiple layers (project-local, module, global) and may invoke tools (e.g., WhisperFlow, file search).
**Status:** planned
**Supported Personas:** all
**Tags:** \[core] \[skills] \[engine] \[LLM] \[tools]

### 🔁 Flow Orchestration

**Description:**
Lily supports declarative `flow.yaml` files that define sequences of skills to run. Each step may pass structured output to the next, allowing outputs of summarization to be used in tweet generation, for example. Flows support persona-aware execution, conditional branching (future), and logging. Flows can be user-defined or installed via modules.
**Status:** planned
**Supported Personas:** all
**Tags:** \[core] \[flows] \[workflow] \[composability]

### 🗃 Skill Resolution Hierarchy

**Description:**
Lily resolves skills in a strict override chain: `.lily/skills/ → modules/*/skills/ → ~/.lily/skills/`. She allows module-specific namespacing and can detect shadowed skills. A registry indexes all discovered skills with metadata, enabling fuzzy search, autocompletion, and invocation via TUI/CLI.
**Status:** planned
**Supported Personas:** all
**Tags:** \[core] \[skills] \[filesystem] \[registry]

### 🧩 Extension Module Loader

**Description:**
Modules are installable bundles that add new skills, flows, rules, memory profiles, or tools. Lily can load modules from the global user directory (`~/.lily/modules/`) or project-local `.lily/modules/`. Each module declares its skills and flows in standard locations and can export metadata for indexing and UI presentation.
**Status:** planned
**Supported Personas:** all
**Tags:** \[core] \[modules] \[extensibility] \[UX]

### 🧠 Persona-Aware Prompting

**Description:**
Each persona (e.g., Dev, Life, Research, Chrona) defines tone, role, memory strategy, and optional tools. Skills and flows can specify which personas they support. Lily injects persona metadata into prompt construction, memory indexing, and execution context. Persona switching may be manual (`lily persona switch research`) or inferred from project metadata.
**Status:** planned
**Supported Personas:** all
**Tags:** \[core] \[personas] \[prompting] \[memory]

### 🧠 Project Awareness via `.lily/project.yaml`

**Description:**
Lily auto-detects project context by walking upward from the working directory to find `.lily/project.yaml`. This file defines the project name, default persona, included modules, memory profile, and skill overrides. Higher-level `.lily/` directories can define shared configs that cascade into deeper projects, supporting DRY conventions for multi-project workflows.
**Status:** planned
**Supported Personas:** all
**Tags:** \[core] \[projects] \[context] \[configuration]

---

## 💬 VOICE INTERACTION

### 🎙️ WhisperFlow Input Integration

**Description:**
Lily integrates WhisperFlow to transcribe user speech into markdown inputs, which are then interpreted as task prompts. Voice tasks may be short-form (“Summarize the paper I read yesterday”) or invoke full flows (“Create a script from the latest podcast and post a tweet”). Lily may support both push-to-talk CLI and always-on GUI microphone modes.
**Status:** planned
**Supported Personas:** life, research, chrona
**Tags:** \[voice] \[input] \[UX] \[tools]

### 🔊 TTS Output Agent

**Description:**
Lily can speak replies aloud using a selected TTS backend (e.g., Coqui or ElevenLabs). Output may be the result summary, a conversational acknowledgment, or synthesized flow output (e.g., a news anchor voice reading a video script). Voice selection, playback volume, and auto-reply toggling are configurable by persona or mode.
**Status:** planned
**Supported Personas:** life, chrona
**Tags:** \[voice] \[output] \[tts] \[audio]

---

## 🖥️ CLI / TUI / GUI

### 💻 CLI Command System

**Description:**
Lily exposes commands like `lily run summarize`, `lily run-flow daily_digest`, `lily skills`, `lily modules`, and `lily persona switch`. CLI output includes markdown previews, error messages, and rework triggers. Optional Bash autocomplete is supported.
**Status:** planned
**Supported Personas:** all
**Tags:** \[cli] \[interface] \[developer]

### 🧮 Kanban-Style Terminal UI

**Description:**
Lily’s TUI shows all active and archived tasks in emoji-decorated columns (📝 Todo, 🔄 In Progress, ✅ Complete, ♻️ Needs Rework). Each task expands into a right-side detail panel showing `initial.md`, `result.md`, associated flow or skill, and logs.
**Status:** planned
**Supported Personas:** all
**Tags:** \[tui] \[UI] \[productivity]

### 📑 Right-Side Context Panel

**Description:**
Context panel in the TUI displays the current task file, memory summary, persona, and skill or flow structure. Allows scrolling, editing, approval, or voice playback. May include metadata such as effort type (quick, immersive).
**Status:** planned
**Supported Personas:** all
**Tags:** \[tui] \[UX] \[context]

### 🧠 Flow Composer GUI (Future)

**Description:**
Future web or GUI interface that allows visual drag-and-drop construction of flows by connecting skills. May include preview runners, persona selectors, and flow templates (e.g., “Summarize + Reflect + Tweet”).
**Status:** future
**Supported Personas:** all
**Tags:** \[gui] \[flows] \[visual] \[creator-tools]

---

## 🎓 PH.D / RESEARCH MODULE

### 📚 Summarize Paper Skill

**Description:**
Summarizes academic papers into structured sections: Abstract Summary, Key Claims, Evidence Presented, Methodology Notes, and Citations. May work from raw text, PDF, or parsed BibTeX. Optionally links to memory for citation tracking.
**Status:** planned
**Supported Personas:** research
**Tags:** \[research] \[skills] \[academic] \[pdf]

### 📘 Literature Review Flow

**Description:**
Executes a full literature review flow across multiple sources: summarize each paper → compare themes → cluster insights → synthesize narrative. Supports markdown export with headings and bibliography placeholder.
**Status:** planned
**Supported Personas:** research
**Tags:** \[research] \[flows] \[phd] \[longform]

### 🧠 Citation Tracker

**Description:**
Parses references from markdown or BibTeX. Builds a project-local `citations.yaml` index. Can auto-link citation mentions, suggest missing citations, and help build the final references section.
**Status:** planned
**Supported Personas:** research
**Tags:** \[research] \[tools] \[memory] \[bibliography]

---

## 🎬 CHRONA MODULE

### 🎞 Transcribe + Summarize Video Flow

**Description:**
Runs WhisperFlow → summarize → extract quotes → draft script → prep video. Optimized for 9:16 or 16:9 input. Used in influencer/shorts production.
**Status:** planned
**Supported Personas:** chrona
**Tags:** \[chrona] \[flows] \[media] \[video] \[voice]

### 🧙 Scriptwriter Skill

**Description:**
Turns transcript or idea summaries into full scripts, with support for narrator tone, beat pacing, and persona-based voice tuning. Optionally outputs thread-ready files.
**Status:** planned
**Supported Personas:** chrona
**Tags:** \[chrona] \[skills] \[voice] \[scripting]

### 🎛 Media-Ready Thread Generator

**Description:**
Generates detailed `thread.md` files for media workflows (e.g., “Render a 30s inspirational video from this script”). Adds annotations for tools (voice, music, video).
**Status:** planned
**Supported Personas:** chrona
**Tags:** \[chrona] \[UX] \[prompting] \[agents]

---

## 🔧 UTILITIES & INFRASTRUCTURE

### 🧠 Memory Profile Loader

**Description:**
Loads memory strategy per persona or task type: e.g., short-term, recursive summarization, citation-linked. Skills or flows can request memory behavior explicitly.
**Status:** planned
**Supported Personas:** all
**Tags:** \[infra] \[memory] \[strategy]

### 📂 Config Layer Merger

**Description:**
When detecting a project, Lily walks upward through parent folders to collect `.lily/project.yaml` files. These are merged bottom-up, allowing reusable persona/module/memory configs at org or workspace level.
**Status:** planned
**Supported Personas:** all
**Tags:** \[infra] \[filesystem] \[config] \[multi-project]

### 🔍 Skill / Flow / Task Search

**Description:**
Fuzzy-searchable index of skills, flows, and task templates. Used in CLI autocompletion, TUI quick actions, and GUI flow-builder palette.
**Status:** planned
**Supported Personas:** all
**Tags:** \[UX] \[navigation] \[search] \[developer]
