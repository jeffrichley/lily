# Contributing to Lily

## Pull request description (required)

Every pull request **must** use the repository PR template. The description is validated in CI; the PR will not pass until the body satisfies the checks below.

### What we check

1. **Required sections**  
   The PR body must include these headings (from `.github/pull_request_template.md`):
   - **Summary**
   - **Verification**
   - **Risk Assessment**
   - **Checklist (Ruthless)**

2. **Decisions, not placeholders**  
   You must actually answer (check at least one option) for:
   - **Risk Level** (Low / Medium / High)
   - **Perf Impact** (no impact / improvement / regression)
   - **Breaking Change?** (Yes / No)
   - **Config / Schema Changes** (None / Yes)

3. **Verification gates**  
   The Verification section must mention:
   - `/cleanup` (quality + tests)
   - `/coverage` (coverage threshold)  

   For **non-draft** PRs, the checkboxes for those two gates must be **checked**. Draft PRs can leave them unchecked until the PR is ready for review.

4. **Minimal content**  
   - **Summary:** At least a short real summary (not only HTML comments or placeholders).
   - **Tests Added / Updated:** Either list the tests you added/updated or explicitly write "None" (e.g. for doc-only PRs).
   - **Failure Modes Considered:** Either add at least one bullet or explicitly write "N/A".

### How to comply

1. When opening a PR, use the **template** shown by GitHub (it’s based on `.github/pull_request_template.md`). If you didn’t use it, click “Get started” or open the template and copy its structure into the description.
2. Fill in every required section. Replace placeholders and comments with real content.
3. Check **one** option for Risk Level, Perf Impact, Breaking Change?, and Config / Schema Changes.
4. Before marking the PR ready for review, run `/cleanup` and `/coverage` (or `just quality-check` and `just test-cov`), then **check** the corresponding boxes in **Required Gates** under Verification.

### If the check fails

CI will post a failure with a list of what’s missing. Fix the PR description:

- Add any missing headings (copy from the template).
- Check the required checkboxes in Risk Level, Perf Impact, Breaking Change?, and Config / Schema Changes.
- Add a short Summary, and either list tests (or say "None") and failure modes (or say "N/A").
- For non-draft PRs, check the /cleanup and /coverage boxes in Verification.

Headings are matched case-insensitively; small wording variations are allowed. The goal is a complete, reviewable description, not exact wording.

### Local quality and tests

Before pushing, run:

- `just quality-check` — same gates as CI (format, lint, types, complexity, etc.).
- `just test-cov` — tests with coverage (threshold from `pyproject.toml`).

If both pass locally, CI should pass too.

### Pre-commit hooks (optional)

To run format, lint, and commit-message checks automatically before each commit:

```bash
just pre-commit-install
```

This installs pre-commit hooks from `.pre-commit-config.yaml`, including a commit-msg hook that enforces conventional commits. You can also run `just pre-commit` to check all files without committing.
