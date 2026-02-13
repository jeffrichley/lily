```
docs/specs/agent_mode_v0/skills_loader_contract.md
```

(Aligned with `process.md` and scoped by `needed.md`.)  

---

# Skills Loader Contract (V0)

This document specifies **how Lily discovers, loads, filters, and snapshots skills** in Agent Mode v0.

This is a behavioral contract for the loader.
It is not an implementation guide.

If a loader behavior is not defined here, it does not exist in v0.

---

## 1. Definitions

**Skill**
A skill is a directory containing at minimum `SKILL.md`. (Exact skill format is defined in `SKILL_SPEC_V0.md`.)

**Skill ID / Name**
A skill’s identity is the directory name (e.g., `skills/plan_compiler/`).
Within a given loader run, skill IDs must be unique after precedence resolution.

**Source**
A root directory that may contain multiple skill directories.

**Resolved Skill**
The final selected version of a skill after:

1. discovery, 2) precedence resolution, 3) eligibility filtering.

**Snapshot**
A stable list (index) of resolved skills stored in the session to prevent drift.

---

## 2. Skill Source Roots (V0)

Lily loads skills from a fixed ordered set of source roots.

### 2.1 Required Source Roots

V0 requires the following sources:

1. **Bundled**: `SKILLS_BUNDLED_DIR`
   First-party skills shipped with Lily.

2. **Workspace**: `SKILLS_WORKSPACE_DIR`
   Project-local overrides and project-specific skills.

### 2.2 Optional Source Roots

V0 may support:

3. **User**: `SKILLS_USER_DIR`
   Personal skills available across projects.

If user skills are not implemented in v0, the loader must behave as if this source root is empty.

### 2.3 No Other Sources in V0

V0 explicitly does **not** include:

* plugin-contributed skills
* remote skill registries
* marketplace installs
* network-fetched skills

---

## 3. Discovery Rules

### 3.1 Directory Traversal

For each source root, Lily scans **only immediate child directories** as candidate skills.

A candidate directory is a skill if it contains:

* `SKILL.md` (required)

No recursive nested skill discovery in v0.

### 3.2 Skill Name Extraction

The skill name is:

* the directory name (basename) of the skill folder

Example:

* `/…/skills/plan_compiler/SKILL.md` → skill name `plan_compiler`

### 3.3 Discovery Output

The loader produces a set of discovered candidates:

```
Candidate = (skill_name, source_root, absolute_path)
```

---

## 4. Precedence Resolution

### 4.1 Precedence Order (V0)

When two or more candidates share the same `skill_name`, Lily resolves the winner by precedence:

```
Workspace > User > Bundled
```

Meaning: the *highest-precedence* source provides the resolved skill.

### 4.2 Determinism Requirement

Given the same filesystem state and the same configured source roots:

* the same resolved skill set must be produced
* with identical precedence winners

There must be no nondeterministic ordering (e.g., OS directory listing order must not affect results).

### 4.3 Conflict Visibility

When conflicts exist (same skill name in multiple sources):

* loader must record conflict metadata for debugging (non-user-facing is fine)
* but must still deterministically choose a winner

No interactive prompting in v0.

---

## 5. Eligibility Filtering

Eligibility filtering occurs **after precedence resolution** (winner chosen), not before.

Rationale: precedence is a deterministic contract; eligibility decides whether the resolved winner is usable.

### 5.1 Eligibility Inputs

Eligibility conditions are read from skill metadata (per `SKILL_SPEC_V0.md`) and may include:

* OS constraints (e.g., `darwin`, `linux`, `win32`)
* required environment variables
* required binaries available on PATH
* required config keys (optional in v0; may be deferred)

### 5.2 Eligibility Outcomes

For each resolved skill:

* If eligible → included
* If ineligible → excluded

### 5.3 No Fallback-to-Lower-Precedence in V0

If the highest-precedence resolved skill is ineligible, Lily **must not** automatically fall back to a lower-precedence version.

Reason: silent fallback creates surprising behavior and breaks auditability.

Instead, the skill is excluded and the system must surface an inspectable reason via diagnostics.

(If we ever want fallback behavior, it becomes a vNext feature with explicit rules and strong logging.)

---

## 6. Index Construction (Available Skills)

The loader constructs an **Available Skills Index** from eligible resolved skills.

### 6.1 Required Fields (per entry)

Each entry must include at minimum:

* `skill_name`
* `source` (bundled/user/workspace)
* `path`
* `summary` (if available; otherwise empty)
* `invocation_modes` (if declared; otherwise default)

### 6.2 Stable Sort Order

The index must be ordered deterministically. Recommended order:

1. alphabetical by `skill_name`

No “most relevant” ordering in the loader. Relevance is runtime/LLM territory.

---

## 7. Snapshot Semantics

### 7.1 When a Snapshot Is Created

A skills snapshot is created:

* when a session is created, or
* when `/reload_skills` is executed

### 7.2 Snapshot Contents

The snapshot stores:

* the Available Skills Index
* a `snapshot_version` token (monotonic integer or hash)
* optional diagnostic metadata (conflicts, ineligible reasons)

### 7.3 Snapshot Stability Guarantee

Within a session:

* Lily uses the snapshot for all skill selection and command resolution
* filesystem changes do **not** take effect until explicit reload

This prevents mid-session drift and “it worked 5 minutes ago” failures.

---

## 8. Command-Level Behaviors

### 8.1 `/skills`

* Lists skills from the current snapshot only
* Does not trigger discovery
* Deterministic ordering

### 8.2 `/skill <name>`

Resolution rules:

1. Match `<name>` exactly against snapshot skill names.
2. If not found, fail clearly (no fuzzy match in v0).
3. If found, return the resolved skill entry.

No fallback to other names. No “did you mean” in v0 unless you want it (optional UX sugar).

### 8.3 `/reload_skills`

* Re-runs discovery → precedence → eligibility → index construction
* Creates a new snapshot version
* Replaces the session’s active snapshot

---

## 9. Error Handling Contract

The loader must distinguish:

* **Loader errors** (cannot read directories, invalid permissions, corrupt metadata)
* **Skill errors** (missing `SKILL.md`, invalid frontmatter, etc.)
* **Eligibility failures** (requirements not met)

### 9.1 Loader Errors

If a required source root cannot be read:

* loader fails (hard fail) unless explicitly configured as optional

### 9.2 Skill Errors

If a candidate skill is malformed:

* exclude it
* record diagnostics

No hard fail for a single bad skill.

### 9.3 Eligibility Failures

Exclude the skill and record the reason.

---

## 10. Out of Scope (Explicitly Not Included)

The skills loader v0 does not include:

* file watchers / auto-refresh
* skill installation
* skill signing / provenance verification
* plugin-contributed skill sources
* dependency resolution between skills
* “fallback to lower precedence if winner is ineligible”
* semantic search over skills
* remote loading

---

## 11. Definition of Done (Loader Contract)

This contract is satisfied when:

* skills are discovered deterministically from defined roots
* precedence resolution is stable and matches: `Workspace > User > Bundled`
* eligibility filtering excludes ineligible skills without silent fallback
* available skills index is stable and sorted deterministically
* session snapshot prevents drift until explicit reload
* commands `/skills`, `/skill`, `/reload_skills` operate strictly against the snapshot
