# ✅ Lily – TODOS.md (High-Level Story Queue)

This file serves as a structured backlog of high-level development stories (similar to Agile epics or story cards). Each item represents a meaningful unit of work that will eventually link to a detailed markdown plan (e.g. `planning/stories/voice_pipeline.md`).

Features are grouped by subsystem and tagged for priority or module alignment.

---

## 🧠 CORE ENGINE

* [x] 🔍 **Skill registry and resolution** `[core]` — Create discovery system that indexes local, module, and global skills with override logic. ✅ **Completed 2025-07-22**
* [ ] 🔁 **Flow execution controller** `[core]` — Executes multi-step `flow.yaml` files with persona-aware transitions and state handling.
* [ ] 📂 **Config layer merger** `[core]` — Implement hierarchical loading and merging of `.lily/project.yaml` across directory levels.
* [ ] 📜 **Flow result logging and backreference system** `[core]` — Store `result.md` in a way that supports search, memory, and reuse.
* [ ] 🧾 **Task lifecycle tracker + state storage** `[core] [tasks] [UX]` — Build a persistent task state tracker that reflects the todo → in progress → done lifecycle across CLI/TUI.
* [x] 🧠 **Skill schema and metadata validator** `[core] [developer] [validation]` — Enforce front matter format for skills and flows (name, tags, kind, persona) for validation and discoverability. ✅ **Completed 2025-07-22**
* [ ] 🔍 **Skill / Flow / Task search index** `[UX] [navigation] [index]` — Create fuzzy-searchable registry of skills, flows, and active task specs.
* [ ] 🧰 **Tool registry schema + resolution system** `[core] [tools]` — Define tool metadata structure and enable tool resolution by skill or flow.

---

## 🧩 MODULE SYSTEM

* [ ] 📦 **Module loader and registry** `[modules]` — Enable Lily to discover and load modules with manifests, skills, and flows.
* [ ] 🪪 **Module manifest validator** `[modules]` — Create schema and validator for `module.yaml` declarations.
* [ ] 🧰 **Chrona module bootstrap** `[chrona]` — Scaffold initial `skills/`, `flows/`, and example `project.yaml` for Chrona use case.
* [ ] 📚 **Research module scaffold** `[research]` — Build out basic summarization and citation-tracking skills for PhD workflows.

---

## 💬 VOICE INTERACTION

* [ ] 🎙️ **WhisperFlow input capture** `[voice]` — Integrate WhisperFlow as a tool + build `lily voice record` CLI command.
* [ ] 🧠 **Voice input → skill mapping** `[voice]` — Use transcribed input to resolve correct skill or flow.
* [ ] 🔊 **TTS reply agent (Coqui/ElevenLabs)** `[voice]` — Create interface for reading `result.md` aloud using persona voice profile.

---

## 🖥️ CLI / TUI / GUI

* [x] 💻 **CLI command router** `[cli]` — Implement `lily run`, `lily run-flow`, `lily skills`, `lily flows`, etc. ✅ **Completed 2025-07-22**
* [ ] 🧮 **Kanban-style TUI MVP** `[tui]` — Initial terminal UI for showing tasks and context panel.
* [ ] 📑 **Context-aware right panel viewer** `[tui]` — Show `initial.md`, `result.md`, flow state, and memory in TUI.

---

## 🧠 PERSONAS & MEMORY

* [ ] 🧬 **Persona switching engine** `[persona]` — Load `PERSONAS.yaml`, support dynamic switching, apply per-skill.
* [ ] 🧠 **Memory profile support** `[memory]` — Build out configurable memory strategies (shortform, longform, citation-linked).

---

## 📚 DOCUMENTATION

* [ ] 🗺 **LILY\_RULES.md** — Define tone, UX guidance, and structural rules for prompt/response behavior.
* [ ] 🧑‍🎤 **PERSONAS.yaml definition** — Structure for declaring roles, tones, tools, and memory profiles per persona.
* [ ] 🧩 **Extension architecture write-up** — Guide for creating modules with skills and flows.

---

## 🚀 FUTURE / NICE-TO-HAVE

* [ ] 🎨 **Drag-and-drop GUI flow builder** `[gui] [future]` — Visual canvas for connecting skills and building flows.
* [ ] 💡 **Flow variable injection + step linkage** `[core] [flows]` — Allow dynamic reference to earlier outputs using `{{ step.result }}` syntax in flows.
* [ ] ♻️ **Rework triggering system** `[core] [UX]` — Enable Lily to mark tasks as needing rework and optionally auto-retry or suggest fixes.
* [ ] ✅ **Output validator layer** `[core] [validation]` — Add markdown/result.md post-process validation via front matter rules or plugins.
* [ ] 🧪 **Skill rework loop + self-validation** `[future] [core]` — Allow Lily to detect invalid output and auto-trigger a rework or debug pattern.
* [ ] 🛡️ **Security / safety guardrails** `[future] [infra]` — Input sanitization, file overwrite checks, and sandbox execution support.
* [ ] 🗃 **Project snapshot + archive tooling** `[future] [UX]` — Export `.lily/` task state and outputs to shareable or long-term storage.
* [ ] 📦 **Project export command** `[UX] [infra]` — CLI tool to package `.lily/` into reusable snapshots or zip archives.

---

Each item will link to a `.md` file in `planning/stories/` once work begins.
