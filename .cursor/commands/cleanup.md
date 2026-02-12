# Intent

Bring the repo to a **green state** by running `just quality` and `just test`. If either fails, the agent must fix the problems, then re-run gates until ✅ quality passes and ✅ tests pass — or until a stop condition is reached.

This command is a **self-healing gate**: run `just quality` + `just test`, fix failures, and loop until green (with strict limits + safety rails).

---

## Trigger

Run this command **only when the user issues:**

```
/cleanup
```

---

## Guardrails (Google-level)

The agent must:

- Prefer the **smallest possible fix** that makes gates pass.
- Keep fixes **local and scoped** to failures.
- Never change behavior unless tests/requirements demand it.
- Never "paper over" failures (e.g., disabling a lint rule, skipping tests) unless the user explicitly authorizes it.
- Never rewrite large chunks to "make it work."

---

## Preconditions

Before starting, verify:

1. **Repo root:**

   ```bash
   git rev-parse --show-toplevel
   ```

2. **`just` exists:**

   ```bash
   just --version
   ```

3. **Targets exist:**

   ```bash
   just --list
   ```

   Must include: `quality`, `test`

If any fail → stop and report what's missing.

---

## Loop Contract

The agent will run a loop of:

1. **Run gate**
2. **Parse failures**
3. **Apply minimal fix**
4. **Re-run relevant gate**
5. Repeat until green or stop condition

- **Max iterations:** 6 loops
- **Max changed files per loop:** 10

If exceeded → stop and ask for guidance with a concrete report.

---

## Execution Steps

### 0) Snapshot state (traceability)

```bash
git status
git diff
```

If the working tree is dirty from earlier work, proceed normally (do not stash).

---

### 1) Quality Gate (first)

Run:

```bash
just quality
```

If it fails:

- Identify the **first actionable** error category (lint / format / type / import / style).
- Apply the **minimal** fix.
- Re-run `just quality`.
- Repeat until `just quality` passes or stop condition triggers.

**Fix policy for common quality failures**

- **Formatting / lint:** apply mechanical corrections (remove unused imports, fix line length, reorder imports, etc.).
- **Type errors:** prefer correcting types properly (signatures, return types, narrowing) over `Any` or broad ignores.
- **Static analysis:** fix root cause; don't suppress warnings by default.

**Forbidden without explicit user approval**

- Adding blanket ignores (`# noqa`, `type: ignore`) unless tightly scoped to a single line and justified.
- Disabling rules in config.
- Marking checks as "excluded" to avoid work.

---

### 2) Test Gate (second)

Once quality is green, run:

```bash
just test
```

If it fails:

- Capture failing test names and the first failure reason.
- Fix the **smallest** issue that causes the failure.
- Re-run `just test`.
- If failures persist, keep iterating within loop limits.

**Test fix policy**

- Prefer fixing production code over weakening tests.
- Only modify tests if the failure indicates the test is incorrect/outdated.
- Do not delete tests to "make green."

---

## Reporting (every loop)

After each loop, the agent must output:

**Cleanup Report (Loop N)**

- Quality: ✅ pass / ❌ fail
- Tests: ✅ pass / ❌ fail / ⏭ skipped
- Changes made: file list + 1-line description per file
- Next action: "Re-running just quality" or "Re-running just test"

At the end (green):

**Cleanup Complete**

- Quality: ✅
- Tests: ✅
- Summary of changes (short)

---

## Stop Conditions (must halt and ask)

The agent must stop and ask the user if any occur:

1. **6 loops reached** and not green
2. Failures suggest **missing dependency / environment issue** (e.g., cannot import package, tool missing)
3. Fix would require **large refactor** or uncertain behavior change
4. The agent cannot reproduce the failure deterministically
5. The best path requires suppressing rules or skipping tests

When stopping, include:

- failing output summary
- hypothesis
- two concrete options

---

## Hard Rules (never do)

- Never run `git clean -fd` or delete files.
- Never modify CI configs to bypass.
- Never "fix" by disabling the gate target.
- Never claim success unless both targets pass.

---

## Example End State

**Cleanup Complete**

- Quality: ✅
- Tests: ✅

Changes:

- `src/foo.py`: removed unused import causing ruff failure
- `src/bar.py`: corrected return type annotation for mypy
- `tests/test_baz.py`: updated fixture to match new API shape (test was stale)
