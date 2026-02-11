"""Layer 1: Canonical JSON serialization and hashing (deterministic)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize to canonical JSON bytes. Deterministic; stable across key order.

    Supported types: BaseModel (via model_dump(mode='json')), dict, list, str,
    int, float, bool, None. Raises on unsupported types or NaN/Infinity.
    """
    if obj is None:
        data: Any = None
    elif isinstance(obj, BaseModel):
        data = obj.model_dump(mode="json")
    elif isinstance(obj, (dict, list, str, int, float, bool)):
        data = obj
    else:
        raise TypeError(f"Unsupported type for canonical JSON: {type(obj).__name__}")

    raw = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return raw.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    """Return hex-encoded SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: Any) -> str:
    """Hash payload deterministically.

    JSON-like payload -> canonical JSON bytes -> sha256.
    bytes -> sha256 directly.
    File hashing is Layer 0.
    """
    if isinstance(payload, bytes):
        return sha256_bytes(payload)
    return sha256_bytes(canonical_json_bytes(payload))
