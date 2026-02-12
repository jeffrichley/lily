"""Layer 4: Write path policy enforcement. Minimal mtime-based detection."""

from __future__ import annotations

from pathlib import Path


def snapshot_mtimes(root: Path) -> dict[str, float]:
    """Recursively collect path -> mtime for all files under root."""
    result: dict[str, float] = {}
    root_resolved = root.resolve()
    try:
        for p in root_resolved.rglob("*"):
            if p.is_file():
                try:
                    result[str(p)] = p.stat().st_mtime
                except OSError:
                    pass
    except OSError:
        pass
    return result


def get_modified_paths(
    before: dict[str, float],
    after: dict[str, float],
) -> list[str]:
    """Return paths that are new or have different mtime in after."""
    modified: list[str] = []
    for path, mtime in after.items():
        if path not in before or before[path] != mtime:
            modified.append(path)
    return modified


def check_write_paths(
    modified_paths: list[str],
    run_root: Path,
    allow_write_paths: list[str],
    deny_write_paths: list[str],
    *,
    exclude_prefixes: list[str] | None = None,
) -> tuple[bool, str | None]:
    """
    Check modified paths against allow/deny policy.
    Returns (ok, violation_details). violation_details is None if ok.
    - deny takes precedence: any modified path under a deny path -> violation
    - allow: if non-empty, modified path must be under at least one allow path
    - exclude_prefixes: relative to run_root; paths under these are skipped (e.g. logs)
    """
    exclude_prefixes = exclude_prefixes or []
    run_resolved = run_root.resolve()
    exclude_resolved = [
        str((run_resolved / e).resolve()) if not Path(e).is_absolute() else e
        for e in exclude_prefixes
    ]
    allow_resolved = [
        str((run_resolved / a).resolve()) if not Path(a).is_absolute() else a
        for a in allow_write_paths
    ]
    deny_resolved = [
        str((run_resolved / d).resolve()) if not Path(d).is_absolute() else d
        for d in deny_write_paths
    ]

    def _is_under(path_str: str, prefix_str: str) -> bool:
        try:
            Path(path_str).resolve().relative_to(Path(prefix_str).resolve())
            return True
        except ValueError:
            return False

    for path in modified_paths:
        path_res = str(Path(path).resolve())
        skip = any(
            _is_under(path_res, ex) or path_res == str(Path(ex).resolve())
            for ex in exclude_resolved
        )
        if skip:
            continue
        for deny in deny_resolved:
            if _is_under(path_res, deny) or path_res == str(Path(deny).resolve()):
                return False, f"Write to denied path: {path}"
        if allow_write_paths:
            under_any = any(
                _is_under(path_res, a) or path_res == str(Path(a).resolve())
                for a in allow_resolved
            )
            if not under_any:
                return False, f"Write to path not in allowlist: {path}"
    return True, None
