"""Discovery + registry + policy snapshot for skills CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lily.runtime.config_loader import load_runtime_config
from lily.runtime.config_schema import RuntimeConfig, SkillsConfig
from lily.runtime.skill_discovery import (
    SkillCandidate,
    SkillDiscoveryEvent,
    discover_skill_candidates,
)
from lily.runtime.skill_policies import build_retrieval_blocked_keys
from lily.runtime.skill_registry import SkillRegistry, build_skill_registry


@dataclass
class SkillCliDiagnostics:
    """Everything needed to render ``lily skills list|inspect|doctor``."""

    enabled: bool
    base_path: Path
    runtime_config: RuntimeConfig
    skills_config: SkillsConfig | None
    candidates: tuple[SkillCandidate, ...]
    discovery_events: tuple[SkillDiscoveryEvent, ...]
    registry: SkillRegistry
    policy_blocked: dict[str, str]

    @classmethod
    def from_config_paths(
        cls,
        config_path: str | Path,
        override_config_path: str | Path | None = None,
    ) -> SkillCliDiagnostics:
        """Load runtime config and compute discovery, registry merge, and list blocks.

        Args:
            config_path: Base runtime config path.
            override_config_path: Optional override config path.

        Returns:
            Diagnostics snapshot (skills may be disabled).
        """
        resolved = Path(config_path)
        base_path = resolved.resolve().parent
        runtime = load_runtime_config(config_path, override_config_path)
        skills_cfg = runtime.skills
        if skills_cfg is None or not skills_cfg.enabled:
            return cls(
                enabled=False,
                base_path=base_path,
                runtime_config=runtime,
                skills_config=skills_cfg,
                candidates=(),
                discovery_events=(),
                registry=SkillRegistry({}, []),
                policy_blocked={},
            )

        candidates, discovery_events = discover_skill_candidates(
            skills_cfg,
            base_path=base_path,
        )
        cand_tuple = tuple(candidates)
        ev_tuple = tuple(discovery_events)
        registry = build_skill_registry(candidates, skills_cfg)
        policy_blocked = build_retrieval_blocked_keys(candidates, skills_cfg)
        return cls(
            enabled=True,
            base_path=base_path,
            runtime_config=runtime,
            skills_config=skills_cfg,
            candidates=cand_tuple,
            discovery_events=ev_tuple,
            registry=registry,
            policy_blocked=dict(policy_blocked),
        )
