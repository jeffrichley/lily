# Kernel layers and "things" to build

## Layer 0 — Storage and Identity

- [x] Run identity (run_id, timestamps, kernel version) — *Phase A done*
- [x] Artifact store — put_json, put_text, put_file, get, open_path, list; global SQLite index — *Phase B–D + put_text done*
- [x] Provenance metadata (producer, time, inputs) — in ArtifactRef and store
- [x] Minimal CLI — `lily run new` (+ optional `--work-order`); Typer + Rich; creates run dir + manifest, optionally attaches work order as file artifact — *done*

## Layer 1 — Contracts and Validation

- Envelope model (universal typed wrapper)
- [x] ArtifactRef model (stable references + hashes) — *done in Layer 0 Phase B*
- Schema registry (register artifact types)
- Validation engine (Pydantic/JSONSchema hooks)

## Layer 2 — Execution Graph Runtime

- Step model (inputs/outputs/executor/retry/timeout)
- Graph model (nodes/edges)
- Run state persistence (resume/replay)
- Executor interface (local process + LLM later)

## Layer 3 — Gates

- Gate model (inputs + runner + required/optional)
- Gate runners (local command runner first)
- Gate result model (pass/fail + reasons + logs)
- Gate report persistence (logs capture + artifact refs)

## Layer 4 — Routing and Policies

- Routing rules model (if fail → route)
- Retry policy enforcement (bounded)
- Workspace policies (allowlist/denylist paths)
- Tool allowlist policy (what executors may run)

## Layer 5 — Observability and Reproducibility

- Structured run logs (step timings, stdout/stderr)
- Provenance graph (who produced what from what)
- Replay controls (rerun step N, gates-only)
- Snapshot metadata (env fingerprints, uv lock hash, etc.)

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
L1A["Envelope Model - universal wrapper"]:::red
L1B["ArtifactRef Model - stable refs and hashes"]:::green
L1C["Schema Registry - register artifact types"]:::red
L1D["Validation Engine - Pydantic JSONSchema hooks"]:::red
end

%% =========================
%% Layer 2
%% =========================
subgraph L2["Layer 2 - Execution Graph Runtime"]
L2A["Step Model - inputs outputs executor retry timeout"]:::red
L2B["Graph Model - nodes and edges"]:::red
L2C["Run State Persistence - resume replay"]:::red
L2D["Executor Interface - local process baseline"]:::red
end

%% =========================
%% Layer 3
%% =========================
subgraph L3["Layer 3 - Gates"]
L3A["Gate Model - inputs, runner, required optional"]:::red
L3B["Gate Runners - local command runner first"]:::red
L3C["GateResult Model - pass fail, reasons, refs"]:::red
L3D["Gate Logs Capture - stdout stderr and files"]:::red
end

%% =========================
%% Layer 4
%% =========================
subgraph L4["Layer 4 - Routing and Policies"]
L4A["Routing Rules Model - outcome to next step"]:::red
L4B["Retry Policy Enforcement - bounded retries"]:::red
L4C["Workspace Policies - allow deny paths"]:::red
L4D["Tool Allowlist Policy - executors tools permitted"]:::red
end

%% =========================
%% Layer 5
%% =========================
subgraph L5["Layer 5 - Observability and Reproducibility"]
L5A["Structured Run Logs - step timing, status"]:::red
L5B["Provenance Graph - artifact lineage"]:::red
L5C["Replay Controls - rerun step N, gates-only"]:::red
L5D["Environment Fingerprints - python, uv lock hash"]:::red
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
