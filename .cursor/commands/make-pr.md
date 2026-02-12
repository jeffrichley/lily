# make-pr

## Trigger

Run this skill **only when the user issues:**

```
/make-pr
```

---

## Intent

Create a high-quality Pull Request that is ready to review and merge, using **Google-grade hygiene**:

- branch is clean and single-purpose
- commits are conventional / Commitizen-compliant
- PR description **honors the PR template verbatim**
- required gates are green
- CI checks are actively monitored until completion (or escalated with evidence)

---

## Preconditions

Before doing anything, the agent must verify:

1. **Repo root:**

   ```bash
   git rev-parse --show-toplevel
   ```

2. **PR template exists** at the gold-standard location:

   ```bash
   test -f .github/pull_request_template.md
   ```

3. **`gh` CLI** is installed and authenticated (preferred):

   ```bash
   gh --version
   gh auth status
   ```

If `gh` is not available, the agent may fall back to GitHub UI instructions **only if explicitly permitted by the user**.

---

## Core Principles (Google-style)

- **Single-purpose PR:** one coherent change. No drive-by refactors.
- **Reviewability > cleverness:** PR should be easy to understand and verify.
- **Every commit is safe:** no red commits; no broken main.
- **Template compliance is mandatory:** structure stays intact; content is filled with real signal.
- **CI is not "fire and forget":** monitor checks; provide evidence when failing.

---

## Workflow

### Phase 0 — Decide PR Shape

1. Inspect current status:

   ```bash
   git status
   git diff
   ```

2. If the working tree contains unrelated changes:

   - STOP and ask the user whether to split, stash, or discard.
   - Do not proceed with a mixed PR.

---

### Phase 1 — Branching (Clean & Traceable)

Create or switch to a branch with a descriptive name.

**Branch naming standard:**

- `feat/<scope>-<slug>`
- `fix/<scope>-<slug>`
- `chore/<scope>-<slug>`
- `refactor/<scope>-<slug>`

Example:

```bash
git checkout -b feat/engine-model-cache
```

Rules:

- If already on a feature branch, keep it.
- Never create PRs directly from `main`.

---

### Phase 2 — Quality Gates Must Be Green

Before making the PR:

1. Run cleanup (self-healing):

   ```
   /cleanup
   ```

2. If coverage is part of your bar (recommended for most PRs):

   ```
   /coverage
   ```

3. If tests were added/changed or the suite is suspicious:

   ```
   /test-quality
   ```

**Hard rule:** If these cannot reach green due to a stop condition, abort PR creation and report why.

---

### Phase 3 — Commit (Conventional / Commitizen)

If there are uncommitted changes, create a proper commit:

```
/commit
```

Rules:

- Exactly one logical unit per commit (unless the user asked for multiple).
- Do not commit generated artifacts, caches, logs, or secrets.
- Commit message must follow:

  ```
  <type>(<scope>): <summary>
  ```

---

### Phase 4 — Prepare PR Body From Template (Mandatory)

The PR body must be derived from:

```
.github/pull_request_template.md
```

**Template rules:**

- Use the template **verbatim** as the base.
- Preserve headings and checklist items.
- Fill each section with concrete details.
- Checkboxes must be meaningfully answered:
  - Risk Level (Low/Medium/High)
  - Perf Impact
  - Breaking Change? (Yes/No)
  - Config/Schema changes (None/Yes)
  - Gate checkboxes (checked when green)

**Implementation approach (recommended):**

- Create a temporary filled PR body file.
- Never hand-write the PR body from scratch.

Example flow:

```bash
cp .github/pull_request_template.md /tmp/pr_body.md
# Edit /tmp/pr_body.md by filling sections (keep structure intact)
```

---

### Phase 5 — Push Branch

1. Ensure remote exists:

   ```bash
   git remote -v
   ```

2. Push branch (set upstream):

   ```bash
   git push -u origin HEAD
   ```

---

### Phase 6 — Open PR (Template-Compliant)

Use `gh pr create` and pass the filled body file:

```bash
gh pr create \
  --title "<conventional title>" \
  --body-file /tmp/pr_body.md \
  --base main
```

**Title rules:**

- Conventional Commit style is strongly preferred:
  - `feat(scope): ...`
  - `fix(scope): ...`

**Draft policy:**

- If work is complete and gates are green: open as ready PR.
- If collaboration is desired before final polish: open as draft **but still keep template structure**.

Optional add-ons (only if repo uses them):

```bash
gh pr edit --add-label "needs-review"
gh pr edit --add-reviewer <team-or-user>
```

---

### Phase 7 — Monitor PR Checks (Non-Negotiable)

After PR creation, the agent must actively monitor Actions/checks.

**Preferred commands:**

1. Show checks summary:

   ```bash
   gh pr checks --watch
   ```

2. If `--watch` isn't available in your version:

   ```bash
   gh pr checks
   gh run list --limit 10
   ```

3. If a run fails, open logs for the failing run:

   ```bash
   gh run view <run-id> --log-failed
   ```

**Failure handling:**

If checks fail, the agent must:

1. Identify the *first failing gate* and its root error.
2. Apply minimal fix(es) (do not "thrash").
3. Re-run local gates as appropriate:
   - `/cleanup` for lint/type/test failures
   - `/coverage` if coverage gate fails
4. Commit with a conventional message.
5. Push, and resume monitoring.

**Do not:**

- disable CI checks
- weaken tests to "get green"
- change configs to silence tools unless explicitly authorized

---

## Output Requirements

When the command completes, the agent must provide:

**Make PR Report**

- PR link (or `gh pr view --web` instruction)
- Title and branch name
- Gate status:
  - cleanup ✅/❌
  - coverage ✅/❌
  - tests ✅/❌
- CI status:
  - all checks ✅ or list failing checks + evidence + fix summary
- Any follow-ups (if appropriate)

---

## Stop Conditions (must ask the user)

Stop and request input if:

- PR is not single-purpose and needs splitting
- fixes require architectural decisions or large refactor
- CI failures are environment/secret/config related
- template compliance is unclear (conflicting headings/templates)
- the repo uses a non-`main` default branch and cannot be inferred safely

---

## Definition of Done

`/make-pr` is complete only when:

- PR exists
- PR body is template-compliant and filled with real signal
- required local gates are green
- CI checks are green **or** failures are reported with evidence and a concrete fix plan
