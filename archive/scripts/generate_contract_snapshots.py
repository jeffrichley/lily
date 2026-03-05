"""Generate deterministic contract-envelope snapshot fixtures."""

from __future__ import annotations

from pathlib import Path

from lily.runtime.contract_snapshots import write_contract_snapshot


def main() -> None:
    """Generate and write contract snapshot fixture file."""
    output = Path("tests/contracts/contract_envelopes.snapshot.json")
    write_contract_snapshot(output)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
