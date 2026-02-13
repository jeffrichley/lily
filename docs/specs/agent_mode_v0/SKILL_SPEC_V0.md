# Skill Specification (V0)

This document defines the **minimal skill format** required for Lily Agent Mode v0.

**Scope.** This specification exists only to support:

- Loader contract
- Deterministic command dispatch
- Eligibility filtering
- Invocation mode (prompt_rewrite vs tool_dispatch)

If metadata does not influence execution decisions, it does not belong in v0.

---

## 1. Skill Directory Structure

A skill is a directory with the following structure:

```
<skill_name>/
├── SKILL.md          (required)
└── assets/           (optional, ignored by loader)
```

- Only `SKILL.md` is required in v0.
- No code files, Python modules, nested skills, or manifest file.
- The skill directory name defines the `skill_name`.

---

## 2. SKILL.md Structure

`SKILL.md` contains:

1. Optional YAML frontmatter (bounded by `---`)
2. Markdown body (the skill instructions)

Example:

```markdown
---
summary: Short description of what the skill does.
invocation_mode: prompt_rewrite
command: plan
requires_tools:
  - read
  - write
eligibility:
  os: [darwin, linux]
  env: []
  binaries: []
---

# Plan Compiler

When invoked, this skill converts conversation into a structured work plan.
...
```

Frontmatter is optional. If absent, defaults apply.

---

## 3. Minimal Frontmatter Keys (V0)

Only the following keys are recognized in v0. Anything else must be ignored.

### 3.1 `summary` (optional)

| Property | Value |
|----------|--------|
| Type | string |
| Purpose | Short human-readable description used in `/skills` output. |
| If missing | Defaults to empty string. |

### 3.2 `invocation_mode` (optional)

| Property | Value |
|----------|--------|
| Type | string |
| Allowed values | `prompt_rewrite` (default), `tool_dispatch` |

**`prompt_rewrite`** (default):

- Lily selects skill, reads `SKILL.md`, injects skill instructions into model context.
- Model executes via reasoning + tool calls.

**`tool_dispatch`**:

- Deterministic mode. Requires `command_tool` (see below).
- Lily bypasses skill instruction rewrite and directly invokes the specified tool.
- LLM does not reinterpret the skill.

If `tool_dispatch` is declared but `command_tool` is missing, the loader must treat the skill as malformed and exclude it.

### 3.3 `command` (optional)

| Property | Value |
|----------|--------|
| Type | string |
| Purpose | Enables `/skill` shorthand invocation. |

If present, `/skill <skill_name>` may also be invoked as `/<command>`.

Example: `command: plan` allows `/plan`.

- Command names must match `^[a-z0-9_-]+$` and must not collide with built-in commands.
- Built-in commands win; skill is excluded if collision occurs.

### 3.4 `command_tool` (required if `invocation_mode: tool_dispatch`)

| Property | Value |
|----------|--------|
| Type | string |
| Purpose | Tool name to invoke deterministically. |

Example:

```yaml
invocation_mode: tool_dispatch
command_tool: compile_plan
```

- Must match an existing registered tool.
- If tool does not exist, skill is excluded at load time. No runtime fallback.

### 3.5 `requires_tools` (optional)

| Property | Value |
|----------|--------|
| Type | list of strings |
| Purpose | Hint for tool policy gating. |

Example:

```yaml
requires_tools:
  - read
  - write
  - shell
```

- If required tools are unavailable in current tool policy, skill is excluded from Available Skills Index.
- No partial capability.

### 3.6 `eligibility` (optional)

| Property | Value |
|----------|--------|
| Type | object |

Supported keys:

```yaml
eligibility:
  os: [darwin, linux]
  env: [OPENAI_API_KEY]
  binaries: [git]
```

| Key | Meaning | Behavior if condition fails |
|-----|---------|------------------------------|
| `os` | Allowed operating systems | Skill excluded. |
| `env` | Required environment variables | Skill excluded if any missing. |
| `binaries` | Required binaries on PATH | Skill excluded if any missing. |

No fallback to lower-precedence skill (per loader contract).

---

## 4. Skill Body Semantics

The Markdown body of `SKILL.md`:

- Is treated as instructional content.
- Is injected into context when skill is selected (prompt_rewrite mode).
- Must not contain executable code or reference hidden runtime APIs.

In v0 the body is trusted content; there is no security scanning or sandbox isolation layer.

---

## 5. Skill Execution Rules

### 5.1 Single-Skill Rule (V0)

Lily may select at most one skill per request. Skill chaining is not supported in v0.

### 5.2 Deterministic Override

If the user invokes `/skill <name>` or a `/command` alias:

- Lily must use that skill.
- Must not fall back to another skill.
- Must fail clearly if the skill is not available.

### 5.3 No Fuzzy Matching (V0)

- Skill names must match exactly.
- No semantic similarity search, no "did you mean", no alias expansion beyond explicit `command`.

---

## 6. Malformed Skill Handling

A skill must be excluded if:

- `SKILL.md` is missing
- Invalid YAML frontmatter
- `tool_dispatch` declared without `command_tool`
- `command_tool` references nonexistent tool
- `command` collides with built-in command
- Eligibility conditions fail

Malformed skills must not crash the loader. Diagnostics must record the reason.

---

## 7. Canonical Example Skill

**Folder structure:**

```
skills/
└── plan_compiler/
    └── SKILL.md
```

**`skills/plan_compiler/SKILL.md`:**

```markdown
---
summary: Convert conversation into a structured implementation plan.
invocation_mode: prompt_rewrite
command: plan
requires_tools:
  - read
  - write
eligibility:
  os: [darwin, linux, win32]
  env: []
  binaries: []
---

# Plan Compiler

You are the Plan Compiler skill.

## Purpose

Transform the current conversation into a structured, actionable plan.

## Rules

1. Extract goals from the conversation.
2. Identify constraints.
3. Break work into ordered steps.
4. Output structured markdown with:
   - Objective
   - Constraints
   - Phases
   - Step list
5. Do not execute filesystem changes unless explicitly requested.

## Output Format

```markdown
# Plan

## Objective
...

## Constraints
...

## Phases
1. ...
2. ...

## Steps
- [ ] Step 1
- [ ] Step 2
```
```

---

## 8. Definition of Done (Skill Spec V0)

This spec is satisfied when:

- Loader can parse frontmatter deterministically
- Eligibility filtering works
- Command dispatch works deterministically
- Malformed skills are excluded safely
- A canonical example skill loads and executes
- `/skills`, `/skill`, `/plan` behave as defined
