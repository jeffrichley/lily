"""Base command interface following the Command Pattern."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Protocol


class CommandResult(Protocol):
    """Protocol defining the structure of command results."""

    success: bool
    message: str


@dataclass
class CommandResultImpl:
    """Concrete implementation of CommandResult protocol.

    Attributes:
        success: Whether the command executed successfully
        message: Human-readable summary message
        files_created: List of file paths that were created
        files_skipped: List of file paths that were skipped (already existed)
    """

    success: bool
    message: str
    files_created: List[str]
    files_skipped: List[str]

    def __post_init__(self):
        """Ensure lists are initialized."""
        if not hasattr(self, "files_created") or self.files_created is None:
            self.files_created = []
        if not hasattr(self, "files_skipped") or self.files_skipped is None:
            self.files_skipped = []


class Command(ABC):
    """Abstract base class for all Lily commands.

    All commands must implement execute() and validate() methods.
    """

    @abstractmethod
    def execute(self, *args, **kwargs) -> CommandResult:
        """Execute the command and return result.

        Returns:
            CommandResult instance with success status and message
        """
        pass

    @abstractmethod
    def validate(self, *args, **kwargs) -> bool:
        """Validate prerequisites before execution.

        Returns:
            True if validation passes, False otherwise

        Raises:
            ValueError: If validation fails with specific error details
        """
        pass
