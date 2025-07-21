"""Test integration with Petal package."""


def test_petal_import():
    """Test that petal can be imported."""
    import petal

    assert petal is not None
    assert hasattr(petal, "__version__")


def test_petal_version():
    """Test that petal version is accessible."""
    import petal

    assert petal.__version__ == "0.1.0"


def test_petal_modules():
    """Test that petal modules are accessible."""
    import petal

    # Test that we can access petal's package structure
    assert hasattr(petal, "__init__")
