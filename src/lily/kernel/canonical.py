"""Layer 1: Canonical JSON serialization and hashing (deterministic)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from pydantic import BaseModel
from pydantic.types import JsonValue

# Read-only JSON type: covariant Mapping/Sequence so list[str], dict[str,str]
# etc. work without cast. Use for params and returns when data is only read.
type JSONReadOnly = (
    Mapping[str, JSONReadOnly]
    | Sequence[JSONReadOnly]
    | str
    | int
    | float
    | bool
    | None
)

# For building/mutating JSON, use pydantic.types.JsonValue.
# Canonical serialization accepts either (we only read/serialize).
CanonicalJSONInput = BaseModel | JSONReadOnly


def canonical_json_bytes(obj: CanonicalJSONInput) -> bytes:
    """Serialize to canonical JSON bytes. Deterministic; stable across key order.

    Supported types: BaseModel (via model_dump(mode='json')), dict, list, str,
    int, float, bool, None. Raises on unsupported types or NaN/Infinity.

    Args:
        obj: Model or JSON-like structure to serialize.

    Returns:
        UTF-8 encoded canonical JSON bytes.

    Raises:
        TypeError: On unsupported type.
    """
    if obj is None:
        data: JsonValue = None
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
    """Return hex-encoded SHA-256 hash of data.

    Args:
        data: Raw bytes to hash.

    Returns:
        Hex-encoded digest string.
    """
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: bytes | CanonicalJSONInput) -> str:
    """Hash payload deterministically.

    JSON-like payload -> canonical JSON bytes -> sha256.
    bytes -> sha256 directly.
    File hashing is Layer 0.

    Args:
        payload: Bytes or JSON-like payload to hash.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    if isinstance(payload, bytes):
        return sha256_bytes(payload)
    return sha256_bytes(canonical_json_bytes(payload))
