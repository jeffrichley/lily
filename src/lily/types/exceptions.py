"""Custom exceptions for Lily."""


class SkillNotFoundError(Exception):
    """Raised when a skill cannot be found in any search path."""

    pass


class InvalidSkillError(Exception):
    """Raised when a skill file has invalid front matter or structure."""

    pass


class ProjectContextError(Exception):
    """Raised when there's an issue with project context configuration."""

    pass


class SkillCommandError(Exception):
    """Raised when there's an issue with skill command creation or execution."""

    pass


class SkillDiscoveryError(Exception):
    """Raised when there's an issue with skill discovery."""

    pass
