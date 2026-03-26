# Feature: debt-tracker-readability-cleanup

Improve debt tracker readability by ensuring completed debt is not listed under Active Debt.

## Branch Setup

```bash
git switch main
```

## Intent Lock

**Must**:
- move all completed (`[x]`) debt items out of `## Active Debt`
- keep all closure evidence/details intact
- preserve open debt items in place

**Must Not**:
- change debt priority semantics
- modify open debt targets/owners

**Acceptance Criteria**:
- `## Active Debt` contains only open (`[ ]`) items
- completed items are listed under `## Recently Closed Debt`
- docs validation passes

**Required Tests/Gates**:
- `just docs-check`
- `just status`
