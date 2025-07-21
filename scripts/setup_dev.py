#!/usr/bin/env python3
"""Development setup script for Lily with Petal integration."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """Run a command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result


def setup_dev_environment():
    """Set up the development environment."""
    print("Setting up Lily development environment...")

    # Check if we're in a CI environment
    is_ci = os.getenv("CI") == "true"

    # Install Lily dependencies
    print("Installing Lily dependencies...")
    run_command("uv pip install -e '.[dev,docs]'")

    # Handle Petal installation
    petal_path = Path("../petal")

    if is_ci:
        print("CI environment detected - Petal should be checked out by CI")
        # In CI, Petal should already be checked out by the workflow
        if petal_path.exists():
            print("Installing Petal from CI checkout...")
            run_command("uv pip install -e ../petal")
        else:
            print("Warning: Petal not found in CI - using GitHub version")
    else:
        # Local development
        if petal_path.exists():
            print("Local Petal found - installing as editable dependency...")
            run_command("uv pip install -e ../petal")
        else:
            print("Local Petal not found - installing from GitHub...")
            run_command("uv pip install git+https://github.com/jeffrichley/petal.git")

    # Install pre-commit hooks
    print("Installing pre-commit hooks...")
    run_command("pre-commit install")

    print("✅ Development environment setup complete!")


if __name__ == "__main__":
    setup_dev_environment()
