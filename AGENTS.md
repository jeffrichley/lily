# AGENTS

## Feature vs Internal Work Separation

- Keep roadmap and punchlist items split into:
  - `User-visible features`
  - `Internal engineering tasks`
- Do not mix internal implementation details into user-visible feature bullets.

## Phase Execution Contract

- Before implementing a phase, define:
  - explicit acceptance criteria
  - explicit non-goals
  - required tests and gates
- Treat phase scope as fixed unless changed explicitly by the user.

## Commit Policy

- Commit at the end of each completed phase.
- For follow-up work after a completed phase:
  - use one commit for UX polish
  - use one commit for docs-only updates

## PR Expectations

- PR description must clearly state:
  - what is fully complete
  - what is compatibility/temporary
  - what remains deferred
- Avoid implying full subsystem completion when only compatibility surfaces exist.

## CLI Output UX Rule

- User-facing commands should prefer structured Rich rendering (tables/panels).
- Avoid raw JSON data panels for default interactive output unless a dedicated JSON mode is requested.

## Dispatch Pattern Rule

- Prefer strategy/registry dispatch over long `if`/`elif` chains when branching by mode/backend/type.
- Use explicit handler maps keyed by stable identifiers so adding new backends/modes does not require editing a large conditional block.

## Warning Policy

- Treat test/runtime warnings as defects, not noise.
- Before merge, quality/test runs should be warning-clean.
- If a warning cannot be eliminated immediately, document:
  - exact warning signature
  - why it is currently unavoidable
  - owner and target date for removal
- Do not add new warning suppressions unless explicitly approved by the user.
