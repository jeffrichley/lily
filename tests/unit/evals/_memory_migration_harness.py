"""Memory-migration eval harness for Phase 7 operational gates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lily.config import CheckpointerBackend, CheckpointerSettings
from lily.memory import (
    FileBackedPersonalityMemoryRepository,
    MemoryQuery,
    MemoryWriteRequest,
    StoreBackedPersonalityMemoryRepository,
)
from lily.observability import memory_metrics
from lily.runtime.checkpointing import build_checkpointer
from lily.runtime.conversation import (
    ConversationRequest,
    ConversationResponse,
    _compact_history_langgraph_native,
    _compact_history_rule_based,
)
from lily.runtime.facade import RuntimeFacade
from lily.session.factory import SessionFactory, SessionFactoryConfig
from lily.session.models import Message, MessageRole
from lily.session.store import load_session, save_session

RESTART_MIN_CASES = 2
RESTART_MIN_PASS_RATE = 1.0
PARITY_MIN_CASES = 2
PARITY_MIN_PASS_RATE = 1.0
POLICY_MIN_CASES = 2
POLICY_MIN_PASS_RATE = 1.0
RETRIEVAL_MIN_CASES = 2
RETRIEVAL_MIN_PASS_RATE = 1.0
COMPACTION_MIN_CASES = 3
COMPACTION_MIN_PASS_RATE = 1.0


@dataclass(frozen=True)
class EvalCaseResult:
    """Result for one migration-eval case."""

    case_id: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class EvalSuiteReport:
    """Aggregated results for one migration-eval suite."""

    suite_id: str
    results: tuple[EvalCaseResult, ...]

    @property
    def total(self) -> int:
        """Return total case count."""
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        """Return pass-rate ratio."""
        if self.total == 0:
            return 0.0
        return sum(1 for result in self.results if result.passed) / self.total

    @property
    def failed_case_ids(self) -> tuple[str, ...]:
        """Return failed case ids for diagnostics."""
        return tuple(result.case_id for result in self.results if not result.passed)


class _ConversationCaptureExecutor:
    """Conversation executor fixture that captures last request."""

    def __init__(self) -> None:
        """Initialize capture slot."""
        self.last_request: ConversationRequest | None = None

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Capture request and return deterministic output."""
        self.last_request = request
        return ConversationResponse(text="ok")


def run_restart_continuity_suite(*, temp_dir: Path) -> EvalSuiteReport:
    """Run restart continuity checks for session + sqlite checkpointer."""
    bundled_dir = temp_dir / "bundled"
    workspace_dir = temp_dir / "workspace"
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
    runtime = RuntimeFacade()
    session_file = temp_dir / "session.json"

    _ = runtime.handle_input("/remember favorite number is 42", session)
    save_session(session, session_file)
    restored = load_session(session_file)
    shown = runtime.handle_input("/memory show favorite", restored)

    sqlite_path = temp_dir / "checkpoints.sqlite"
    checkpointer = build_checkpointer(
        CheckpointerSettings(
            backend=CheckpointerBackend.SQLITE,
            sqlite_path=str(sqlite_path),
        )
    )
    _ = RuntimeFacade(conversation_checkpointer=checkpointer.saver)
    sqlite_ok = sqlite_path.exists()
    return EvalSuiteReport(
        suite_id="restart_continuity",
        results=(
            EvalCaseResult(
                case_id="restart_session_restore_continuity",
                passed=shown.code == "memory_listed"
                and "favorite number is 42" in shown.message,
                detail=shown.code,
            ),
            EvalCaseResult(
                case_id="restart_sqlite_checkpointer_initialized",
                passed=sqlite_ok,
                detail=str(sqlite_path),
            ),
        ),
    )


def run_store_parity_suite(*, temp_dir: Path) -> EvalSuiteReport:
    """Run file-vs-store parity checks for long-term personality memory."""
    file_repo = FileBackedPersonalityMemoryRepository(root_dir=temp_dir / "memory-file")
    store_repo = StoreBackedPersonalityMemoryRepository(
        store_file=temp_dir / "memory-store.sqlite"
    )
    request = MemoryWriteRequest(
        namespace="user_profile/workspace:parity/persona:lily",
        content="favorite project is lily",
    )
    file_row = file_repo.remember(request)
    store_row = store_repo.remember(request)
    file_rows = file_repo.query(
        MemoryQuery(
            query="favorite project",
            namespace=request.namespace,
            limit=5,
        )
    )
    store_rows = store_repo.query(
        MemoryQuery(
            query="favorite project",
            namespace=request.namespace,
            limit=5,
        )
    )
    return EvalSuiteReport(
        suite_id="store_parity",
        results=(
            EvalCaseResult(
                case_id="store_parity_write_content",
                passed=file_row.content == store_row.content == request.content,
                detail=f"{file_row.content}|{store_row.content}",
            ),
            EvalCaseResult(
                case_id="store_parity_query_counts",
                passed=len(file_rows) == len(store_rows) == 1,
                detail=f"{len(file_rows)}|{len(store_rows)}",
            ),
        ),
    )


def run_policy_redline_suite(*, temp_dir: Path) -> EvalSuiteReport:
    """Run policy-denial checks for memory write paths."""
    bundled_dir = temp_dir / "bundled"
    workspace_dir = temp_dir / "workspace"
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
    runtime = RuntimeFacade(memory_tooling_enabled=True)
    remember_denied = runtime.handle_input("/remember token=abc123", session)
    tool_denied = runtime.handle_input(
        "/memory long tool remember --domain user_profile token=abc123",
        session,
    )
    return EvalSuiteReport(
        suite_id="policy_redline",
        results=(
            EvalCaseResult(
                case_id="policy_denied_native_remember",
                passed=remember_denied.code == "memory_policy_denied",
                detail=remember_denied.code,
            ),
            EvalCaseResult(
                case_id="policy_denied_langmem_tool",
                passed=tool_denied.code == "memory_policy_denied",
                detail=tool_denied.code,
            ),
        ),
    )


def run_retrieval_relevance_suite(*, temp_dir: Path) -> EvalSuiteReport:
    """Run retrieval relevance and multi-trial consistency checks."""
    bundled_dir = temp_dir / "bundled"
    workspace_dir = temp_dir / "workspace"
    bundled_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    factory = SessionFactory(
        SessionFactoryConfig(
            bundled_dir=bundled_dir,
            workspace_dir=workspace_dir,
            reserved_commands={"remember"},
        )
    )
    session = factory.create(active_agent="lily")
    capture = _ConversationCaptureExecutor()
    runtime = RuntimeFacade(conversation_executor=capture)
    _ = runtime.handle_input("/remember favorite color is blue", session)

    trial_passes = 0
    trials = 3
    for _ in range(trials):
        _ = runtime.handle_input("what is my favorite color?", session)
        if (
            capture.last_request
            and "favorite color is blue" in capture.last_request.memory_summary
        ):
            trial_passes += 1
    return EvalSuiteReport(
        suite_id="retrieval_relevance",
        results=(
            EvalCaseResult(
                case_id="retrieval_summary_contains_relevant_fact",
                passed=trial_passes >= 1,
                detail=f"passes={trial_passes}/{trials}",
            ),
            EvalCaseResult(
                case_id="retrieval_multitrial_consistency",
                passed=trial_passes == trials,
                detail=f"passes={trial_passes}/{trials}",
            ),
        ),
    )


def run_compaction_effectiveness_suite(*, temp_dir: Path) -> EvalSuiteReport:
    """Run deterministic context-compaction checks."""
    del temp_dir

    tool_blob = "x" * 3000
    history = tuple(
        Message(role=MessageRole.TOOL, content=tool_blob) for _ in range(8)
    ) + tuple(
        Message(role=MessageRole.USER, content=f"turn {index}") for index in range(70)
    )
    rule_compacted = _compact_history_rule_based(history)
    native_compacted = _compact_history_langgraph_native(
        history=history,
        max_tokens=120,
    )
    evicted_low_value = len(rule_compacted) < len(history)
    native_bounded = len(native_compacted) < len(history)
    has_system_summary = any(item.role == MessageRole.SYSTEM for item in rule_compacted)
    return EvalSuiteReport(
        suite_id="compaction_effectiveness",
        results=(
            EvalCaseResult(
                case_id="compaction_rule_based_reduces_history_size",
                passed=evicted_low_value,
                detail=f"{len(history)}->{len(rule_compacted)}",
            ),
            EvalCaseResult(
                case_id="compaction_langgraph_native_reduces_history_size",
                passed=native_bounded,
                detail=f"{len(history)}->{len(native_compacted)}",
            ),
            EvalCaseResult(
                case_id="compaction_adds_summary_event",
                passed=has_system_summary,
                detail=str(has_system_summary),
            ),
        ),
    )


def run_memory_phase7_observability_sample(*, temp_dir: Path) -> dict[str, object]:
    """Run representative memory operations and return observability snapshot."""
    memory_metrics.reset()
    bundled_dir = temp_dir / "bundled"
    workspace_dir = temp_dir / "workspace"
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
    listed = runtime.handle_input("/memory long show --domain user_profile", session)
    if listed.data is not None:
        for row in listed.data.get("records", []):
            if isinstance(row, dict) and row.get("last_verified") is not None:
                memory_metrics.record_last_verified(last_verified=datetime.now(UTC))
    return memory_metrics.snapshot().to_dict()
