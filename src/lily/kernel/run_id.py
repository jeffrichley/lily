"""Run ID generation. Layer 0: single dedicated function, uuid4."""

import uuid


def generate_run_id() -> str:
    """Generate a new run ID. Standard UUID string, unique per run."""
    return str(uuid.uuid4())
