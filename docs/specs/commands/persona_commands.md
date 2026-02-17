---
owner: "@team"
last_updated: "2026-02-17"
status: "reference"
source_of_truth: false
---

# Persona Commands

Phase 6 command surface for persona and memory controls.

## Persona

- `/persona list`
  - List available persona profiles and mark the active one with `*`.
- `/persona use <name>`
  - Switch active persona for the current session.
  - Resets explicit style override so the selected persona default style is used.
- `/persona show`
  - Show active persona summary, default style, effective style, and instructions.
- `/persona export <name> [path]`
  - Export persona profile markdown to disk.
- `/persona import <path>`
  - Import persona profile markdown into the persona catalog.
- `/reload_persona`
  - Reload persona catalog from disk for the current runtime/session.

## Style

- `/style focus|balanced|playful`
  - Set explicit per-session style override.
  - Persists in session state across restart.

## Memory

- `/remember <text>`
  - Save one personality memory fact in the `global` namespace.
- `/memory show [query]`
  - Show matching personality memory records.
  - When query is omitted, shows recent records.
- `/forget <memory_id>`
  - Delete one personality memory record by id.

## Agent Compatibility

- `/agent list`
- `/agent use <name>`
- `/agent show`

Current behavior: persona-backed compatibility surface until full multi-agent orchestration lands.
