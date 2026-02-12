#!/usr/bin/env python3
"""Generate the initial Test Quality Audit markdown file.

Discovers all test files (test_*.py, *_test.py) under the tests directory,
and for each file extracts test methods (top-level test_* functions and
test_* methods on classes). Writes a skeleton markdown file with:

- Inventory of test file paths
- Per-file sections with a table of test methods (Method | Score | Notes)
- Placeholder sections for file-level scores, prioritized list, Phase B, summary.

Excludes: __init__.py, conftest.py, and directories like pack_fixtures
(support modules, not test modules).
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler

app = typer.Typer(
    name="generate-test-quality-audit",
    help="Generate Test Quality Audit skeleton (test files + method tables).",
)
console = Console()

# Rich logging: format and handler
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, show_path=False)],
)
log = logging.getLogger(__name__)


def is_test_file(path: Path, _tests_root: Path) -> bool:
    """True if path is a test module we want to audit (not fixture/conftest/init)."""
    name = path.name
    if name.startswith("_") or name == "conftest.py":
        return False
    if "pack_fixtures" in path.parts or "fixtures" in path.parts:
        return False
    return bool(name.startswith("test_") or name.endswith("_test.py"))


def collect_test_files(tests_root: Path) -> list[Path]:
    """Return sorted list of test file paths under tests_root."""
    found: list[Path] = []
    for path in tests_root.rglob("*.py"):
        if not path.is_file():
            continue
        if is_test_file(path, tests_root):
            found.append(path)
    return sorted(found, key=lambda p: p.as_posix())


def _collect_from_class(class_node: ast.ClassDef, prefix: str = "") -> list[str]:
    """Collect test_* methods from a class (and nested classes).

    Returns names like 'test_foo' or 'ClassName::test_foo'.
    """
    names: list[str] = []
    class_prefix = (
        f"{class_node.name}::" if prefix == "" else f"{prefix}{class_node.name}::"
    )
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("test_"):
                names.append(f"{class_prefix}{node.name}")
        elif isinstance(node, ast.ClassDef):
            names.extend(_collect_from_class(node, class_prefix))
    return names


def get_test_methods_from_file(file_path: Path) -> list[str]:
    """Parse Python file with ast and return names of test functions/methods.

    Matches pytest discovery:
    - Top-level functions named test_*
    - Methods named test_* in any class (including nested classes)
    - Excludes nested functions (e.g. def test_inner inside def test_outer)
      since pytest does not collect those.

    Class methods are returned as "ClassName::test_method" for the audit.
    """
    names: list[str] = []
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception:
        return ["(parse error)"]
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ["(syntax error)"]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("test_"):
                names.append(node.name)
        elif isinstance(node, ast.ClassDef):
            names.extend(_collect_from_class(node))
    return sorted(names)


def path_relative_to(path: Path, root: Path) -> str:
    """Path as posix string relative to root."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def generate_audit_md(
    tests_root: Path,
    output_path: Path,
    repo_root: Path | None = None,
) -> None:
    """Write the audit skeleton markdown to output_path."""
    repo = repo_root or output_path.parent
    test_files = collect_test_files(tests_root)
    lines: list[str] = [
        "# Test Quality Audit",
        "",
        "Generated skeleton for `/test-quality`. Fill in sections as you audit.",
        "",
        "---",
        "",
        "## 1. Inventory (test files)",
        "",
        "Every test file in the suite. No fixtures or support modules.",
        "",
    ]
    for i, p in enumerate(test_files, start=1):
        rel = path_relative_to(p, repo)
        lines.append(f"{i}. `{rel}`")
    lines.extend(
        [
            "",
            "---",
            "",
            "## 2. Per-file method tables (rank methods here)",
            "",
            "Rank or score test methods per file. Fill in **Score** and **Notes**.",
            "",
        ]
    )
    for file_path in test_files:
        rel = path_relative_to(file_path, repo)
        methods = get_test_methods_from_file(file_path)
        log.debug("Parsed %s: %d test methods", rel, len(methods))
        lines.append(f"### `{rel}`")
        lines.append("")
        lines.append("| Method | Score (0-3) | Notes |")
        lines.append("|--------|-------------|-------|")
        lines.extend([f"| `{m}` | | |" for m in methods])
        lines.append("")
    lines.extend(
        [
            "---",
            "",
            "## 3. File-level scores (rubric)",
            "",
            "After scoring each file, add the table (path + dimensions + average).",
            "",
            "*Placeholder: fill in after Step 2.*",
            "",
            "---",
            "",
            "## 4. Prioritized refactor list",
            "",
            "Ordered list of files to refactor (average <2.0 first).",
            "",
            "*Placeholder: fill in after Phase A.*",
            "",
            "---",
            "",
            "## 5. Phase B progress",
            "",
            "After each refactor, append a line: `Refactored: path`",
            "",
            "*Placeholder: append during Phase B.*",
            "",
            "---",
            "",
            "## 6. Final summary",
            "",
            "*Placeholder: fill in after Phase C.*",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


@app.command()
def main(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output markdown file path."),
    ] = Path("test_quality_audit.md"),
    tests_dir: Annotated[
        Path,
        typer.Option("--tests-dir", help="Root directory containing test files."),
    ] = Path("tests"),
    repo_root: Annotated[
        Path | None,
        typer.Option(
            "--repo-root",
            help="Repo root for relative paths (default: parent of output).",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging."),
    ] = False,
) -> None:
    """Generate Test Quality Audit (inventory + method tables + placeholders)."""
    if verbose:
        log.setLevel(logging.DEBUG)
    resolved_output = output.resolve()
    repo = repo_root.resolve() if repo_root else resolved_output.parent
    tests_root = tests_dir.resolve() if tests_dir.is_absolute() else repo / tests_dir
    if not tests_root.is_dir():
        log.error("Tests directory not found: %s", tests_root)
        raise typer.Exit(1)
    log.info("Discovering test files under %s", tests_root)
    test_files = collect_test_files(tests_root)
    log.info("Found %d test files", len(test_files))
    generate_audit_md(tests_root, resolved_output, repo)
    n = len(test_files)
    out = f"[green]Wrote[/green] [bold]{resolved_output}[/bold]"
    console.print(f"{out} [dim]({n} files)[/dim]")


if __name__ == "__main__":
    app()
