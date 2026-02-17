"""Validate docs frontmatter and optionally auto-add missing blocks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lily.docs_validator import (
    ValidationConfig,
    default_config,
    validate_docs_frontmatter,
)


def _parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Validate docs frontmatter and active-doc freshness."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root path.",
    )
    parser.add_argument(
        "--max-active-age-days",
        type=int,
        default=21,
        help="Maximum allowed age in days for docs with status: active.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-add placeholder frontmatter to docs missing a frontmatter block.",
    )
    return parser.parse_args()


def main() -> int:
    """Run docs validation and print deterministic diagnostics."""
    args = _parse_args()
    repo_root = args.repo_root.resolve()
    cfg = default_config(repo_root)
    config = ValidationConfig(
        docs_root=cfg.docs_root,
        max_active_age_days=args.max_active_age_days,
        auto_fix_missing_frontmatter=args.fix,
    )
    errors = validate_docs_frontmatter(config)
    if errors:
        print("docs frontmatter validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("docs frontmatter validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
