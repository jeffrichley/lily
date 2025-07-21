"""Basic tests for Lily package."""

from lily import __author__, __email__, __version__


def test_version():
    """Test that version is defined."""
    assert __version__ == "0.1.0"


def test_author():
    """Test that author is defined."""
    assert __author__ == "Jeff Richley"


def test_email():
    """Test that email is defined."""
    assert __email__ == "jeffrichley@gmail.com"


def test_import():
    """Test that the package can be imported."""
    import lily

    assert lily is not None
