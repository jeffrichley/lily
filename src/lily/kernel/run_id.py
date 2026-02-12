"""Run ID generation. Layer 0: single dedicated function, uuid4."""

import uuid


def generate_run_id() -> str:
    """Generate a new run ID. Standard UUID string, unique per run.

    Returns:
        New UUID string (e.g. for .iris/runs/<run_id>/).
    """
    return str(uuid.uuid4())
