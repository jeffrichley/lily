# Self-Review Checklist (Reusable)

Use this checklist before commit and PR.

## Bugs / Correctness
- Does behavior match plan/spec exactly?
- Any obvious runtime errors, edge-case failures, or invalid assumptions?

## Regressions
- Could this break existing workflows, APIs, CLI contracts, or data contracts?
- Were impacted areas re-tested?

## Tests
- Are new/changed behaviors covered by tests?
- Are missing tests explicitly documented as risk?

## Risks
- Security, data loss, migration, compatibility, performance, operational risk noted?
- Are rollback/remediation paths clear?

## Evidence
- Validation commands and outcomes are captured.
- User-visible outputs are proven with direct verification commands.
