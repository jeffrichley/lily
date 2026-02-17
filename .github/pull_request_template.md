# Summary

<!--
1–3 sentences. What changed and why.
Focus on user-visible behavior and/or system guarantees.
No implementation narration.
-->

## Problem / Motivation

<!--
What problem does this solve?
Why now?
Link issues, docs, incidents, or design notes if they exist.
-->

## Approach

<!--
High-level approach and key design decisions.
If trade-offs exist, state them.
If refactor, explain what risk is reduced / what capability is enabled.
-->

---

# What Changed

## User-facing / Contract Changes

<!--
If none, say: "None."
If this changes a public API/CLI/schema/config contract, describe it here.
-->

## Key Changes (bullets)

- <!-- e.g., Added X to Y -->
- <!-- e.g., Updated Z behavior to ... -->

## Out of Scope

<!--
Explicitly list tempting adjacent work that was not done to keep PR focused.
-->

---

# Verification

## Required Gates

- [ ] `/cleanup` run (quality + tests) and **green**
- [ ] `/coverage` run (coverage threshold) and **green**
- [ ] `/test-quality` considered (new tests follow quality standards)

## Tests Added / Updated

<!--
List tests with intent. Prefer behavior names over file names.
Example:
- Added unit tests for router decision table (valid routes + error handling)
- Added integration test for engine runner contract with fake engine
-->

- <!-- -->
- <!-- -->

## How to Reproduce / Validate

<!--
Give exact commands or steps. A reviewer should be able to verify quickly.
-->

```bash
# e.g.
just quality-check
just test-cov
```

---

# Risk Assessment

## Risk Level

- [ ] Low (localized change, strong tests, minimal surface area)
- [ ] Medium (touches core paths, moderate surface area, good tests)
- [ ] High (wide surface area, complex behavior, or migration involved)

## Failure Modes Considered

<!--
List the realistic ways this could break in prod/dev, and why it's safe.
Examples:
- invalid config -> graceful error
- missing cache dir -> fallback behavior
- concurrency -> deterministic order
-->

- <!-- -->
- <!-- -->

## Rollback Plan

<!--
How to revert safely if needed.
Examples:
- revert commit
- feature flag off
- config toggle back
-->

- <!-- -->

---

# Performance / Scalability

## Perf Impact

- [ ] No measurable impact expected
- [ ] Potential improvement
- [ ] Potential regression (explain below)

<!--
If relevant, include:
- complexity changes
- hot path changes
- allocations / IO changes
- expected workload effects
-->

---

# Compatibility / Migration

## Breaking Change?

- [ ] No
- [ ] Yes (details below)

<!--
If breaking:
- what breaks
- who is affected
- migration steps
- timeline (if any)
-->

## Config / Schema Changes

- [ ] None
- [ ] Yes (details below)

<!--
If yes, include before/after examples or a minimal snippet.
-->

---

# Documentation Impact

- [ ] No docs update needed
- [ ] Docs updated in this PR (list paths below)
- [ ] Docs follow-up required (owner + target date below)

<!--
If docs were updated, list canonical paths (for example: docs/dev/status.md).
If follow-up is required, include owner and target date and link the follow-up item.
-->

---

# Security / Privacy

- [ ] No secrets/keys added
- [ ] No sensitive data logged
- [ ] No new external network calls (or documented below)

<!--
If anything security-relevant changed, explain it here.
-->

---

# Code Health

## Debt / Follow-ups

<!--
List follow-ups that are real and actionable.
Prefer "create issue" style phrasing.
-->

- <!-- -->

## Reviewer Notes

<!--
Where should reviewers focus?
What file/area is most important?
Any tricky parts?
-->

- <!-- -->

---

# Checklist (Ruthless)

## PR Hygiene

- [ ] PR is **single-purpose** (no mixed refactor + feature + drive-by formatting)
- [ ] No generated artifacts or caches committed
- [ ] No debug prints / commented code left behind
- [ ] Names and docs updated where needed
- [ ] Errors are actionable (type + key context; not fragile string matching)

## Test Quality (non-negotiable)

- [ ] Tests assert **behavior/contracts**, not implementation details
- [ ] Mocks only at boundaries; no deep mock chains
- [ ] Exception tests do **not** exact-match full message strings
- [ ] Tests are deterministic (seeded randomness, no wall-clock reliance)
- [ ] Tests are readable (AAA structure, clear naming, one reason to fail)

## Coverage Quality

- [ ] Added tests cover high-value logic (not “coverage padding”)
- [ ] Edge cases and failure paths included where meaningful
- [ ] Coverage improvements map to confidence improvements
