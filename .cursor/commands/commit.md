# Intent

Create a single, high-quality, Commitizen-compliant commit representing the work completed so far.

This command is used to finalize a unit of work into a clean, reviewable commit.

## What This Command Does

When `/commit` is invoked, the agent will:

- Inspect the working tree.
- Validate that the changes form a single logical unit.
- Construct a Conventional Commit message.
- Stage only the correct files.
- Create the commit.
- Show a summary of what was committed.

## What This Command Must NOT Do

- Must NOT auto-run after edits.
- Must NOT commit everything blindly.
- Must NOT include unrelated files.
- Must NOT create multiple commits.
- Must NOT guess intent if the change is unclear.

**If uncertainty exists → STOP and ask the user.**

## Step-by-Step Execution

### Pre-Commit Gate (Required)

Before preparing a commit, the agent must ensure the workspace passes all quality and test gates by invoking:

```
/cleanup
```

This step is mandatory and must not be skipped unless the user explicitly overrides it.

#### Behavior

1. Invoke `/cleanup`.
2. Wait for `/cleanup` to complete.
3. If `/cleanup` reports success → continue with the normal commit workflow.
4. If `/cleanup` stops due to a guardrail or unresolved failure → abort the commit and report that the repository is not in a committable state.

#### Failure Message

If `/cleanup` cannot reach green:

- **Commit aborted: quality/test gates are not passing. Resolve reported issues before committing.**
- Do not create a commit in this case.

#### Rationale (for the agent, not the user)

This enforces:

- No red commits.
- No "fix later" debt.
- Every commit is releasable.
- History remains bisectable.
- CI should never fail on main.

### 1. Inspect Changes

Run:

```bash
git status
git diff
```

Understand what changed before acting.

### 2. Validate Commit Scope

Ensure the diff represents ONE of:

- a feature
- a fix
- a refactor
- a documentation change
- a build/config update

If multiple concerns are detected:

➡️ **Ask the user whether to split the commit.**

### 3. Filter Files

Stage intentionally:

```bash
git add <file1> <file2> ...
```

Never:

```bash
git add .
```

Exclude:

- caches
- logs
- generated media
- model artifacts
- temp files

### 4. Generate Commit Message (Commitizen Format)

Use:

```
<type>(<scope>): <summary>
```

Types allowed:

- feat
- fix
- refactor
- perf
- docs
- test
- build
- ci
- chore

Scope = subsystem, not filename.

### 5. Write Message

Rules:

- Imperative voice ("add", not "added").
- ≤ 72 chars summary.
- No fluff words.
- Explain why in body if needed.

Example:

```
feat(engine): add persistent model cache mounting

Mount ~/.chrona/models into containers to avoid repeated downloads.
```

### 6. Validate and Create Commit

- **Validate:** Before committing, ensure the message passes Commitizen:
  `just commit-check` with the message, or `uv run cz check -m "<message>"`.
  If validation fails, fix the message (type, scope, format) and re-check.
- **Create:** Either run `just commit` (interactive Commitizen flow) or, when the message is already decided and validated:
  `git commit -m "<message>"`

### 7. Verify Result

```bash
git log -1 --stat
```

Present summary to the user.

## Safety Checks (Google-Style Guardrails)

Before committing, verify:

- ✔ No secrets
- ✔ No unrelated edits
- ✔ No debug code
- ✔ No generated artifacts
- ✔ Repo still builds/imports
- ✔ Commit is reviewable as a single change

**If any check fails → stop and report.**

## Output to User

After completion, return:

```
✔ Commit created successfully

<commit message>

Files:
- file_a.py
- file_b.py
```

## Failure Behavior

If the commit cannot be cleanly formed, respond with:

```
Commit aborted: changes span multiple concerns.
Recommend splitting into separate commits.
```

Do not attempt to fix automatically.

## Philosophy of This Command

`/commit` is a deliberate act — like pressing "record" on history.

It should feel like telling a disciplined senior engineer:

**"Wrap this up properly."**
