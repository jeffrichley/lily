---
owner: "@jeffrichley"
last_updated: "2026-03-25"
status: "active"
source_of_truth: true
---

# Backlog: Skills distribution and packaging (post-MVP)

This document defines **contracts and surfaces** for portable skill bundles and org-level rollout. It is **backlog / specification** work, not an active implementation plan under `.ai/PLANS/`. Implementation is tracked as roadmap **SI-008** and backlog **BL-007**.

**Traceability**

- Roadmap: **SI-008** (`docs/dev/roadmap.md`)
- Backlog: **BL-007** (`docs/dev/backlog.md`)
- Parent: SI-007 plan `005` Phase 9 closure (`.ai/PLANS/005-skills-system-implementation.md`)
- Sources: `.ai/SPECS/002-skills-system/PRD.md` §13; `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` (distribution bullets in §20)

## Feature description

Operators and orgs need to **move** curated skill packages between machines and **publish** approved versions without copying raw repository trees ad hoc. The contract must be **versioned**, **checksum-backed**, and aligned with the existing on-disk skill package shape (`SKILL.md` + bounded `references/`).

## Problem statement

- Local `skills.roots` discovery is sufficient for dev, but there is no **portable interchange format** with validation and provenance hooks.
- **API-driven** and **org-wide** governance (channels, rollback) require explicit lifecycle semantics before implementation.

## Solution statement

Define a **single archive format** (`.lily-skill`), a **JSON manifest** with schema versioning, a **deterministic error taxonomy**, and **CLI/API sketches** for import/export/verify. Rollout semantics (channels, pinning) are specified so implementation can proceed without redesign.

## Non-goals (this specification)

- Implementing zip I/O, HTTP servers, or storage backends.
- Replacing filesystem discovery for local development.
- Enterprise tenancy / SSO (see PRD §13 “Future”).

---

## 1. Portable bundle archive (`.lily-skill`)

### 1.1 Container

| Property | Value |
|----------|--------|
| File extension | `.lily-skill` |
| Encoding | ZIP (`.zip` container); compression **deflate** recommended; UTF-8 path names only |
| Root layout | Exactly one `manifest.json` at the archive root; skill trees under `skills/` |

### 1.2 Directory layout (inside ZIP)

```text
manifest.json
skills/
  <canonical-key-1>/
    SKILL.md
    references/...
  <canonical-key-2>/
    SKILL.md
```

- Each `<canonical-key-*>` directory name **must** equal the normalized canonical key for that package (same rules as `skill_types.normalize_skill_name` / parser).
- Only files under each skill directory are part of that skill; no symlink targets (rejected at unpack).

### 1.3 `manifest.json` (schema version `1`)

Top-level object:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | `integer` | yes | Manifest schema; start at `1`. |
| `bundle_id` | `string` (UUID) | yes | Unique id for this bundle build. |
| `bundle_version` | `string` (semver) | yes | Semver of the **bundle** artifact (not necessarily each skill’s metadata version). |
| `format_version` | `integer` | yes | Archive format version; start at `1` (must match this spec). |
| `lily_compat` | `object` | yes | See below. |
| `created_at` | `string` (RFC 3339 UTC) | yes | Build timestamp. |
| `author` | `object` | no | `{ "name": "...", "email": "..." }` or org id string for provenance. |
| `skills` | `array` | yes | One entry per skill directory under `skills/`. |
| `signatures` | `object` | no | Reserved for future detached signing; not required in v1. |

**`lily_compat`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `min_lily` | `string` | yes | Minimum Lily app version (semver) that can import this bundle. |
| `max_lily` | `string` | no | Optional upper bound for pre-release breaking changes. |

**`skills[]` items**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `canonical_key` | `string` | yes | Must match subdirectory name under `skills/`. |
| `root_path` | `string` | yes | Relative path, e.g. `skills/my-skill`. |
| `files_sha256` | `object` | yes | Map **relative path from skill root** → lowercase hex SHA-256 (e.g. `SKILL.md`, `references/notes.md`). |
| `skill_version` | `string` | no | Copy of `metadata.version` from `SKILL.md` if present (informational). |

**Integrity**

- Validators **must** verify every file listed in `files_sha256` after extraction.
- Optional future field: `archive_sha256` at manifest top-level for whole-file fingerprinting.

---

## 2. Validation / import error taxonomy

Stable machine-oriented codes (extend with `detail` human string):

| Code | Meaning |
|------|---------|
| `SKILL_BUNDLE_NOT_ZIP` | File is not a readable ZIP. |
| `SKILL_BUNDLE_LAYOUT` | Missing `manifest.json` or `skills/` root. |
| `SKILL_BUNDLE_MANIFEST_SCHEMA` | `manifest.json` fails JSON schema / required fields. |
| `SKILL_BUNDLE_COMPAT` | Lily version outside `lily_compat` range. |
| `SKILL_BUNDLE_CHECKSUM` | Listed file missing or SHA-256 mismatch. |
| `SKILL_BUNDLE_PARSE` | `SKILL.md` in bundle fails existing `skill_catalog` validation. |
| `SKILL_BUNDLE_KEY_MISMATCH` | Directory name vs manifest `canonical_key` mismatch. |
| `SKILL_BUNDLE_POLICY` | Unpack would violate path bounds or symlink policy. |

---

## 3. CLI surfaces (future implementation)

| Command | Purpose |
|---------|---------|
| `lily skills bundle verify <path.lily-skill>` | Validate ZIP + manifest + checksums + parse each `SKILL.md`; no install. |
| `lily skills bundle export --output <path> <skill-root>...` | Build a bundle from existing on-disk skill dirs (dev/share). |
| `lily skills bundle import --into <dir> <path.lily-skill>` | Verify then extract into a target skills root (operator control). |

Rules: default output remains **Rich** tables/panels per `AGENTS.md`; optional `--json` for automation.

---

## 4. API-managed lifecycle (future implementation)

REST-style sketch (paths illustrative):

| Operation | Description |
|-----------|-------------|
| `POST /v1/skill-bundles` | Upload `.lily-skill`; server runs same validation as `bundle verify`. |
| `GET /v1/skill-bundles/{bundle_id}` | Metadata + compatibility; no body leak of skill content without authz. |
| `POST /v1/skill-bundles/{bundle_id}/publish` | Move bundle to a **channel** (e.g. `stable` / `beta`) with semver tag. |
| `DELETE /v1/skill-bundles/{bundle_id}` | Soft-delete or tombstone per org policy. |

**Versioning**

- **Bundle** semver (`bundle_version`) and **per-skill** metadata version are both surfaced; runtime merge rules stay consistent with `skill_registry` (scope precedence unchanged—import target chooses roots).

---

## 5. Organization rollout and governance

| Concept | Definition |
|---------|------------|
| **Channel** | Named stream (`stable`, `beta`, `internal`) mapping to a set of published bundle ids. |
| **Pin** | Config or lockfile holds `bundle_id` + `bundle_version` + optional SHA-256 for reproducibility. |
| **Rollback** | Previous bundle id remains addressable; switching pin reverts without re-upload if retained. |
| **Governance** | Org policy defines who may publish, which channels exist, and audit logging (out of scope for v1 API sketch). |

---

## 6. Implementation phases (when BL-007 is scheduled)

| Phase | Deliverable |
|-------|-------------|
| A | Read-only `bundle verify` + unit tests against golden `.lily-skill` fixtures |
| B | `bundle import` to a staging directory + integration tests |
| C | `bundle export` from discovered skill dirs |
| D | Optional HTTP client for API sketch + auth hooks |

---

## Status record

- **Specification**: captured in this backlog doc (contract-only; no runtime code).
- **Implementation**: not started — **SI-008** / **BL-007**.

---

## References

- `.ai/PLANS/005-skills-system-implementation.md` — SI-007 MVP phases 1–8 (retrieval); Phase 9 closed with this backlog spec.
- `docs/dev/references/skills-si007-mvp.md` — operator verification for retrieval MVP.
- PRD §13 Future considerations; SKILLS_ARCHITECTURE §20 distribution rows.
