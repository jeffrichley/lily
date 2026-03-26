"""Unit tests for status_report CLI behavior and helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[3] / "scripts" / "status_report.py"
MODULE_SPEC = importlib.util.spec_from_file_location("status_report", MODULE_PATH)
assert MODULE_SPEC is not None
assert MODULE_SPEC.loader is not None
status_report = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = status_report
MODULE_SPEC.loader.exec_module(status_report)


@pytest.mark.unit
def test_parse_working_tree_counts_handles_mixed_porcelain_codes() -> None:
    """Porcelain parsing should classify staged/unstaged/untracked/conflicted."""
    # Arrange - build mixed porcelain content.
    porcelain = "\n".join(
        [
            " M tracked.txt",
            "M  staged.txt",
            "MM mixed.txt",
            "?? new.txt",
            "UU conflict.txt",
        ]
    )

    # Act - parse counts.
    counts = status_report._parse_working_tree_counts(porcelain)

    # Assert - each category count is deterministic.
    assert counts.staged == 3
    assert counts.unstaged == 3
    assert counts.untracked == 1
    assert counts.conflicted == 1


@pytest.mark.unit
def test_parse_divergence_reads_rev_list_output() -> None:
    """Divergence parser should map left/right counts to behind/ahead."""
    # Arrange - provide one rev-list output sample.
    raw = "2 5"

    # Act - parse divergence values.
    divergence = status_report._parse_divergence(raw)

    # Assert - behind and ahead map correctly.
    assert divergence.state == "ok"
    assert divergence.behind == 2
    assert divergence.ahead == 5


@pytest.mark.unit
def test_collect_pr_context_returns_unavailable_when_gh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PR context should degrade to unavailable when gh is not usable."""
    # Arrange - force gh command failure.
    monkeypatch.setattr(status_report, "_run_command", lambda _args: ("", 1))

    # Act - collect PR context.
    pr = status_report._collect_pr_context()

    # Assert - fallback values are explicit.
    assert pr.number == "unavailable"
    assert pr.state == "unavailable"
    assert pr.ci_rollup == "unavailable"


@pytest.mark.unit
def test_show_flags_default_to_true() -> None:
    """All positive show flags should default to true."""
    # Arrange - build parser with defaults.
    parser = status_report._arg_parser()

    # Act - parse no-arg invocation.
    args = parser.parse_args([])

    # Assert - every show flag defaults true.
    assert args.show_summary is True
    assert args.show_docs is True
    assert args.show_plans is True
    assert args.show_current_focus is True
    assert args.show_git_context is True


@pytest.mark.unit
def test_build_snapshot_skips_subprocess_calls_for_hidden_panels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Collection work should be skipped when panel visibility is false."""
    # Arrange - disable every panel and track subprocess use.
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str]) -> tuple[str, int]:
        calls.append(cmd)
        return "", 0

    monkeypatch.setattr(status_report, "_run_command", _fake_run)
    visibility = status_report.PanelVisibility(
        show_summary=False,
        show_docs=False,
        show_plans=False,
        show_current_focus=False,
        show_git_context=False,
    )

    # Act - build snapshot from disabled visibility.
    snapshot = status_report._build_snapshot(visibility)

    # Assert - no payloads and no subprocess probes.
    assert snapshot.summary is None
    assert snapshot.docs is None
    assert snapshot.plans is None
    assert snapshot.current_focus is None
    assert snapshot.git_context is None
    assert calls == []


@pytest.mark.unit
def test_snapshot_to_json_contains_expected_git_context_shape() -> None:
    """JSON mode should include deterministic keys with git_context payload."""
    # Arrange - craft deterministic snapshot payload.
    snapshot = status_report.StatusSnapshot(
        summary=status_report.SummaryData(branch="feat/x", dirty=False, open_debt=3),
        docs=None,
        plans=None,
        current_focus=["Ship panel flags"],
        git_context=status_report.GitContext(
            branch="feat/x",
            upstream_branch="origin/feat/x",
            working_tree=status_report.WorkingTreeCounts(
                staged=1,
                unstaged=2,
                untracked=3,
                conflicted=0,
            ),
            upstream_divergence=status_report.Divergence(ahead=4, behind=1, state="ok"),
            origin_main_divergence=status_report.Divergence(
                ahead=6,
                behind=2,
                state="ok",
            ),
            commit=status_report.CommitContext(
                sha="abc123",
                subject="feat: test",
                author="dev",
                age="1h ago",
            ),
            stash=status_report.StashContext(count=1, latest="WIP", age="2h ago"),
            pr=status_report.PullRequestContext(
                number="12", state="OPEN", ci_rollup="pass"
            ),
        ),
    )
    visibility = status_report.PanelVisibility(
        show_summary=True,
        show_docs=False,
        show_plans=False,
        show_current_focus=True,
        show_git_context=True,
    )

    # Act - serialize snapshot to JSON.
    payload = json.loads(status_report._snapshot_to_json(snapshot, visibility))

    # Assert - expected keys and nested git fields exist.
    assert set(payload.keys()) == {
        "current_focus",
        "docs",
        "git_context",
        "plans",
        "summary",
        "visibility",
    }
    assert payload["git_context"]["working_tree"] == {
        "staged": 1,
        "unstaged": 2,
        "untracked": 3,
        "conflicted": 0,
    }
    assert payload["git_context"]["pr"]["ci_rollup"] == "pass"


@pytest.mark.unit
def test_main_respects_false_show_flag_for_git_context(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Explicit false show flag should disable git panel collection and payload."""
    # Arrange - disable git/docs/plans/focus and mock command probes.
    commands: list[list[str]] = []

    def _fake_run(cmd: list[str]) -> tuple[str, int]:
        commands.append(cmd)
        if cmd[:2] == ["git", "rev-parse"]:
            return "feat/branch", 0
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return "", 0
        return "", 0

    monkeypatch.setattr(status_report, "_run_command", _fake_run)
    monkeypatch.setattr(
        status_report,
        "_count_open_checkboxes",
        lambda _path: 0,
    )
    monkeypatch.setattr(
        status_report,
        "_collect_docs_data",
        lambda: pytest.fail("docs should not collect"),
    )
    monkeypatch.setattr(
        status_report,
        "_collect_plan_rows",
        lambda: pytest.fail("plans should not collect"),
    )
    monkeypatch.setattr(status_report, "_current_focus_items", lambda: [])
    monkeypatch.setattr(
        "sys.argv",
        [
            "status_report.py",
            "--json",
            "--show-docs",
            "false",
            "--show-plans",
            "false",
            "--show-current-focus",
            "false",
            "--show-git-context",
            "false",
        ],
    )

    # Act - run CLI main with JSON mode.
    exit_code = status_report.main()
    payload = json.loads(capsys.readouterr().out)

    # Assert - git_context hidden and gh probes absent.
    assert exit_code == 0
    assert payload["git_context"] is None
    assert payload["visibility"]["show_git_context"] is False
    assert all(cmd[:2] != ["gh", "pr"] for cmd in commands)
