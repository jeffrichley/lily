"""Fixture pack that requires a newer kernel than current. For version mismatch tests."""

from lily.kernel.pack_models import PackDefinition

PACK_DEFINITION = PackDefinition(
    name="needs_new_kernel",
    version="1.0.0",
    minimum_kernel_version="99.0.0",
)
