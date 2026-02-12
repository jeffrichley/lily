### Trigger

Run this skill **only when the user issues:**

```
/test-quality
```

---

### Intent

Audit **every test file** in the repository and ruthlessly upgrade the suite to **Google-quality**. The audit is **file-by-file**: you must read and score every test file (no sampling or pattern-only review); refactoring is driven by the resulting prioritized list.

* remove brittleness
* fix incorrect mocking
* eliminate “testing internals”
* strengthen assertions
* improve readability and diagnostics
* reduce flakiness
* enforce a consistent style that makes failures obvious and actionable

This command is a **test suite refactor + hardening pass**. It should measurably increase confidence, not just “make tests pass.”

---

### Preconditions

1. Confirm repo root:

   ```
   git rev-parse --show-toplevel
   ```
2. Identify test runner / framework via `just` targets:

   ```
   just --list
   ```
3. Run baseline tests (and do not start changing anything until you see current state):

   ```
   just test
   ```

If baseline tests are failing, the agent must:

* report failures
* fix those first (minimal changes)
* re-run `just test` until green
  Then begin the quality audit.

---

## Audit artifact (mandatory)

**You must create and maintain a single Markdown file** that records progress at each step. The user can open this file at any time to verify that the workflow is being followed. Suggested path: `test_quality_audit.md` in the repo root (or in `ideas/` / `docs/` if the project keeps such artifacts there). If the user specifies a path, use that instead.

**The audit file is started by running the project’s audit generator script (Step 0).** The script writes the full skeleton: inventory, per-file tables of test methods (for ranking), and empty placeholder sections. The rest of the workflow is **filling in those sections**—no step should be skipped.

**Update the file at each of the following points** (do not wait until the end):

0. **Step 0 (Initialize):** Run the script to generate the base audit file (inventory + method tables + placeholders).
1. **After Step 1 (Inventory):** The inventory is already in the file from Step 0; confirm it matches the discovered list and fix if the script missed anything.
2. **After Step 2 (Scoring):** Fill in the file-level scores table and, in each per-file section, the method Score/Notes columns as needed. Add the prioritized refactor list to its section.
3. **After Phase A (prioritized list):** Ensure the prioritized refactor list section is filled.
4. **During Phase B:** After refactoring each target file, append a line in the "Phase B progress" section (e.g. “Refactored: `path`”) so progress is visible.
5. **After Phase C:** Fill in the final summary section. The audit file then serves as the full audit trail.

If a step is skipped, the file will visibly lack that section; the user can confirm the workflow was followed by checking the file.

---

## The Audit Workflow

### Step 0 — Initialize audit file (mandatory, run first)

**Run the project’s audit generator script** so the base Markdown file exists with the correct structure. The script:

* Discovers all test files (e.g. `tests/**/test_*.py`, `*_test.py`), excluding fixtures, `conftest.py`, and `__init__.py`.
* For each test file, parses it and lists every test method (e.g. `test_*` functions).
* Writes the audit file with: (1) inventory of test file paths, (2) per-file sections each containing a **table of test methods** with columns e.g. Method | Score (0–3) | Notes (so methods can be ranked), (3) placeholder sections for file-level scores, prioritized refactor list, Phase B progress, and final summary.

**How to run:** From the repo root:

```bash
uv run python scripts/generate_test_quality_audit.py -o test_quality_audit.md
```

Or use the just recipe if one exists (e.g. `just test-quality-audit-init`). If the project has no script yet, the agent must create it (e.g. `scripts/generate_test_quality_audit.py`) so that the audit file can be started correctly and the workflow is “fill in the empty sections.”

**Do not proceed to Step 1 until the audit file exists and contains the inventory and per-file method tables.**

---

### Step 1 — Inventory All Tests (mandatory, no shortcuts)

Find **every** test file. Search:

* `tests/**`
* `src/**/tests/**`
* `**/test_*.py`, `*_test.py`

**You must produce a single inventory that lists every test file by path** (e.g. numbered or grouped by module). Do not proceed until you have a complete list. No sampling: every file that runs as part of the test suite must appear in the inventory.

**Confirm the inventory in the audit file** (from Step 0) matches this list; if the script missed any path or included a non-test file, fix the audit file. Then proceed to Step 2.

---

### Step 2 — Score Every Test File (mandatory, file-by-file)

**You must open and read every file in the inventory.** For **each** of those files, assign a score 0–3 on each dimension below. Do not score from grep or pattern search alone; you must read the file to score it.

Dimensions:

1. **Contract Focus**: tests *what* not *how*
2. **Assertion Strength**: asserts behavior/invariants, not incidental values
3. **Stability**: deterministic; no time/order/flaky dependencies
4. **Isolation**: correct boundaries; minimal mocking; no global state bleed
5. **Readability**: obvious intent; AAA structure; good naming
6. **Diagnostics**: failures point to root cause; helpful assertion messages
7. **Maintainability**: avoids brittle snapshots, magic strings, internal hooks

**Output requirement:** Before any refactoring, you must produce a scores table (or per-file list) showing each file’s path and its seven scores + average. Any file with average <2.0 is a refactor target. Optionally include files with average ≥2.0 that still have clear, fixable issues.

**Add the scores table to the audit file.** Then produce the prioritized refactor list and add it to the audit file. Do not proceed to Phase B until the audit file contains both the scores and the prioritized list.

---

### Step 3 — Apply the Google-Quality Rules

These are **mandatory** unless explicitly overridden by the user.

---

## Non-Negotiable Rules

### 1) Test Public Contracts, Not Internals

✅ Prefer:

* public functions/classes
* stable interfaces
* documented behavior
* observable outputs and side effects

❌ Avoid:

* private methods (`_foo`)
* patching internal helper calls unless boundary is the purpose
* asserting implementation order or call counts except when contractually required

If internal testing is unavoidable, refactor production code to expose a stable seam (small adapter/interface) rather than coupling tests to internals.

---

### 2) Assert Behavior, Not Incidental Details

✅ Assert:

* returned values meaningfully
* state transitions and invariants
* emitted events / artifacts
* error types and relevant fields
* interactions at system boundaries (file written, tool invoked) **via stable seams**

❌ Avoid:

* exact formatting unless formatting is the product
* internal object identity
* “magic string equality” for errors
* asserting all kwargs to a third-party call unless your contract depends on them

---

### 3) Exception Testing Must Be Robust

✅ Prefer:

* assert the exception **type**
* assert **key substrings** or structured fields (error code, enum, attribute)
* assert error cause chains if meaningful

❌ Do not:

* assert exact full exception messages
* match entire tracebacks
* rely on punctuation/spacing

---

### 4) Mock Only at Boundaries (and Mock Correctly)

✅ Mock boundaries:

* network calls
* filesystem IO (when expensive)
* subprocess/tool invocations
* time/randomness (inject clock / seed)
* external services

❌ Do not mock:

* pure functions
* domain logic
* classes you own unless creating a seam
* “mock because it’s hard”

**Correct mocking rules:**

* patch **where it is looked up**, not where it is defined
* prefer `monkeypatch` / dependency injection
* avoid deep mock chains (`a().b().c()`), build small fakes instead

---

### 5) Eliminate Brittle Tests

Brittleness indicators (must fix):

* depends on test execution order
* depends on wall-clock time
* sleeps / retries without a deterministic clock
* depends on environment variables without explicit setting
* depends on local machine paths
* depends on randomness without seeding
* depends on external services

Fix strategies:

* inject deterministic clock
* seed randomness
* use tmp paths/fixtures
* use fake implementations over mocks
* isolate state, reset globals

---

### 6) Ban Weak Tests

Remove or rewrite tests that:

* only check “does not crash”
* assert `True`
* assert “something exists” without meaning
* execute lines for coverage

Every test must answer:

* “What contract is this protecting?”
* “What bug would this catch?”

---

## Best Practices to Enforce (Creative + Ruthless)

### Test Design

* **AAA Structure**: Arrange / Act / Assert (blank lines between).
* **One reason to fail** per test (avoid kitchen-sink tests).
* Prefer **parameterized tests** for edge cases instead of copy/paste.
* Use **data builders** (small helper factories) rather than giant fixtures.
* Use **table-driven tests** for validation logic.
* Prefer **fakes** over mocks for complex collaborators.

### Naming Standards

* Test names must encode behavior:

  * `test_<function>__when_<condition>__then_<expected>()`
  * or descriptive plain-English pytest style.

### Assertions

* Assert **invariants**, not just outputs:

  * idempotency
  * monotonic behavior
  * ordering guarantees (only if contractual)
  * schema validation and error paths

* Prefer richer assertions:

  * assert subsets, not entire dicts (unless contract is exact structure)
  * assert types and critical keys
  * validate boundaries

### Diagnostics

* Ensure failures are self-explanatory:

  * use `pytest` assertions that show diffs
  * add assertion messages when necessary
  * avoid opaque asserts like `assert x`

### Fixtures & State

* No shared mutable global fixtures.
* Avoid heavy module-scoped fixtures unless performance demands it.
* Use `tmp_path` for filesystem.
* Never write outside temp dirs.
* Make tests hermetic.

### “Golden” Outputs

* Only use snapshots when:

  * output format is the product
  * snapshot is stable
  * you have a review process for snapshot diffs

Otherwise, assert structured properties.

### Property / Fuzz Tests (Selective)

Add lightweight property tests where huge leverage exists:

* parsing/serialization round-trips
* invariants under random valid inputs
* boundary behaviors

Keep them deterministic and fast.

### Speed & Layering

* Keep unit tests fast (<100ms each ideally).
* Integration tests should be clearly labeled/marked.
* Don’t accidentally turn unit tests into integration tests.

---

## Execution Plan

### Phase A — Baseline & Map

1. `just test` (must be green)
2. **Inventory:** List every test file (see Step 1; no sampling).
3. **Score:** Read and score every file in the inventory (see Step 2). Produce the scores table/list.
4. **Prioritized list:** From the scores, produce the refactor list (all files with average <2.0, plus any others you flag). Order by highest risk / lowest quality first. Ensure the audit file contains this list. Do not start Phase B until the list is in the audit file.

### Phase B — Refactor Loop

**Target set:** The prioritized refactor list from Phase A (as recorded in the audit file). Work through **each** file on that list in order; do not skip files or substitute a different set based on pattern search. **After refactoring each file, append a line to the audit file** (e.g. “Refactored: `tests/unit/test_foo.py`”) so the user can see progress.

For each target file:

1. Improve test structure and naming
2. Replace brittle mocks with seams/fakes
3. Strengthen assertions (behavior/invariants)
4. Fix exception tests to be robust
5. Remove or rewrite weak tests
6. Ensure hermeticity (tmp_path, seeded randomness, deterministic time)

After each file:

* run `just test`
* stop immediately if anything breaks, fix before moving on

### Phase C — Final Verification

1. `just test`
2. (optional if available) `just test-cov`
3. Summarize improvements and remaining risks

---

## Output Requirements

When `/test-quality` completes, the agent must provide:

**Test Quality Report**

* **Audit file:** Path to the audit Markdown file (e.g. `test_quality_audit.md`) that was created/updated at each step. The user can open it to verify the workflow.
* **Files audited:** N (must equal the number of files in the inventory; report “audited N” only if you read and scored every one).
* **Scores:** Per-file scores table or summary (or explicit statement that every file was scored with the rubric). Must appear in the audit file.
* **Prioritized list used:** Which files were on the refactor list and in what order (must appear in the audit file).
* **Files modified:** N
* Key issues fixed (bulleted, grouped)
* Anti-brittleness improvements made
* New helper utilities added (builders, fakes)
* Any tests intentionally left as-is (with justification)
* Suggested next upgrades (if any)

---

## Stop Conditions (must ask)

Stop and ask the user if:

* refactoring requires product code changes to create seams
* an existing test appears to be encoding incorrect behavior
* the suite relies on an external service and needs a strategy
* test performance becomes unacceptable
* uncertain about whether output formatting is part of the contract

---

## Absolute Prohibitions

* Do not lower quality standards “to make tests pass.”
* Do not delete meaningful tests without replacement.
* Do not add broad ignores/suppressions.
* Do not weaken assertions to greenwash failures.
* Do not commit flakiness.

---

### Definition of Done

`/test-quality` is done only when:

* The **audit file** exists and contains: inventory, scores table, prioritized list, Phase B progress (per-file refactor lines), and final summary.
* `just test` passes
* tests are contract-focused, stable, readable
* exception checks are robust (type + relevant details)
* mocking is boundary-only and correct
* brittle patterns are eliminated across the suite
