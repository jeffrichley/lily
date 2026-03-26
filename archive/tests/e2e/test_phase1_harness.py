"""Phase 1 e2e harness smoke tests."""

from __future__ import annotations

import pytest

from lily.session.store import SESSION_SCHEMA_VERSION


@pytest.mark.e2e
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
    assert payload.get("schema_version") == SESSION_SCHEMA_VERSION
    session = payload.get("session")
    assert isinstance(session, dict)
    assert isinstance(session.get("session_id"), str)
    assert isinstance(session.get("conversation_state"), list)


@pytest.mark.e2e
def test_init_is_idempotent_and_keeps_existing_session(e2e_env: object) -> None:
    """Running `init` again should not invalidate persisted session artifacts."""
    # Arrange - initialized environment with one bundled skill and first run
    env = e2e_env
    env.write_skill(
        root=env.bundled_dir,
        name="echo",
        frontmatter={
            "summary": "Echo",
            "invocation_mode": "llm_orchestration",
        },
    )
    first_init = env.init()
    first_run = env.run("/skills")
    first_payload = env.read_session_payload()
    first_session = first_payload.get("session")
    assert isinstance(first_session, dict)
    first_session_id = first_session.get("session_id")

    # Act - run init again and execute one more command
    second_init = env.init()
    second_run = env.run("/skills")
    second_payload = env.read_session_payload()
    second_session = second_payload.get("session")

    # Assert - both inits/runs succeed and same persisted session id is retained
    assert first_init.exit_code == 0
    assert second_init.exit_code == 0
    assert first_run.exit_code == 0
    assert second_run.exit_code == 0
    assert isinstance(first_session_id, str)
    assert isinstance(second_session, dict)
    assert second_session.get("session_id") == first_session_id


@pytest.mark.e2e
def test_run_unknown_command_returns_error_and_still_persists_session(
    e2e_env: object,
) -> None:
    """Unknown command should fail explicitly while leaving session persisted."""
    # Arrange - initialized environment
    env = e2e_env
    init_result = env.init()

    # Act - invoke unknown slash command
    result = env.run("/definitely_not_a_real_command")

    # Assert - deterministic error path and persisted session payload
    assert init_result.exit_code == 0
    assert result.exit_code == 1
    assert env.session_file.exists()
    payload = env.read_session_payload()
    session = payload.get("session")
    assert payload.get("schema_version") == SESSION_SCHEMA_VERSION
    assert isinstance(session, dict)
    assert isinstance(session.get("session_id"), str)
