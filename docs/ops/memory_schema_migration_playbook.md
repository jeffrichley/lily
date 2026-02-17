# Memory Schema Migration Playbook

Purpose: safe, repeatable process for memory schema/version upgrades.

## Preconditions

- Freeze deploys touching memory/session code.
- Confirm clean quality gates:
  - `just quality test`
  - `just memory-migration-gates`
- Create fresh backup using `docs/ops/memory_backup_restore_runbook.md`.

## Versioning Contract

- Session schema uses `session_schema_version`.
- Memory records include `schema_version`.
- Migration steps must be idempotent and deterministic.

## Migration Flow

1. Define target schema and invariants.
2. Add migration adapter (old -> new) in code with explicit tests.
3. Add compatibility read path for previous schema version.
4. Add write-path update to only emit new schema version.
5. Run dry-run migration on copied backup data.
6. Validate:
   - record counts preserved
   - namespace integrity preserved
   - policy-sensitive fields preserved
7. Run eval/quality gates.
8. Roll forward in controlled environment.

## Validation Checklist

- [ ] No record loss by count.
- [ ] No cross-domain leakage (`persona_core`, `user_profile`, `working_rules`, `task_memory`).
- [ ] `last_verified`, `status`, `conflict_group`, and `expires_at` preserved.
- [ ] Command contracts unchanged (`code` fields stable).
- [ ] Memory migration eval suite green.

## Rollback Strategy

1. Stop Lily.
2. Restore pre-migration backup files.
3. Revert schema-writing code path to previous release.
4. Re-run smoke commands and eval gates.

## Change Record Template

- Date:
- Commit:
- From schema:
- To schema:
- Dry-run results:
- Validation results:
- Rollback tested: yes/no
