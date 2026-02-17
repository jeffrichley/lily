"""Scaffold a minimal Lily tool module with optional base contract."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def main() -> None:
    """Generate one minimal tool file from stable template."""
    parser = argparse.ArgumentParser(description="Scaffold a Lily tool module.")
    parser.add_argument("name", help="tool name (for example: echo_text)")
    parser.add_argument(
        "--output-dir",
        default="src/lily/runtime/tools",
        help="target directory for generated tool module",
    )
    args = parser.parse_args()

    tool_name = args.name.strip().lower().replace("-", "_")
    class_name = "".join(part.capitalize() for part in tool_name.split("_")) + "Tool"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{tool_name}.py"
    if output_file.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {output_file}")

    content = dedent(
        f"""
        \"\"\"Scaffolded Lily tool: {tool_name}.\"\"\"

        from __future__ import annotations

        from pydantic import BaseModel, ConfigDict

        from lily.runtime.executors.tool_base import BaseToolContract
        from lily.session.models import Session


        class _Input(BaseModel):
            \"\"\"Typed input schema for {tool_name}.\"\"\"

            model_config = ConfigDict(extra=\"forbid\", frozen=True)

            payload: str


        class _Output(BaseModel):
            \"\"\"Typed output schema for {tool_name}.\"\"\"

            model_config = ConfigDict(extra=\"forbid\", frozen=True)

            display: str


        class {class_name}(BaseToolContract):
            \"\"\"Minimal {tool_name} tool implementation.\"\"\"

            name = \"{tool_name}\"
            input_schema = _Input
            output_schema = _Output

            def execute_typed(
                self,
                typed_input: BaseModel,
                *,
                session: Session,
                skill_name: str,
            ) -> dict[str, object]:
                del session
                del skill_name
                payload = _Input.model_validate(typed_input)
                return {{"display": payload.payload}}
        """
    ).strip()
    output_file.write_text(content + "\n", encoding="utf-8")
    print(f"created {output_file}")
    print()
    print("SKILL.md snippet:")
    print(
        dedent(
            f"""
            ---
            summary: {tool_name}
            invocation_mode: tool_dispatch
            command_tool_provider: builtin
            command_tool: {tool_name}
            capabilities:
              declared_tools: [builtin:{tool_name}]
            ---
            """
        ).strip()
    )


if __name__ == "__main__":
    main()
