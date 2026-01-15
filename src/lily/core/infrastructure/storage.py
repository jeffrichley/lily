"""Storage and logging infrastructure for filesystem operations."""

import hashlib
import importlib.resources
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Optional

from lily.core.infrastructure.models.log import LogAction, LogEntryModel


class Storage:
    """Handles filesystem operations for Lily project artifacts."""

    def create_directory(self, path: Path) -> None:
        """Create directory if it doesn't exist.

        Args:
            path: Directory path to create
        """
        path.mkdir(parents=True, exist_ok=True)

    def create_file(self, path: Path, content: str) -> None:
        """Create file with content. Skip if exists (idempotent).

        Args:
            path: File path to create
            content: Content to write to file
        """
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def file_exists(self, path: Path) -> bool:
        """Check if file exists.

        Args:
            path: File path to check

        Returns:
            True if file exists, False otherwise
        """
        return path.exists() and path.is_file()

    def read_json(self, path: Path) -> Dict:
        """Read JSON file. Attempt repair if corrupted.

        Args:
            path: JSON file path to read

        Returns:
            Dictionary containing parsed JSON data

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is corrupted and cannot be repaired
        """
        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")
            result: Dict = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            # Attempt repair by returning empty dict (caller should handle defaults)
            # This allows corrupted files to be recreated
            raise json.JSONDecodeError(
                f"Corrupted JSON file: {path}. Error: {e.msg}", e.doc, e.pos
            ) from e

    def write_json(self, path: Path, data: Dict) -> None:
        """Write JSON file atomically.

        Uses a temporary file and atomic rename to ensure file integrity.

        Args:
            path: JSON file path to write
            data: Dictionary to serialize as JSON
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write using temporary file
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
        ) as tmp_file:
            json.dump(data, tmp_file, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp_file.name)

        # Atomic rename
        tmp_path.replace(path)

    def append_jsonl(self, path: Path, entry: Dict) -> None:
        """Append JSONL entry to file.

        Args:
            path: JSONL file path
            entry: Dictionary to append as a single line
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("a", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)
            f.write("\n")

    def append_markdown_log(self, path: Path, entry: str) -> None:
        """Append markdown log entry.

        Args:
            path: Markdown log file path
            entry: Markdown-formatted log entry to append
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("a", encoding="utf-8") as f:
            f.write(entry)
            if not entry.endswith("\n"):
                f.write("\n")

    def calculate_hash(self, path: Path) -> str:
        """Calculate SHA-256 hash of file content.

        Args:
            path: File path to hash

        Returns:
            SHA-256 hash as hex string (64 characters)

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Cannot calculate hash: file not found: {path}")

        sha256 = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    def copy_template(self, template_name: str, destination: Path) -> None:
        """Copy a template file from templates directory to destination.

        Args:
            template_name: Name of the template file (e.g., "VISION.md")
            destination: Destination path where template will be copied

        Raises:
            FileNotFoundError: If template file doesn't exist
            OSError: If file cannot be copied
        """
        try:
            # Use importlib.resources to access package templates
            templates_package = importlib.resources.files("lily.templates")
            template_path = templates_package / template_name

            if not template_path.is_file():
                raise FileNotFoundError(f"Template not found: {template_name}")

            # Read template content
            template_content = template_path.read_text(encoding="utf-8")

            # Write to destination (create parent directories if needed)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(template_content, encoding="utf-8")
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                raise
            raise OSError(f"Failed to copy template {template_name}: {e}") from e

    def check_permissions(self, path: Path) -> bool:
        """Check if path is writable.

        Args:
            path: Path to check (file or directory)

        Returns:
            True if path is writable, False otherwise
        """
        if path.exists():
            return os.access(path, os.W_OK)
        else:
            # Check if parent directory is writable
            parent = path.parent
            if parent.exists():
                return os.access(parent, os.W_OK)
            # Recursively check parent directories
            while parent != parent.parent:
                if parent.exists():
                    return os.access(parent, os.W_OK)
                parent = parent.parent
            return False


class Logger:
    """Handles dual-format logging (JSONL and Markdown) for Lily commands."""

    def __init__(self, storage: Storage, log_jsonl_path: Path, log_md_path: Path):
        """Initialize logger with storage and log file paths.

        Args:
            storage: Storage instance for file operations
            log_jsonl_path: Path to JSONL log file (.lily/log.jsonl)
            log_md_path: Path to Markdown log file (.lily/log.md)
        """
        self.storage = storage
        self.log_jsonl_path = log_jsonl_path
        self.log_md_path = log_md_path

    def log_init(
        self,
        action: str,
        files: List[str],
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """Log init command execution to both log.md and log.jsonl.

        Writes the same information to both formats synchronously.

        Args:
            action: Action type ("created", "skipped", "repaired", "failed")
            files: List of file paths affected
            metadata: Optional metadata dictionary (project_name, phase, etc.)
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        entry = LogEntryModel(
            timestamp=now,
            command="init",
            action=LogAction(action),
            files=files,
            metadata=metadata,
        )

        # Write to JSONL format
        jsonl_entry = entry.model_dump(mode="json")
        # Pydantic v2 converts datetime to ISO string automatically in mode="json"
        self.storage.append_jsonl(self.log_jsonl_path, jsonl_entry)

        # Write to Markdown format
        md_entry = self._format_markdown_entry(entry, now)
        self.storage.append_markdown_log(self.log_md_path, md_entry)

    def _format_markdown_entry(self, entry: LogEntryModel, timestamp: datetime) -> str:
        """Format log entry as Markdown.

        Args:
            entry: LogEntryModel instance
            timestamp: Datetime object

        Returns:
            Markdown-formatted log entry string
        """
        # Format timestamp for display: "2026-01-14 10:30:00"
        display_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        lines = [f"[{display_time}] {entry.command}"]
        for file_path in entry.files:
            lines.append(f"- {entry.action.value}: {file_path}")

        if entry.metadata:
            metadata_lines = []
            for key, value in entry.metadata.items():
                metadata_lines.append(f"  {key}: {value}")
            if metadata_lines:
                lines.extend(metadata_lines)

        return "\n".join(lines)
