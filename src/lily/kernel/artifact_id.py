"""Artifact ID generation. Layer 0: single function, uuid4."""

import uuid


def generate_artifact_id() -> str:
    """Generate a new artifact ID (UUID); used as directory name under artifacts/.

    Returns:
        A new UUID string.
    """
    return str(uuid.uuid4())
