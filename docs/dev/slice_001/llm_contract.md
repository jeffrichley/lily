---
owner: "TBD"
last_updated: "TBD"
status: "reference"
source_of_truth: false
---

# Slice 001 LLM Contract

Purpose: define the exact runtime contract for LLM orchestration so implementation can proceed without leaking framework details into the rest of Lily.

Scope: this contract applies to `llm_orchestration` skill execution via the internal backend boundary (`runtime.llm_backend`).

## 1. Boundary And Ownership

- Public to Lily runtime:
  - `LlmRunRequest`
  - `LlmRunResponse`
  - `LlmBackend.run(request) -> response`
- Private implementation detail:
  - LangChain agent composition
  - model provider SDK wiring
  - prompt/agent internals

Rule: command/session/skills modules must never import LangChain directly.

## 2. Request Contract

`LlmRunRequest` fields:

- `session_id: str`
- `skill_name: str`
- `skill_summary: str`
- `user_text: str`
- `model_name: str`

Field constraints:

- `skill_name` must be non-empty and come from snapshot entry name.
- `user_text` may be empty.
- `model_name` must come from `session.model_settings.model_name`.
- `session_id` must come from active session.

## 3. Response Contract

`LlmRunResponse` fields:

- `text: str`

Field constraints:

- `text` must always be non-empty for successful runs.
- `text` is final user-facing content for the command path.

## 4. Failure Contract

Backend failures are mapped to deterministic command errors by executor/invoker layers.

Error categories:

- `backend_unavailable`: provider/network/runtime unavailable.
- `backend_timeout`: timeout exceeded.
- `backend_invalid_response`: response missing required output contract.
- `backend_policy_blocked`: content blocked by configured policy.

Mapping rule:

- No raw exception trace is returned to users.
- User-facing message must be explicit and stable.
- Internal logging captures full exception metadata.

## 5. Retry Policy

Default policy for `llm_orchestration`:

- Max attempts: `2` (1 initial + 1 retry).
- Retryable categories:
  - transient transport/provider errors
  - timeout
- Non-retryable categories:
  - policy blocked
  - schema/contract validation failures
  - deterministic input validation failures

Backoff:

- fixed backoff of `250ms` between attempt 1 and retry.

## 6. Guardrails

Input guardrails:

- Reject execution if skill metadata is missing/invalid (already enforced upstream).
- Normalize whitespace in `user_text`; do not alter semantic content.

Output guardrails:

- Response must satisfy `LlmRunResponse` schema.
- Empty output is invalid and treated as `backend_invalid_response`.

Prompt boundary guardrails:

- Skill identity and user payload must be passed as separate structured fields.
- No hidden fallback skill selection from inside backend implementation.

## 7. Model Policy

Model selection source:

- Use `session.model_settings.model_name` exactly.

No implicit fallback for Slice 001:

- If requested model is unsupported/unavailable, fail explicitly.

Future extension point:

- policy-based model routing may be added later, but must remain deterministic and documented.

## 8. Observability Contract

Minimum structured runtime event fields:

- `session_id`
- `skill_name`
- `invocation_mode`
- `model_name`
- `attempt`
- `duration_ms`
- `status`
- `error_code` (if failed)

Redaction:

- Do not log secrets from environment variables.
- Do not log full provider credentials.

## 9. Determinism Requirements On Command Surface

- `/skill <name>` remains exact-match and snapshot-only.
- LLM backend does not choose alternate skills.
- Errors are explicit and no-fallback.
- Same command path behavior is preserved regardless of backend framework.

## 10. Acceptance Criteria For `LangChainBackend.run(...)`

- Accepts `LlmRunRequest` and returns valid `LlmRunResponse`.
- Implements retry policy exactly as defined above.
- Emits structured observability fields.
- Surfaces deterministic mapped failures to caller.
- Keeps LangChain-specific types/imports contained in `runtime.llm_backend`.
