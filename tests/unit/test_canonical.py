"""Layer 1: Canonical serialization and hashing (Phase 2)."""

from datetime import UTC, datetime

import pytest

from lily.kernel.canonical import canonical_json_bytes, hash_payload, sha256_bytes


def test_canonical_json_bytes_stable_regardless_of_key_order():
    """Canonical JSON bytes are stable regardless of input dict key order."""
    a = canonical_json_bytes({"b": 2, "a": 1})
    b = canonical_json_bytes({"a": 1, "b": 2})
    assert a == b
    assert a.decode("utf-8") == '{"a":1,"b":2}'


def test_canonical_json_bytes_supported_types():
    """Supports None, bool, int, float, str, list, dict."""
    assert canonical_json_bytes(None) == b"null"
    assert canonical_json_bytes(True) == b"true"
    assert canonical_json_bytes(42) == b"42"
    assert canonical_json_bytes(3.14) == b"3.14"
    assert canonical_json_bytes("hi") == b'"hi"'
    assert canonical_json_bytes([1, 2]) == b"[1,2]"
    assert canonical_json_bytes({"x": 1}) == b'{"x":1}'


def test_canonical_json_bytes_dict_with_datetime_fails_hard():
    """Dict containing non-JSON-serializable value (e.g. datetime) fails hard — no silent coercion."""
    with pytest.raises(
        TypeError,
        match="Object of type datetime is not JSON serializable|not serializable",
    ):
        canonical_json_bytes({"ts": datetime.now(UTC)})
    with pytest.raises(TypeError):
        hash_payload({"ts": datetime.now(UTC)})


def test_canonical_json_bytes_fails_on_unsupported_types():
    """Raises TypeError on unsupported types."""
    with pytest.raises(TypeError, match="Unsupported type"):
        canonical_json_bytes(object())
    with pytest.raises(TypeError, match="Unsupported type"):
        canonical_json_bytes({1, 2, 3})  # set
    with pytest.raises(TypeError, match="Unsupported type"):
        canonical_json_bytes(
            (1, 2)
        )  # tuple - plan says list/dict/str/int/float/bool/None + BaseModel


def test_canonical_json_bytes_fails_on_nan():
    """Raises on NaN (allow_nan=False)."""
    with pytest.raises(ValueError, match="Out of range|NaN|allow_nan"):
        canonical_json_bytes(float("nan"))
    with pytest.raises(ValueError, match="Out of range|Infinity|allow_nan"):
        canonical_json_bytes(float("inf"))


def test_canonical_json_bytes_base_model():
    """BaseModel is converted via model_dump(mode='json')."""
    from pydantic import BaseModel

    class M(BaseModel):
        x: int

    assert canonical_json_bytes(M(x=1)) == b'{"x":1}'


def test_sha256_bytes():
    """sha256_bytes returns hex digest."""
    h = sha256_bytes(b"hello")
    assert isinstance(h, str)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_payload_deterministic():
    """Hash is deterministic across runs for same payload."""
    payload = {"a": 1, "b": 2}
    assert hash_payload(payload) == hash_payload(payload)
    assert hash_payload(payload) == hash_payload({"b": 2, "a": 1})


def test_hash_payload_changes_when_payload_changes():
    """Hash changes when payload changes."""
    h1 = hash_payload({"x": 1})
    h2 = hash_payload({"x": 2})
    h3 = hash_payload({"x": 1, "y": 0})
    assert h1 != h2
    assert h1 != h3
    assert h2 != h3


def test_hash_payload_bytes():
    """hash_payload on bytes hashes directly (no canonical JSON)."""
    h = hash_payload(b"raw bytes")
    assert h == sha256_bytes(b"raw bytes")
