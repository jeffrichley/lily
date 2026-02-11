"""Artifact ID generation. Layer 0: single function, uuid4."""

import uuid


def generate_artifact_id() -> str:
    """Generate a new artifact ID. UUID string, unique per artifact; used as directory name under artifacts/."""
    return str(uuid.uuid4())
