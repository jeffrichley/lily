### Trigger

Run this skill **only when the user issues:**

```
/coverage
```

---

### Intent

Bring the repository to a **green coverage gate** by running:

* `just test-cov`

If the coverage threshold is not met, the agent must **add high-value, Google-quality tests** until the configured threshold passes.

This command is not about “gaming the number.” It is about increasing confidence: tests should meaningfully verify correctness, prevent regressions, and document intended behavior.

**Threshold location:** The coverage fail-under value is in `pyproject.toml` under `[tool.coverage.report]` as `fail_under` (e.g. `fail_under = 80`).

---

### Preconditions

Before starting, the agent must verify:

1. Repo root:

   ```
   git rev-parse --show-toplevel
   ```
2. `just` is available:

   ```
   just --version
   ```
3. Coverage target exists:

   ```
   just --list
   ```

   Must include: `test-cov`

If any precondition fails → stop and report what’s missing.

---

### Core Principle

**Coverage is a signal, not the goal.**
The goal is **robust correctness**.

The agent must prioritize tests that:

* validate core behavior and invariants
* cover edge cases that are likely to regress
* exercise public APIs and contracts
* improve failure localization (clear assertions, meaningful names)

The agent must avoid:

* “empty” tests that only execute lines
* testing private implementation details unless necessary
* brittle mocks that lock in internal structure
* meaningless assertions (`assert True` / “smoke only”)

---

### Loop Contract

The agent will loop until either:

* ✅ `just test-cov` passes (including threshold), or
* a stop condition triggers.

**Max loops:** 8
**Max new/edited test files per loop:** 6
**Max total new tests per loop:** 15 (favor quality over quantity)

---

### Execution Steps

#### 0) Baseline Snapshot

Run:

```
git status
just test-cov
```

Capture:

* overall coverage %
* configured threshold: from `pyproject.toml` → `[tool.coverage.report]` → `fail_under` (e.g. `fail_under = 80`), or from the tool output
* failing message from the coverage gate
* (if shown) per-file coverage table or “missing lines” report

If `just test-cov` already passes → report success and stop.

---

#### 1) Coverage Triage: Biggest Bang for Buck

The agent must identify **where tests will add the most confidence per unit effort**.

Rank candidates using this scoring heuristic:

**Impact Score = (Risk × Importance × Coverage Gap) / Test Cost**

Where:

* **Risk**: likelihood of defects/regressions (complex logic, parsing, state transitions, concurrency, boundary math)
* **Importance**: user-facing or core pipeline modules, “engine contracts,” schema validation, routing/policies
* **Coverage Gap**: low coverage in a meaningful module (ignore “glue” if low risk)
* **Test Cost**: estimated effort to test well (low if pure functions, higher if heavy IO)

**Prefer:**

* pure functions and deterministic logic
* core orchestration and contracts
* validation and error handling paths
* business rules and branching logic

**Defer (unless required):**

* thin wrappers over third-party libraries
* generated code
* obvious boilerplate getters/setters
* heavy integrations that need major harness work

---

#### 2) Choose a Test Strategy (Google-quality)

For each top candidate module, pick the best approach:

1. **Contract tests**
   Validate the public API surface and invariants (inputs → outputs, error conditions).

2. **Behavior tests**
   Verify meaningful behavior (e.g., routing decisions, schema validation, artifact handling).

3. **Edge-case tests**
   Boundaries, empty inputs, invalid inputs, off-by-one cases, uncommon branches.

4. **Property-like tests (when appropriate)**
   Deterministic property checks: idempotency, monotonicity, invariants.

5. **Golden tests (sparingly)**
   Stable snapshot outputs for structured data where exact formatting matters.

**Rule:** If a test doesn’t increase confidence, don’t write it.

---

#### 3) Implement Tests

Requirements for every new/updated test:

* Clear name (behavior-oriented)
* Arrange/Act/Assert structure
* Minimal mocking (prefer real objects, lightweight fakes)
* Assert *meaningful outcomes* (not just “no exception”)
* Include negative tests for expected failures when valuable

If adding fixtures:

* keep them small and local
* avoid huge shared fixtures that become test debt

---

#### 4) Re-run Coverage Gate

After adding tests, run:

```
just test-cov
```

If still failing:

* repeat triage with updated report
* pick next highest-impact targets
* continue loop

---

### Reporting (every loop)

After each loop, the agent must provide:

**Coverage Report (Loop N)**

* Gate: ✅ pass / ❌ fail
* Coverage: `<current %>` (and threshold if known)
* Highest-impact areas targeted:

  * `<module/file>` — why it matters
* Tests added/updated:

  * `<test file>` — short description
* Next move:

  * “Targeting X next because Y”

At completion:

**Coverage Complete**

* `just test-cov`: ✅
* Coverage: `<final %>` (threshold: `<threshold>`)
* Summary of test improvements (what confidence increased)

---

### Stop Conditions (must halt and ask)

Stop and ask the user if:

1. The threshold can’t be met without large integration harness work
2. Coverage gaps are mostly in auto-generated or third-party wrapper code
3. The remaining low-coverage code is clearly dead/unused but needs a decision
4. `just test-cov` output does not include actionable per-file/missing-lines info and the agent cannot locate coverage config (check `pyproject.toml` → `[tool.coverage.report]` → `fail_under`)
5. Fix would require changing production behavior (not just tests)

When stopping, include:

* current coverage vs threshold
* top remaining low-coverage modules
* recommended path (tests vs refactor vs exclude decision)

---

### Explicit Anti-Gaming Policy

The agent must NOT:

* add tests that only execute lines with weak assertions
* mark lines with pragmas to exclude coverage unless explicitly approved
* lower the configured threshold
* skip expensive tests without user authorization

If excluding coverage is truly justified, the agent must propose it as an option and wait for approval.

---

### “Google-Quality” Test Checklist

Every meaningful test should aim to answer:

* What contract is being validated?
* What bug would this have caught?
* What regression does this prevent?
* Is the failure message obvious and actionable?
* Is the test stable (not timing/flaky)?
* Is it too coupled to internals?

---

### Output Format (final)

When done, the agent must output:

* Confirmation that `just test-cov` passes
* List of key behaviors now covered
* Suggested next “quality investments” (optional, small)
