"""Phase 1 e2e harness smoke tests."""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_init_run_and_session_persisted(e2e_env: object) -> None:
    """`init -> run` should create deterministic persisted session artifacts."""
    # Arrange - one bundled skill and initialized environment
    # Arrange - one bundled skill so /skills output is non-empty
    env = e2e_env
    env.write_skill(
        root=env.bundled_dir,
        name="echo",
        frontmatter={
            "summary": "Echo",
            "invocation_mode": "llm_orchestration",
        },
    )

    # Act - initialize workspace and run a command
    init_result = env.init()
    run_result = env.run("/skills")

    # Assert - successful execution and persisted session payload
    assert init_result.exit_code == 0
    assert run_result.exit_code == 0
    assert env.session_file.exists()
    payload = env.read_session_payload()
    assert payload.get("schema_version") == 1
    session = payload.get("session")
    assert isinstance(session, dict)
    assert isinstance(session.get("session_id"), str)
    assert isinstance(session.get("conversation_state"), list)
