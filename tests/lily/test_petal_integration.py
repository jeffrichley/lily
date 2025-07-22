"""Smoke test for basic project setup."""


def test_basic_import():
    """Test that we can import basic modules."""
    # Test that we can import our own package
    import lily

    assert lily is not None
