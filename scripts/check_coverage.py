#!/usr/bin/env python3
"""
Pre-commit hook to ensure 80% test coverage.

This script runs pytest with coverage and fails if coverage is below 80%.
"""

import subprocess
import sys
from pathlib import Path


def run_coverage_check() -> bool:
    """Run pytest with coverage and check if it meets the 80% threshold."""
    try:
        # Run pytest with coverage (pytest handles the 80% threshold)
        result = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                "--cov=src/lily",
                "--cov-report=term-missing",
                "--cov-fail-under=80",
                "tests/",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        # Return the exit code (pytest handles the coverage threshold)
        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        print(f"Error running pytest: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("Error: 'uv' command not found. Please install uv.", file=sys.stderr)
        return False


if __name__ == "__main__":
    success: bool = run_coverage_check()
    if not success:
        print(
            "\n❌ Test coverage is below 80%. Please add more tests.", file=sys.stderr
        )
        print(
            "💡 You can run 'make test-cov' to see detailed coverage report.",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print("\n✅ Test coverage is at least 80%.")
        sys.exit(0)
