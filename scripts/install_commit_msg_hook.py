"""Install a Git commit-msg hook that runs Commitizen (cz check) on the message."""

from pathlib import Path

HOOK_PATH = Path(".git/hooks/commit-msg")
HOOK_CONTENT = """#!/bin/sh
exec uv run cz check --commit-msg-file "$1"
"""


def main() -> None:
    """Install the commit-msg hook that runs cz check on the message."""
    HOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    HOOK_PATH.write_text(HOOK_CONTENT)
    HOOK_PATH.chmod(0o755)
    print("Installed", HOOK_PATH)


if __name__ == "__main__":
    main()
