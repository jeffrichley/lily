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
