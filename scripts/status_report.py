"""Render one command project/docs status summary for operators."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "docs" / "dev" / "status.md"
ROADMAP_FILE = ROOT / "docs" / "dev" / "roadmap.md"
DEBT_FILE = ROOT / "docs" / "dev" / "debt" / "debt_tracker.md"
DOMAIN_PLANS_DIR = ROOT / "docs" / "dev" / "plans"
AI_PLANS_DIR = ROOT / ".ai" / "PLANS"
SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400
STATUS_CODE_WIDTH = 2
REV_LIST_COUNT_PARTS = 2
COMMIT_LOG_PARTS = 4


@dataclass(frozen=True)
class DocMeta:
    """Minimal parsed frontmatter metadata."""

    status: str
    last_updated: str


@dataclass(frozen=True)
class PanelVisibility:
    """Panel visibility controls."""

    show_summary: bool
    show_docs: bool
    show_plans: bool
    show_current_focus: bool
    show_git_context: bool


@dataclass(frozen=True)
class SummaryData:
    """Summary panel payload."""

    branch: str
    dirty: bool
    open_debt: int


@dataclass(frozen=True)
class DocsData:
    """Canonical docs table payload."""

    status_meta: DocMeta
    roadmap_meta: DocMeta
    debt_meta: DocMeta


@dataclass(frozen=True)
class PlanRow:
    """One row in the plans table."""

    surface: str
    plan_name: str
    lifecycle: str
    open_tasks: int


@dataclass(frozen=True)
class WorkingTreeCounts:
    """Git working tree status counts."""

    staged: int
    unstaged: int
    untracked: int
    conflicted: int


@dataclass(frozen=True)
class Divergence:
    """Ahead/behind counts vs one reference."""

    ahead: int | None
    behind: int | None
    state: str


@dataclass(frozen=True)
class CommitContext:
    """Latest commit information."""

    sha: str
    subject: str
    author: str
    age: str


@dataclass(frozen=True)
class StashContext:
    """Stash summary details."""

    count: int
    latest: str
    age: str


@dataclass(frozen=True)
class PullRequestContext:
    """PR and CI rollup status."""

    number: str
    state: str
    ci_rollup: str


@dataclass(frozen=True)
class GitContext:
    """Git context panel payload."""

    branch: str
    upstream_branch: str
    working_tree: WorkingTreeCounts
    upstream_divergence: Divergence
    origin_main_divergence: Divergence
    commit: CommitContext
    stash: StashContext
    pr: PullRequestContext

    @property
    def dirty(self) -> bool:
        """Whether the worktree has any local changes."""
        total = (
            self.working_tree.staged
            + self.working_tree.unstaged
            + self.working_tree.untracked
            + self.working_tree.conflicted
        )
        return total > 0


@dataclass(frozen=True)
class StatusSnapshot:
    """Top-level report payload."""

    summary: SummaryData | None
    docs: DocsData | None
    plans: list[PlanRow] | None
    current_focus: list[str] | None
    git_context: GitContext | None


def _parse_bool(value: str) -> bool:
    """Parse permissive bool-like strings for CLI flags."""
    lowered = value.strip().lower()
    if lowered in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value!r}")


def _arg_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument(
        "--show-summary",
        type=_parse_bool,
        nargs="?",
        const=True,
        default=True,
        help="Show Lily Status summary panel (default: true).",
    )
    parser.add_argument(
        "--show-docs",
        type=_parse_bool,
        nargs="?",
        const=True,
        default=True,
        help="Show canonical docs table (default: true).",
    )
    parser.add_argument(
        "--show-plans",
        type=_parse_bool,
        nargs="?",
        const=True,
        default=True,
        help="Show plan trackers table (default: true).",
    )
    parser.add_argument(
        "--show-current-focus",
        type=_parse_bool,
        nargs="?",
        const=True,
        default=True,
        help="Show current focus panel (default: true).",
    )
    parser.add_argument(
        "--show-git-context",
        type=_parse_bool,
        nargs="?",
        const=True,
        default=True,
        help="Show git context panel (default: true).",
    )
    return parser


def _run_command(args: list[str]) -> tuple[str, int]:
    """Run command and return stdout plus return code."""
    result = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


def _frontmatter(path: Path) -> DocMeta:
    """Parse frontmatter for status and last_updated fields."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return DocMeta(status="unknown", last_updated="unknown")

    status = "unknown"
    last_updated = "unknown"
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("status:"):
            status = line.split(":", 1)[1].strip().strip('"')
        if line.startswith("last_updated:"):
            last_updated = line.split(":", 1)[1].strip().strip('"')
    return DocMeta(status=status, last_updated=last_updated)


def _count_open_checkboxes(path: Path) -> int:
    """Count markdown unchecked checkboxes in one file."""
    text = path.read_text(encoding="utf-8")
    return len(re.findall(r"^- \[ \] ", text, flags=re.MULTILINE))


def _current_focus_items() -> list[str]:
    """Extract `Current Focus` bullets from status diary."""
    text = STATUS_FILE.read_text(encoding="utf-8")
    marker = "## Current Focus"
    if marker not in text:
        return []
    section = text.split(marker, 1)[1]
    section = section.split("\n## ", 1)[0]
    return [
        line.strip()[2:].strip()
        for line in section.splitlines()
        if line.strip().startswith("- ")
    ]


def _now_utc() -> datetime:
    """Current time helper for testability."""
    return datetime.now(UTC)


def _relative_age_from_epoch(epoch_text: str) -> str:
    """Format relative age from unix epoch seconds."""
    try:
        timestamp = int(epoch_text)
    except ValueError:
        return "unknown"

    now_ts = int(_now_utc().timestamp())
    delta = max(0, now_ts - timestamp)
    if delta < SECONDS_PER_MINUTE:
        return "just now"
    if delta < SECONDS_PER_HOUR:
        return f"{delta // SECONDS_PER_MINUTE}m ago"
    if delta < SECONDS_PER_DAY:
        return f"{delta // SECONDS_PER_HOUR}h ago"
    return f"{delta // SECONDS_PER_DAY}d ago"


def _parse_working_tree_counts(porcelain: str) -> WorkingTreeCounts:
    """Parse `git status --porcelain` into deterministic counts."""
    staged = 0
    unstaged = 0
    untracked = 0
    conflicted = 0
    conflict_codes = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}

    for line in porcelain.splitlines():
        if len(line) < STATUS_CODE_WIDTH:
            continue
        code = line[:STATUS_CODE_WIDTH]
        if code == "??":
            untracked += 1
            continue

        x_state = code[0]
        y_state = code[1]
        if x_state not in {" ", "?"}:
            staged += 1
        if y_state not in {" ", "?"}:
            unstaged += 1
        if code in conflict_codes or x_state == "U" or y_state == "U":
            conflicted += 1

    return WorkingTreeCounts(
        staged=staged,
        unstaged=unstaged,
        untracked=untracked,
        conflicted=conflicted,
    )


def _parse_divergence(raw_counts: str) -> Divergence:
    """Parse `git rev-list --left-right --count` output."""
    parts = raw_counts.split()
    if len(parts) != REV_LIST_COUNT_PARTS:
        return Divergence(ahead=None, behind=None, state="unknown")
    try:
        behind = int(parts[0])
        ahead = int(parts[1])
    except ValueError:
        return Divergence(ahead=None, behind=None, state="unknown")
    return Divergence(ahead=ahead, behind=behind, state="ok")


def _divergence_for_ref(ref_name: str) -> Divergence:
    """Compute divergence between HEAD and a given git ref."""
    output, returncode = _run_command(
        ["git", "rev-list", "--left-right", "--count", f"{ref_name}...HEAD"]
    )
    if returncode != 0:
        return Divergence(ahead=None, behind=None, state="unavailable")
    return _parse_divergence(output)


def _classify_rollup_entry(check: object) -> str:
    """Classify one `statusCheckRollup` entry."""
    failing_conclusions = {
        "FAILURE",
        "TIMED_OUT",
        "ACTION_REQUIRED",
        "CANCELLED",
        "STARTUP_FAILURE",
    }
    passing_conclusions = {"SUCCESS", "SKIPPED", "NEUTRAL"}
    pending_states = {"PENDING", "IN_PROGRESS", "QUEUED", "REQUESTED", "WAITING"}

    if not isinstance(check, dict):
        return "pending"
    conclusion = check.get("conclusion")
    status = check.get("status")
    if isinstance(conclusion, str) and conclusion in failing_conclusions:
        return "failing"
    if conclusion is None:
        return "pending"
    if isinstance(status, str) and status in pending_states:
        return "pending"
    if isinstance(conclusion, str) and conclusion in passing_conclusions:
        return "pass"
    return "pending"


def _normalize_ci_rollup(pr_json: dict[str, object]) -> str:
    """Normalize GitHub status rollup into one operator-facing state."""
    rollup = pr_json.get("statusCheckRollup")
    if not isinstance(rollup, list):
        return "unavailable"
    if not rollup:
        return "none"

    saw_pass = False
    for check in rollup:
        state = _classify_rollup_entry(check)
        if state == "failing":
            return "failing"
        if state == "pass":
            saw_pass = True
    return "pass" if saw_pass else "pending"


def _collect_pr_context() -> PullRequestContext:
    """Collect PR and CI context via gh CLI."""
    output, returncode = _run_command(
        ["gh", "pr", "view", "--json", "number,state,statusCheckRollup"]
    )
    if returncode != 0:
        return PullRequestContext(
            number="unavailable",
            state="unavailable",
            ci_rollup="unavailable",
        )

    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return PullRequestContext(
            number="unavailable",
            state="unavailable",
            ci_rollup="unavailable",
        )

    number = payload.get("number")
    state = payload.get("state")
    return PullRequestContext(
        number=str(number) if number is not None else "unknown",
        state=state if isinstance(state, str) else "unknown",
        ci_rollup=_normalize_ci_rollup(payload),
    )


def _collect_commit_context() -> CommitContext:
    """Collect latest commit metadata."""
    output, returncode = _run_command(
        ["git", "log", "-1", "--format=%H%x1f%s%x1f%an%x1f%at"]
    )
    if returncode != 0 or not output:
        return CommitContext(
            sha="unknown",
            subject="unknown",
            author="unknown",
            age="unknown",
        )

    parts = output.split("\x1f")
    if len(parts) != COMMIT_LOG_PARTS:
        return CommitContext(
            sha="unknown",
            subject="unknown",
            author="unknown",
            age="unknown",
        )
    return CommitContext(
        sha=parts[0][:12],
        subject=parts[1] or "unknown",
        author=parts[2] or "unknown",
        age=_relative_age_from_epoch(parts[3]),
    )


def _collect_stash_context() -> StashContext:
    """Collect stash summary and latest entry details."""
    output, returncode = _run_command(["git", "stash", "list", "--format=%gd%x1f%gs"])
    if returncode != 0:
        return StashContext(count=0, latest="unavailable", age="unavailable")
    if not output:
        return StashContext(count=0, latest="none", age="none")

    lines = output.splitlines()
    latest_line = lines[0]
    parts = latest_line.split("\x1f", 1)
    latest_summary = (
        parts[1] if len(parts) == STATUS_CODE_WIDTH and parts[1] else latest_line
    )

    ts_output, ts_code = _run_command(
        ["git", "log", "-1", "--format=%at", "refs/stash"]
    )
    latest_age = "unknown"
    if ts_code == 0 and ts_output:
        latest_age = _relative_age_from_epoch(ts_output)

    return StashContext(count=len(lines), latest=latest_summary, age=latest_age)


def _collect_git_context() -> GitContext:
    """Collect all git-context fields for the Git Context panel."""
    branch_output, branch_code = _run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    )
    branch = branch_output if branch_code == 0 and branch_output else "unknown"

    upstream_output, upstream_code = _run_command(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]
    )
    upstream_branch = (
        upstream_output if upstream_code == 0 and upstream_output else "unavailable"
    )

    porcelain_output, porcelain_code = _run_command(["git", "status", "--porcelain"])
    if porcelain_code == 0:
        working_tree = _parse_working_tree_counts(porcelain_output)
    else:
        working_tree = WorkingTreeCounts(
            staged=0,
            unstaged=0,
            untracked=0,
            conflicted=0,
        )

    upstream_divergence = (
        _divergence_for_ref(upstream_branch)
        if upstream_branch != "unavailable"
        else Divergence(ahead=None, behind=None, state="unavailable")
    )
    origin_main_divergence = _divergence_for_ref("origin/main")

    return GitContext(
        branch=branch,
        upstream_branch=upstream_branch,
        working_tree=working_tree,
        upstream_divergence=upstream_divergence,
        origin_main_divergence=origin_main_divergence,
        commit=_collect_commit_context(),
        stash=_collect_stash_context(),
        pr=_collect_pr_context(),
    )


def _collect_summary_data(git_context: GitContext | None = None) -> SummaryData:
    """Collect summary panel payload, reusing git context when already available."""
    if git_context is not None:
        return SummaryData(
            branch=git_context.branch,
            dirty=git_context.dirty,
            open_debt=_count_open_checkboxes(DEBT_FILE),
        )

    branch_output, branch_code = _run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    )
    branch = branch_output if branch_code == 0 and branch_output else "unknown"
    dirty_output, dirty_code = _run_command(["git", "status", "--porcelain"])
    dirty = bool(dirty_output) if dirty_code == 0 else False
    return SummaryData(
        branch=branch,
        dirty=dirty,
        open_debt=_count_open_checkboxes(DEBT_FILE),
    )


def _collect_docs_data() -> DocsData:
    """Collect docs table payload."""
    return DocsData(
        status_meta=_frontmatter(STATUS_FILE),
        roadmap_meta=_frontmatter(ROADMAP_FILE),
        debt_meta=_frontmatter(DEBT_FILE),
    )


def _collect_plan_rows() -> list[PlanRow]:
    """Collect plan table rows."""
    rows: list[PlanRow] = []
    for plan in sorted(DOMAIN_PLANS_DIR.glob("*_execution_plan.md")):
        meta = _frontmatter(plan)
        rows.append(
            PlanRow(
                surface="docs/dev/plans",
                plan_name=plan.name,
                lifecycle=meta.status,
                open_tasks=_count_open_checkboxes(plan),
            )
        )

    rows.extend(
        [
            PlanRow(
                surface=".ai/PLANS",
                plan_name=plan.name,
                lifecycle="n/a",
                open_tasks=_count_open_checkboxes(plan),
            )
            for plan in sorted(AI_PLANS_DIR.glob("*.md"))
        ]
    )
    return rows


def _build_snapshot(visibility: PanelVisibility) -> StatusSnapshot:
    """Collect only the payloads required by enabled panels."""
    git_context = _collect_git_context() if visibility.show_git_context else None
    summary = _collect_summary_data(git_context) if visibility.show_summary else None
    docs = _collect_docs_data() if visibility.show_docs else None
    plans = _collect_plan_rows() if visibility.show_plans else None
    current_focus = _current_focus_items() if visibility.show_current_focus else None

    return StatusSnapshot(
        summary=summary,
        docs=docs,
        plans=plans,
        current_focus=current_focus,
        git_context=git_context,
    )


def _render_summary(console: Console, summary: SummaryData) -> None:
    """Render summary panel."""
    console.print(
        Panel(
            (
                f"Branch: [bold]{summary.branch}[/bold]\n"
                f"Working tree: [bold]{'dirty' if summary.dirty else 'clean'}[/bold]\n"
                f"Open debt items: [bold]{summary.open_debt}[/bold]"
            ),
            title="Lily Status",
            border_style="cyan",
            expand=True,
        )
    )


def _render_docs(console: Console, docs: DocsData) -> None:
    """Render canonical docs table."""
    docs_table = Table(
        title="Canonical Docs", show_header=True, header_style="bold cyan"
    )
    docs_table.add_column("Surface")
    docs_table.add_column("Path")
    docs_table.add_column("Status")
    docs_table.add_column("Last Updated")
    docs_table.add_row(
        "Status Diary",
        "docs/dev/status.md",
        docs.status_meta.status,
        docs.status_meta.last_updated,
    )
    docs_table.add_row(
        "Roadmap",
        "docs/dev/roadmap.md",
        docs.roadmap_meta.status,
        docs.roadmap_meta.last_updated,
    )
    docs_table.add_row(
        "Debt Tracker",
        "docs/dev/debt/debt_tracker.md",
        docs.debt_meta.status,
        docs.debt_meta.last_updated,
    )
    console.print(docs_table)


def _render_plans(console: Console, rows: list[PlanRow]) -> None:
    """Render plans table."""
    plan_table = Table(
        title="Plan Trackers",
        show_header=True,
        header_style="bold cyan",
    )
    plan_table.add_column("Surface")
    plan_table.add_column("Plan")
    plan_table.add_column("Lifecycle")
    plan_table.add_column("Open Tasks")
    for row in rows:
        plan_table.add_row(
            row.surface,
            row.plan_name,
            row.lifecycle,
            str(row.open_tasks),
        )
    console.print(plan_table)


def _render_focus(console: Console, focus: list[str]) -> None:
    """Render current focus panel."""
    focus_text = (
        "\n".join(f"- {item}" for item in focus)
        if focus
        else "No `Current Focus` entries found."
    )
    console.print(
        Panel(focus_text, title="Current Focus", border_style="green", expand=True)
    )


def _format_divergence(divergence: Divergence) -> str:
    """Format divergence field for panel output."""
    if divergence.state != "ok":
        return divergence.state
    if divergence.ahead is None or divergence.behind is None:
        return "unknown"
    return f"ahead {divergence.ahead}, behind {divergence.behind}"


def _render_git_context(console: Console, git_context: GitContext) -> None:
    """Render git context panel."""
    panel_text = "\n".join(
        [
            f"Branch: [bold]{git_context.branch}[/bold]",
            f"Upstream: [bold]{git_context.upstream_branch}[/bold]",
            (
                "Divergence (upstream): "
                f"[bold]{_format_divergence(git_context.upstream_divergence)}[/bold]"
            ),
            (
                "Divergence (origin/main): "
                f"[bold]{_format_divergence(git_context.origin_main_divergence)}[/bold]"
            ),
            (
                "Working tree: "
                f"[bold]staged={git_context.working_tree.staged} "
                f"unstaged={git_context.working_tree.unstaged} "
                f"untracked={git_context.working_tree.untracked} "
                f"conflicted={git_context.working_tree.conflicted}[/bold]"
            ),
            (
                "Commit: "
                f"[bold]{git_context.commit.sha}[/bold] "
                f"{git_context.commit.subject} "
                f"({git_context.commit.author}, {git_context.commit.age})"
            ),
            (
                "Stash: "
                f"[bold]{git_context.stash.count}[/bold], "
                f"latest={git_context.stash.latest} ({git_context.stash.age})"
            ),
            (
                "PR/CI: "
                f"#{git_context.pr.number} "
                f"state={git_context.pr.state} "
                f"ci={git_context.pr.ci_rollup}"
            ),
        ]
    )
    console.print(
        Panel(panel_text, title="Git Context", border_style="magenta", expand=True)
    )


def _docs_to_dict(docs: DocsData) -> dict[str, dict[str, str]]:
    """Serialize docs payload."""
    return {
        "status_diary": {
            "status": docs.status_meta.status,
            "last_updated": docs.status_meta.last_updated,
        },
        "roadmap": {
            "status": docs.roadmap_meta.status,
            "last_updated": docs.roadmap_meta.last_updated,
        },
        "debt_tracker": {
            "status": docs.debt_meta.status,
            "last_updated": docs.debt_meta.last_updated,
        },
    }


def _plans_to_list(rows: list[PlanRow]) -> list[dict[str, str | int]]:
    """Serialize plan rows."""
    return [
        {
            "surface": row.surface,
            "plan": row.plan_name,
            "lifecycle": row.lifecycle,
            "open_tasks": row.open_tasks,
        }
        for row in rows
    ]


def _git_context_to_dict(git_context: GitContext) -> dict[str, object]:
    """Serialize git context payload."""
    return {
        "branch": git_context.branch,
        "upstream_branch": git_context.upstream_branch,
        "working_tree": {
            "staged": git_context.working_tree.staged,
            "unstaged": git_context.working_tree.unstaged,
            "untracked": git_context.working_tree.untracked,
            "conflicted": git_context.working_tree.conflicted,
        },
        "upstream_divergence": {
            "ahead": git_context.upstream_divergence.ahead,
            "behind": git_context.upstream_divergence.behind,
            "state": git_context.upstream_divergence.state,
        },
        "origin_main_divergence": {
            "ahead": git_context.origin_main_divergence.ahead,
            "behind": git_context.origin_main_divergence.behind,
            "state": git_context.origin_main_divergence.state,
        },
        "commit": {
            "sha": git_context.commit.sha,
            "subject": git_context.commit.subject,
            "author": git_context.commit.author,
            "age": git_context.commit.age,
        },
        "stash": {
            "count": git_context.stash.count,
            "latest": git_context.stash.latest,
            "age": git_context.stash.age,
        },
        "pr": {
            "number": git_context.pr.number,
            "state": git_context.pr.state,
            "ci_rollup": git_context.pr.ci_rollup,
        },
    }


def _snapshot_to_json(snapshot: StatusSnapshot, visibility: PanelVisibility) -> str:
    """Serialize snapshot to deterministic JSON."""
    payload = {
        "visibility": {
            "show_summary": visibility.show_summary,
            "show_docs": visibility.show_docs,
            "show_plans": visibility.show_plans,
            "show_current_focus": visibility.show_current_focus,
            "show_git_context": visibility.show_git_context,
        },
        "summary": (
            {
                "branch": snapshot.summary.branch,
                "working_tree": "dirty" if snapshot.summary.dirty else "clean",
                "open_debt_items": snapshot.summary.open_debt,
            }
            if snapshot.summary is not None
            else None
        ),
        "docs": _docs_to_dict(snapshot.docs) if snapshot.docs is not None else None,
        "plans": _plans_to_list(snapshot.plans) if snapshot.plans is not None else None,
        "current_focus": snapshot.current_focus,
        "git_context": (
            _git_context_to_dict(snapshot.git_context)
            if snapshot.git_context is not None
            else None
        ),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _render_rich(snapshot: StatusSnapshot, visibility: PanelVisibility) -> None:
    """Render enabled surfaces in Rich format."""
    console = Console()
    if visibility.show_summary and snapshot.summary is not None:
        _render_summary(console, snapshot.summary)
    if visibility.show_docs and snapshot.docs is not None:
        _render_docs(console, snapshot.docs)
    if visibility.show_plans and snapshot.plans is not None:
        _render_plans(console, snapshot.plans)
    if visibility.show_current_focus and snapshot.current_focus is not None:
        _render_focus(console, snapshot.current_focus)
    if visibility.show_git_context and snapshot.git_context is not None:
        _render_git_context(console, snapshot.git_context)


def main() -> int:
    """Render status report."""
    args = _arg_parser().parse_args()
    visibility = PanelVisibility(
        show_summary=args.show_summary,
        show_docs=args.show_docs,
        show_plans=args.show_plans,
        show_current_focus=args.show_current_focus,
        show_git_context=args.show_git_context,
    )
    snapshot = _build_snapshot(visibility)

    if args.json:
        print(_snapshot_to_json(snapshot, visibility))
        return 0

    _render_rich(snapshot, visibility)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
