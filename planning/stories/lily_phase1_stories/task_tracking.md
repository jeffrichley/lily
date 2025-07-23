# 📘 Story: Task Tracking & Persistence

## 🧭 Overview
Implement dual-mode task execution: untracked (ephemeral) as default, tracked (persistent) as optional. This allows users to run quick queries without file clutter while maintaining full task lifecycle management for important work.

## ✅ Requirements
- [ ] Untracked mode as default (ephemeral execution, inline results)
- [ ] Tracked mode via `tracked: true` front matter or `--tracked` CLI flag
- [ ] Task lifecycle management only for tracked tasks
- [ ] Clear CLI feedback for both modes
- [ ] TUI support for tracked task display

## 🛠 Development Checklist
- [ ] Add `tracked` field to skill/flow front matter schema
- [ ] Implement tracking manager to determine execution mode
- [ ] Update CLI commands to support `--tracked` flag
- [ ] Modify output handler for dual-mode behavior
- [ ] Update task tracker to only manage tracked tasks
- [ ] Add tracking status to CLI feedback messages
- [ ] Update TUI to only show tracked tasks in kanban board
- [ ] Write tests for both tracked and untracked modes
- [ ] Update documentation and examples

## 🧪 Acceptance Criteria
- [ ] `lily run summarize-text` runs in untracked mode by default
- [ ] `lily run summarize-text --tracked` creates task files and updates tracker
- [ ] Skills with `tracked: true` in front matter always create task files
- [ ] Untracked mode returns results inline with no file outputs
- [ ] Tracked mode creates `.lily/threads/<task>/` directory structure
- [ ] TUI kanban board only shows tracked tasks
- [ ] CLI clearly indicates which mode is being used

## 🧵 Example Usage

### Untracked Mode (Default)
```bash
lily run summarize-text --input document.md
```
```text
✨ Running skill: summarize-text (untracked mode)
🧠 Persona: default
📥 Input: document.md
📤 Result returned inline
✅ Task complete
```

### Tracked Mode (CLI Flag)
```bash
lily run summarize-text --input document.md --tracked
```
```text
✨ Running skill: summarize-text (tracked mode)
🧠 Persona: default
📥 Input: document.md
📤 Output written to .lily/threads/summarize-text-2025-01-15T10-30/result.md
✅ Task tracked and complete
```

### Tracked Mode (Front Matter)
```yaml
---
name: summarize-text
description: Summarizes text content
tracked: true
personas: [life, research]
---
```

## 📁 File Structure

**Untracked Mode:**
- No file outputs
- Results returned to CLI/TUI

**Tracked Mode:**
```
.lily/
├── threads/
│   └── summarize-text-2025-01-15T10-30/
│       ├── initial.md
│       ├── result.md
│       └── logs/
└── FEATURES_LIST.md (updated)
```

## 🔧 Implementation Notes

- Tracking decision: `--tracked` flag OR `tracked: true` in front matter
- Task naming: `<skill-name>-<timestamp>` for tracked tasks
- Directory structure: `.lily/threads/`
- TUI integration: Only tracked tasks appear in kanban board
- Memory integration: Only tracked tasks update memory profiles
- Export functionality: Only tracked tasks are included in project exports
