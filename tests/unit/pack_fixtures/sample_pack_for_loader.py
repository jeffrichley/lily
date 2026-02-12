"""Fixture pack module for pack_loader tests. Exports PACK_DEFINITION."""

from lily.kernel.pack_models import PackDefinition

PACK_DEFINITION = PackDefinition(
    name="sample_pack",
    version="1.0.0",
    minimum_kernel_version="0.1.0",
)
