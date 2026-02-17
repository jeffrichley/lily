"""Unit tests for memory consolidation engines."""

from __future__ import annotations

from pathlib import Path

from lily.memory import (
    ConsolidationBackend,
    ConsolidationRequest,
    LangMemManagerConsolidationEngine,
    MemoryQuery,
    RuleBasedConsolidationEngine,
    StoreBackedPersonalityMemoryRepository,
)
from lily.memory.langmem_tools import LangMemToolingAdapter
from lily.session.models import Message, MessageRole


def _request(
    *,
    enabled: bool,
    backend: ConsolidationBackend,
    history: tuple[Message, ...],
) -> ConsolidationRequest:
    """Build a shared consolidation request fixture."""
    return ConsolidationRequest(
        session_id="session-test",
        history=history,
        personality_namespace="user_profile/workspace:workspace/persona:lily",
        enabled=enabled,
        backend=backend,
        dry_run=False,
    )


def test_rule_based_consolidation_extracts_and_writes(tmp_path: Path) -> None:
    """Rule-based engine should infer deterministic preference memories."""
    repository = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    engine = RuleBasedConsolidationEngine(personality_repository=repository)

    result = engine.run(
        _request(
            enabled=True,
            backend=ConsolidationBackend.RULE_BASED,
            history=(
                Message(role=MessageRole.USER, content="My favorite color is blue"),
                Message(role=MessageRole.USER, content="My name is Jeff"),
            ),
        )
    )

    assert result.status == "ok"
    assert result.written >= 2
    records = repository.query(
        MemoryQuery(
            query="*",
            namespace="user_profile/workspace:workspace/persona:lily",
            limit=20,
        )
    )
    contents = {item.content for item in records}
    assert "favorite color is blue" in contents
    assert "name is Jeff" in contents


def test_langmem_manager_consolidation_writes(tmp_path: Path) -> None:
    """LangMem-manager engine should persist extracted candidates."""
    adapter = LangMemToolingAdapter(store_file=tmp_path / "memory" / "store.sqlite")
    engine = LangMemManagerConsolidationEngine(tooling_adapter=adapter)

    result = engine.run(
        _request(
            enabled=True,
            backend=ConsolidationBackend.LANGMEM_MANAGER,
            history=(
                Message(role=MessageRole.USER, content="I prefer concise responses"),
            ),
        )
    )

    assert result.status == "ok"
    assert result.written == 1
    rows = adapter.search(
        namespace="user_profile/workspace:workspace/persona:lily",
        query="concise",
        tool_name="test_search",
    )
    contents = {
        str(row.get("value", {}).get("content", ""))
        for row in rows
        if isinstance(row.get("value"), dict)
    }
    assert "prefers concise responses" in contents


def test_consolidation_disabled_returns_disabled_status(tmp_path: Path) -> None:
    """Both engines should short-circuit to disabled status when off."""
    repository = StoreBackedPersonalityMemoryRepository(
        store_file=tmp_path / "memory" / "store.sqlite"
    )
    rule_engine = RuleBasedConsolidationEngine(personality_repository=repository)
    langmem_engine = LangMemManagerConsolidationEngine(
        tooling_adapter=LangMemToolingAdapter(
            store_file=tmp_path / "memory" / "store.sqlite"
        )
    )
    request = _request(
        enabled=False,
        backend=ConsolidationBackend.RULE_BASED,
        history=(),
    )

    rule_result = rule_engine.run(request)
    langmem_result = langmem_engine.run(
        request.model_copy(update={"backend": ConsolidationBackend.LANGMEM_MANAGER})
    )

    assert rule_result.status == "disabled"
    assert langmem_result.status == "disabled"
