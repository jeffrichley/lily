"""Result code groupings used by CLI rendering policy."""

from __future__ import annotations

HIDE_DATA_CODES = frozenset(
    {
        "persona_listed",
        "persona_set",
        "persona_shown",
        "persona_reloaded",
        "persona_exported",
        "persona_imported",
        "agent_listed",
        "agent_set",
        "agent_shown",
        "style_set",
        "memory_listed",
        "memory_empty",
        "memory_saved",
        "memory_deleted",
        "memory_langmem_saved",
        "memory_langmem_listed",
        "memory_evidence_ingested",
        "jobs_listed",
        "jobs_empty",
        "job_run_completed",
        "jobs_tailed",
        "jobs_tail_empty",
        "jobs_history",
        "jobs_history_empty",
        "jobs_scheduler_status",
        "jobs_paused",
        "jobs_resumed",
        "jobs_disabled",
    }
)

SECURITY_ALERT_CODES = frozenset(
    {
        "provider_policy_denied",
        "skill_capability_denied",
        "security_policy_denied",
        "plugin_contract_invalid",
        "plugin_container_unavailable",
        "plugin_timeout",
        "plugin_runtime_failed",
        "security_preflight_denied",
        "security_hash_mismatch",
        "approval_required",
        "approval_denied",
        "approval_persist_failed",
    }
)

BLUEPRINT_DIAGNOSTIC_CODES = frozenset(
    {
        "blueprint_not_found",
        "blueprint_bindings_invalid",
        "blueprint_compile_failed",
        "blueprint_execution_failed",
        "blueprint_contract_invalid",
    }
)
