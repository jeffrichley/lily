---
owner: "@team"
last_updated: "2026-02-17"
status: "reference"
source_of_truth: false
---

# Echo Contract (Slice 001)

Purpose: define deterministic expected behavior for the bundled `echo` skill used in vertical-slice smoke tests.

## Input

- User payload text passed via `/skill echo <payload>`.

## Output

- Return exactly the payload transformed to uppercase.

Examples:

- input: `hello world`
- output: `HELLO WORLD`

- input: `Ping?`
- output: `PING?`

## Constraints

- No additional prose.
- No labels or prefixes.
- No fallback to any other skill.
- Invocation must come from explicit snapshot lookup of `echo`.
