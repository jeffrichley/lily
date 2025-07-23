# 📘 Story: Skill Execution

## 🧭 Overview

Enable Lily to run a single skill from CLI, with persona-aware prompt construction, injected input, and structured output logging. This is the foundational unit that all flows and tools build upon.

---

## 🧩 Components to Implement

| Component                    | Description                                                   |
| ---------------------------- | ------------------------------------------------------------- |
| **CLI command** (`lily run`) | Parses args, resolves skill, runs agent                       |
| **Agent or runner**          | Loads front matter, prepares prompt, executes with persona    |
| **Input injector**           | Substitutes `{{ input }}` into skill                          |
| **Output handler**           | Saves to `.lily/threads/<name>/result.md` (if tracked), or returns inline |
| **Persona loader**           | Loads `PERSONAS.yaml`, injects tone, voice, memory            |
| **Skill resolver**           | Searches `.lily/skills/`, module, or global for `<name>.md`   |
| **Error manager**            | Handles missing skill, invalid front matter, failed LLM calls |
| **Tracking manager**         | Determines if task should be tracked based on front matter or CLI flag |

---

## 🛠 Development Checklist

* [x] CLI: `lily run <skill-name> [--input file] [--task name]` ✅ **Completed 2025-07-22**
* [x] Parses and validates arguments ✅ **Completed 2025-07-22**
* [ ] Auto-generates task name if not given (shows placeholder "Auto-generated" but no actual generation logic)
* [x] Skill Resolver: looks in `.lily/skills/`, modules, globals ✅ **Completed 2025-07-22**
* [x] Skill Validator: checks front matter for required fields ✅ **Completed 2025-07-22**
* [ ] Input Substitutor: replaces `{{ input }}` in skill body
* [ ] Persona Loader: loads `PERSONAS.yaml`, applies tone/tools/memory
* [ ] Prompt Constructor: builds prompt from parts
* [ ] LLM Executor: runs prompt and captures output
* [ ] Result Writer: writes `initial.md`, `result.md`, `logs/` (only if tracked)
* [ ] Task Tracker: updates `.lily/FEATURES_LIST.md` or `tasks.db` (only if tracked)
* [ ] Tracking Manager: checks `tracked: true` in front matter or `--tracked` CLI flag
* [ ] Test: validate using the `summarize-text` skill and sample.md

---

## 🧪 Acceptance Criteria

* [ ] Run `lily run summarize-text --input sample.md` (untracked mode by default)
* [ ] Run `lily run summarize-text --input sample.md --tracked` (tracked mode)
* [ ] Untracked mode returns result inline with no file outputs
* [ ] Tracked mode creates `.lily/threads/summarize-text_<timestamp>/result.md`
* [ ] Output contains a `### Summary` header and relevant content
* [ ] Persona tone, tools, and memory are respected (if declared)
* [ ] CLI confirms success with user-friendly message
* [ ] Tracked mode creates: `initial.md`, `result.md`, `logs/`
* [ ] Tracked mode updates FEATURES\_LIST.md or task DB with ✅ task completion

---

## 🧵 Example CLI Flow

```bash
lily run summarize-text --input sample.md
```

```text
# Untracked mode (default)
✨ Running skill: summarize-text
🧠 Persona: life
📥 Input: sample.md (32 lines)
📤 Result returned inline
✅ Task complete

# Tracked mode (--tracked flag)
✨ Running skill: summarize-text
🧠 Persona: life
📥 Input: sample.md (32 lines)
📤 Output written to .lily/threads/summarize-text-2025-07-22T12-00/result.md
✅ Task tracked and complete
```

---

## 🧠 Internal Prompt Rendering Example

**Input Skill Template:**

```markdown
## System Prompt
You are a warm, conversational assistant.

## Instructions
Summarize this clearly:

## Input
{{ input }}
```

**Rendered Prompt:**

```markdown
You are a warm, conversational assistant.

Summarize this clearly:

The industrial revolution marked a major turning point in history. Almost every aspect of daily life was influenced in some way...
```

---

## 🔧 Optional Tools (Future Hooks)

Tools may later be declared in front matter or inferred by persona:

* `tools: [clean_text, summarize]`
* Loaded from `tools/registry.yaml`
* Called before or after LLM execution for advanced chains

---

## 📁 Output Artifacts

**Untracked Mode (Default):**
- No file outputs
- Result returned inline to CLI/TUI

**Tracked Mode (--tracked or tracked: true):**
- `.lily/threads/<task-name>/initial.md`
- `.lily/threads/<task-name>/result.md`
- `.lily/threads/<task-name>/logs/`
- Updates to `.lily/FEATURES_LIST.md` or `tasks.db`
