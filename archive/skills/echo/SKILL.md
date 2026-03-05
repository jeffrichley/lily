---
summary: Echo the user payload as uppercase text only.
invocation_mode: llm_orchestration
---
# Echo

Transform the incoming user payload to uppercase and return only that uppercase text.

Rules:
- Do not add punctuation unless already present in the payload.
- Do not prepend labels like "Echo:".
- Do not include explanations.
