"""Example of using Petal within Lily framework."""

import petal
from lily import __version__ as lily_version


def main():
    """Demonstrate Petal integration with Lily."""
    print(f"Lily version: {lily_version}")
    print(f"Petal version: {petal.__version__}")

    # You can now use Petal's functionality within Lily
    print("✅ Petal is successfully integrated with Lily!")

    # Example: You could import and use Petal modules here
    # from petal.core import SomeClass
    # from petal.types import SomeType

    print("Ready for tandem development!")


if __name__ == "__main__":
    main()
