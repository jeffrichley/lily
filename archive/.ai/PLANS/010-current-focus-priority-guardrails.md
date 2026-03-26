# Feature: current-focus-priority-guardrails

Define explicit priority guardrails for how agents update `docs/dev/status.md` current focus.

## Branch Setup

```bash
git switch main
```

## Intent Lock

**Must**:
- require inclusion of open P1 debt in `Current Focus`
- prohibit AI agents from adding P2+ debt items unless explicitly prioritized by a human
- keep guidance aligned across command/reference/status-doc rule sections

**Must Not**:
- change debt item priorities
- alter debt tracker ownership/targets

**Acceptance Criteria**:
- policy language exists in all current-focus instruction surfaces
- rules are unambiguous for AI-vs-human prioritization authority
- docs checks pass

**Required Tests/Gates**:
- `just docs-check`
- `just status`
