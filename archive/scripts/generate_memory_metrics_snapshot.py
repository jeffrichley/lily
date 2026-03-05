"""Generate deterministic Phase 7 memory observability snapshot."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from lily.observability import memory_metrics
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig


def main() -> None:
    """Generate and write snapshot JSON artifact."""
    memory_metrics.reset()
    root = Path(tempfile.mkdtemp(prefix="lily-phase7-"))
    bundled_dir = root / "bundled"
    workspace_dir = root / "workspace"
    bundled_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"remember", "memory"},
        )
    )
    session = factory.create(active_agent="lily")
    runtime = RuntimeFacade(consolidation_enabled=True)
    _ = runtime.handle_input("/remember favorite number is 42", session)
    _ = runtime.handle_input("/remember token=abc123", session)
    _ = runtime.handle_input("what is my favorite number?", session)
    _ = runtime.handle_input("/memory show favorite", session)
    _ = runtime.handle_input("/memory long consolidate", session)
    _ = runtime.handle_input("/memory long show --domain user_profile", session)
    snapshot = memory_metrics.snapshot().to_dict()
    output = Path("docs/dev/memory_phase7_metrics_post_2026-02-17.json")
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote memory metrics snapshot to {output}")


if __name__ == "__main__":
    main()
