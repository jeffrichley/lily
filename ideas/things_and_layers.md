# Kernel layers and "things" to build

## Layer 0 — Storage and Identity

- [x] Run identity (run_id, timestamps, kernel version) — *Phase A done*
- [x] Artifact store — put_json, put_text, put_file, get, open_path, list; global SQLite index — *Phase B–D + put_text done*
- [x] Provenance metadata (producer, time, inputs) — in ArtifactRef and store
- [x] Minimal CLI — `lily run new` (+ optional `--work-order`); Typer + Rich; creates run dir + manifest, optionally attaches work order as file artifact — *done*

## Layer 1 — Contracts and Validation

- [x] Envelope model (universal typed wrapper)
- [x] ArtifactRef model (stable references + hashes) — *done in Layer 0 Phase B*
- [x] Schema registry (register artifact types)
- [x] Validation engine (Pydantic/JSONSchema hooks)

## Layer 2 — Execution Graph Runtime

- [x] Step model (inputs/outputs/executor/retry/timeout)
- [x] Graph model (nodes/edges)
- [x] Run state persistence (resume/replay)
- [x] Executor interface (local process + LLM later) — *done*

## Layer 3 — Gates

- [x] Gate model (inputs + runner + required/optional)
- [x] Gate runners (local command runner first)
- [x] Gate result model (pass/fail + reasons + logs)
- [x] Gate report persistence (logs capture + artifact refs)

## Layer 4 — Routing and Policies

- [x] Routing rules model (if fail → route) — *Phase 4.6 done*
- [x] Retry policy enforcement (bounded) — *Phase 4.6 done*
- [x] Workspace policies (allowlist/denylist paths) — *Phase 4.5 done*
- [x] Tool allowlist policy (what executors may run) — *Phase 4.4 done*

## Layer 5 — Observability and Reproducibility

- [x] Structured run logs (step timings, stdout/stderr)
- [x] Provenance graph (who produced what from what)
- [x] Replay controls (rerun step N, gates-only)
- [x] Snapshot metadata (env fingerprints, uv lock hash, etc.)
- [x] Artifact replacement (replace ID, record provenance, downstream reset)

## Layer 6 — Extension Points

- Plugin/Pack loader
- Pack contribution: schemas (artifact types)
- Pack contribution: step templates (optional)
- Pack contribution: gate templates (optional)
- Pack contribution: routing policies (optional)

```mermaid
flowchart TD

%% =========================
%% Status legend
%% =========================
subgraph LEGEND["Legend"]
LRED["Not Started"]:::red
LYEL["Started"]:::yellow
LGRN["Completed"]:::green
end

%% =========================
%% Kernel root
%% =========================
KERNEL(["Kernel Runtime - Local-first"]):::red

%% =========================
%% Layer 0
%% =========================
subgraph L0["Layer 0 - Storage and Identity"]
L0A["Run Identity - run_id, timestamps, kernel version"]:::green
L0B["Artifact Store - put_json put_text put_file get open_path list index"]:::green
L0C["Provenance Metadata - producer, time, inputs"]:::green
L0D["CLI - lily run new, optional work_order"]:::green
end

%% =========================
%% Layer 1
%% =========================
subgraph L1["Layer 1 - Contracts and Validation"]
L1A["Envelope Model - universal wrapper"]:::green
L1B["ArtifactRef Model - stable refs and hashes"]:::green
L1C["Schema Registry - register artifact types"]:::green
L1D["Validation Engine - Pydantic JSONSchema hooks"]:::green
end

%% =========================
%% Layer 2
%% =========================
subgraph L2["Layer 2 - Execution Graph Runtime"]
L2A["Step Model - inputs outputs executor retry timeout"]:::green
L2B["Graph Model - nodes and edges"]:::green
L2C["Run State Persistence - resume replay"]:::green
L2D["Executor Interface - local process baseline"]:::green
end

%% =========================
%% Layer 3
%% =========================
subgraph L3["Layer 3 - Gates"]
L3A["Gate Model - inputs, runner, required optional"]:::green
L3B["Gate Runners - local command runner first"]:::green
L3C["GateResult Model - pass fail, reasons, refs"]:::green
L3D["Gate Logs Capture - stdout stderr and files"]:::green
end

%% =========================
%% Layer 4
%% =========================
subgraph L4["Layer 4 - Routing and Policies"]
L4A["Routing Rules Model - outcome to next step"]:::green
L4B["Retry Policy Enforcement - bounded retries"]:::green
L4C["Workspace Policies - allow deny paths"]:::green
L4D["Tool Allowlist Policy - executors tools permitted"]:::green
end

%% =========================
%% Layer 5
%% =========================
subgraph L5["Layer 5 - Observability and Reproducibility"]
L5A["Structured Run Logs - step timing, status"]:::green
L5B["Provenance Graph - artifact lineage"]:::green
L5C["Replay Controls - rerun step N, gates-only"]:::green
L5D["Environment Fingerprints - python, uv lock hash"]:::green
end

%% =========================
%% Layer 6
%% =========================
subgraph L6["Layer 6 - Extension Points"]
L6A["Pack Plugin Loader - discover and load"]:::red
subgraph L6B["Pack Contributions"]
L6B1["Schemas - artifact types"]:::red
L6B2["Step Templates - optional"]:::red
L6B3["Gate Templates - optional"]:::red
L6B4["Routing Policies - optional"]:::red
end
end

%% =========================
%% Connections
%% =========================
KERNEL --> L0
L0 --> L1
L1 --> L2
L2 --> L3
L3 --> L4
L4 --> L5
L5 --> L6
L6 --> L2

%% =========================
%% Styles
%% =========================
classDef red fill:#ffdddd,stroke:#cc0000,stroke-width:2px,color:#330000
classDef yellow fill:#fff2cc,stroke:#cc9900,stroke-width:2px,color:#332200
classDef green fill:#ddffdd,stroke:#009900,stroke-width:2px,color:#003300
```
