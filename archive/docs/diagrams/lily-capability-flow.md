---
owner: "@jeffrichley"
last_updated: "2026-03-04"
status: "active"
source_of_truth: false
---

# Lily Capability Flow (Current + Target)

```mermaid
flowchart TD
    U[User Input: lily run / lily repl]

    C001[CAP-001: Command routing slash vs conversation]

    C006[CAP-006: Agent identity context]
    C007[CAP-007: Agent catalog loading]

    C002[CAP-002: Skills snapshot load + reload]
    C003[CAP-003: Skill invocation modes]
    C004[CAP-004: Tool provider dispatch registry]
    B4[Builtin provider]
    P4[Plugin provider]
    M4[MCP provider]
    C005[CAP-005: Plugin security gate + approvals + policy]

    C008[CAP-008: Jobs manual execution + artifacts/history/tail]
    C009[CAP-009: Jobs scheduler lifecycle controls]
    C010[CAP-010: Blueprint workflow runtime target]

    C011[CAP-011: Supervisor runtime]
    C012[CAP-012: Subagent typed handoffs]
    C013[CAP-013: Delegation gate/routing outcomes]
    C014[CAP-014: Jobs-to-supervisor bridge]
    C015[CAP-015: Unified orchestration observability + replay]

    U --> C001
    C001 --> C006
    C001 --> C002
    C006 --> C007

    C002 --> C003
    C003 --> C004
    C004 --> B4
    C004 --> P4
    C004 --> M4
    P4 --> C005

    C001 --> C008
    C001 --> C009
    C008 --> C010
    C008 --> C015
    C009 --> C015

    C006 --> C011
    C011 --> C012
    C012 --> C013
    C013 --> C004
    C013 --> C015

    C008 --> C014
    C014 --> C011

    classDef ok fill:#d9f7e8,stroke:#2b8a3e,stroke-width:1px,color:#111;
    classDef partial fill:#fff4d6,stroke:#e67700,stroke-width:1px,color:#111;
    classDef missing fill:#ffe3e3,stroke:#c92a2a,stroke-width:1px,color:#111;

    class C001,C002,C003,C005,C006,C007,C008,C009,C010 ok;
    class C004,C015 partial;
    class C011,C012,C013,C014 missing;
    class M4 partial;
    class B4,P4 ok;

    click C001 href "../dev/references/capability-ledger.md#cap-001" "Open CAP-001 in capability ledger"
    click C002 href "../dev/references/capability-ledger.md#cap-002" "Open CAP-002 in capability ledger"
    click C003 href "../dev/references/capability-ledger.md#cap-003" "Open CAP-003 in capability ledger"
    click C004 href "../dev/references/capability-ledger.md#cap-004" "Open CAP-004 in capability ledger"
    click C005 href "../dev/references/capability-ledger.md#cap-005" "Open CAP-005 in capability ledger"
    click C006 href "../dev/references/capability-ledger.md#cap-006" "Open CAP-006 in capability ledger"
    click C007 href "../dev/references/capability-ledger.md#cap-007" "Open CAP-007 in capability ledger"
    click C008 href "../dev/references/capability-ledger.md#cap-008" "Open CAP-008 in capability ledger"
    click C009 href "../dev/references/capability-ledger.md#cap-009" "Open CAP-009 in capability ledger"
    click C010 href "../dev/references/capability-ledger.md#cap-010" "Open CAP-010 in capability ledger"
    click C011 href "../dev/references/capability-ledger.md#cap-011" "Open CAP-011 in capability ledger"
    click C012 href "../dev/references/capability-ledger.md#cap-012" "Open CAP-012 in capability ledger"
    click C013 href "../dev/references/capability-ledger.md#cap-013" "Open CAP-013 in capability ledger"
    click C014 href "../dev/references/capability-ledger.md#cap-014" "Open CAP-014 in capability ledger"
    click C015 href "../dev/references/capability-ledger.md#cap-015" "Open CAP-015 in capability ledger"
```

## Read This Diagram

- Green nodes: implemented runtime capability.
- Amber nodes: partially implemented runtime capability.
- Red nodes: missing runtime capability needed for full multi-agent orchestration.

For canonical status and exit criteria, see:
- `docs/dev/references/capability-ledger.md`

## Capability Jump Links

- [CAP-001](../dev/references/capability-ledger.md#cap-001)
- [CAP-002](../dev/references/capability-ledger.md#cap-002)
- [CAP-003](../dev/references/capability-ledger.md#cap-003)
- [CAP-004](../dev/references/capability-ledger.md#cap-004)
- [CAP-005](../dev/references/capability-ledger.md#cap-005)
- [CAP-006](../dev/references/capability-ledger.md#cap-006)
- [CAP-007](../dev/references/capability-ledger.md#cap-007)
- [CAP-008](../dev/references/capability-ledger.md#cap-008)
- [CAP-009](../dev/references/capability-ledger.md#cap-009)
- [CAP-010](../dev/references/capability-ledger.md#cap-010)
- [CAP-011](../dev/references/capability-ledger.md#cap-011)
- [CAP-012](../dev/references/capability-ledger.md#cap-012)
- [CAP-013](../dev/references/capability-ledger.md#cap-013)
- [CAP-014](../dev/references/capability-ledger.md#cap-014)
- [CAP-015](../dev/references/capability-ledger.md#cap-015)
