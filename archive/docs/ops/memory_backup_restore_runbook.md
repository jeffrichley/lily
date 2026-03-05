---
owner: "@team"
last_updated: "2026-02-17"
status: "reference"
source_of_truth: false
---

# Memory Backup and Restore Runbook

Purpose: deterministic operational steps for backup/export/restore of Lily memory state.

## Scope

- Session state: `.lily/session.json`
- Global config: `.lily/config.json`
- Long-term store: `.lily/memory/langgraph_store.sqlite`
- File fallback stores (if used): `.lily/memory/personality_memory.json`, `.lily/memory/task_memory.json`
- Evidence store: `.lily/memory/evidence_memory.json`
- Checkpointer DB: `.lily/checkpoints/checkpointer.sqlite`

## Backup

1. Stop active Lily REPL/processes.
2. Create backup directory:
   - `mkdir -p .lily/backups/$(date +%Y%m%d_%H%M%S)`
3. Copy known state files:
   - `cp -R .lily/session.json .lily/config.json .lily/memory .lily/checkpoints .lily/backups/<timestamp>/ 2>/dev/null || true`
4. Verify backup contents:
   - `ls -la .lily/backups/<timestamp>`

## Export (Portable Bundle)

1. Create export root:
   - `mkdir -p .lily/exports/<name>`
2. Copy same artifacts as backup.
3. Add metadata manifest:
   - include date, Lily commit SHA, schema versions, and environment notes.

## Restore

1. Stop Lily processes.
2. Backup current local state first (same backup steps).
3. Restore files from chosen backup/export into `.lily/`.
4. Start Lily and verify:
   - `uv run lily run "/memory long show --domain user_profile"`
   - `uv run lily run "/memory evidence show"`
5. If restore is invalid, Lily auto-recovers corrupted session file into `session.json.corrupt-*`.

## Rollback

1. Stop Lily.
2. Restore the pre-restore backup directory to `.lily/`.
3. Re-run verification commands.

## Operational Notes

- Do not restore across incompatible schema versions without migration playbook steps.
- Prefer restoring all `.lily` memory/checkpoint artifacts together to avoid split-brain state.
