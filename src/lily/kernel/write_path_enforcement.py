"""Layer 4: Write path policy enforcement. Minimal mtime-based detection."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import NamedTuple


class _ResolvedPolicy(NamedTuple):
    """Resolved allow/deny/exclude lists and allowlist-active flag."""

    exclude: list[str]
    deny: list[str]
    allow: list[str]
    allow_non_empty: bool


def snapshot_mtimes(root: Path) -> dict[str, float]:
    """Recursively collect path -> mtime for all files under root.

    Args:
        root: Directory to scan.

    Returns:
        Map of absolute path string to mtime.
    """
    result: dict[str, float] = {}
    root_resolved = root.resolve()
    try:
        for p in root_resolved.rglob("*"):
            if p.is_file():
                with contextlib.suppress(OSError):
                    result[str(p)] = p.stat().st_mtime
    except OSError:
        pass
    return result


def get_modified_paths(
    before: dict[str, float],
    after: dict[str, float],
) -> list[str]:
    """Return paths that are new or have different mtime in after.

    Args:
        before: Path -> mtime before.
        after: Path -> mtime after.

    Returns:
        List of path strings that are new or changed.
    """
    modified: list[str] = []
    for path, mtime in after.items():
        if path not in before or before[path] != mtime:
            modified.append(path)
    return modified


def _resolve_path_list(run_resolved: Path, paths: list[str]) -> list[str]:
    return [
        str((run_resolved / p).resolve()) if not Path(p).is_absolute() else p
        for p in paths
    ]


def _is_under(path_str: str, prefix_str: str) -> bool:
    try:
        Path(path_str).resolve().relative_to(Path(prefix_str).resolve())
        return True
    except ValueError:
        return False


def _path_matches_prefix(path_res: str, prefix_str: str) -> bool:
    return _is_under(path_res, prefix_str) or path_res == str(
        Path(prefix_str).resolve()
    )


def _check_one_path(path: str, path_res: str, policy: _ResolvedPolicy) -> str | None:
    """Return violation message if path violates policy, else None.

    Args:
        path: Original path string.
        path_res: Resolved absolute path string.
        policy: Resolved allow/deny/exclude policy.

    Returns:
        Violation message string or None if allowed.
    """
    if any(_path_matches_prefix(path_res, ex) for ex in policy.exclude):
        return None
    for deny in policy.deny:
        if _path_matches_prefix(path_res, deny):
            return f"Write to denied path: {path}"
    if policy.allow_non_empty:
        under_any = any(_path_matches_prefix(path_res, a) for a in policy.allow)
        if not under_any:
            return f"Write to path not in allowlist: {path}"
    return None


def check_write_paths(
    modified_paths: list[str],
    run_root: Path,
    allow_write_paths: list[str],
    deny_write_paths: list[str],
    *,
    exclude_prefixes: list[str] | None = None,
) -> tuple[bool, str | None]:
    """Check modified paths against allow/deny policy.

    Deny takes precedence. If allow list is non-empty, path must be under one.
    Paths under exclude_prefixes are skipped.

    Args:
        modified_paths: Paths that were new or changed.
        run_root: Run directory root for resolving relative paths.
        allow_write_paths: Allowed write path prefixes (relative to run_root).
        deny_write_paths: Denied write path prefixes (relative to run_root).
        exclude_prefixes: Paths under these (relative to run_root) are skipped.

    Returns:
        (ok, violation_details). violation_details is None if ok.
    """
    exclude_prefixes = exclude_prefixes or []
    run_resolved = run_root.resolve()
    policy = _ResolvedPolicy(
        exclude=_resolve_path_list(run_resolved, exclude_prefixes),
        deny=_resolve_path_list(run_resolved, deny_write_paths),
        allow=_resolve_path_list(run_resolved, allow_write_paths),
        allow_non_empty=bool(allow_write_paths),
    )
    for path in modified_paths:
        path_res = str(Path(path).resolve())
        violation = _check_one_path(path, path_res, policy)
        if violation is not None:
            return False, violation
    return True, None
