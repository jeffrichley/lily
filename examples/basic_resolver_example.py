#!/usr/bin/env python3
"""
Basic example demonstrating Lily's skill resolver functionality.

This example shows how to:
1. Create a project context
2. Set up skill resolution strategies
3. Resolve skills from different locations
4. Validate skill files
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import lily modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lily.core.resolver import Resolver
from lily.types.exceptions import InvalidSkillError, SkillNotFoundError
from lily.types.models import ProjectContext


def create_sample_skills():
    """Create sample skill files for demonstration."""
    # Create .lily/skills directory
    skills_dir = Path(".lily/skills")
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Create a local skill (with DEMO prefix)
    local_skill = skills_dir / "DEMO-summarize-text.md"
    local_skill.write_text(
        """---
name: summarize-text
description: Summarizes text content
personas: [life, research]
tags: [summarization, markdown]
kind: atomic
---

## System Prompt
You are a helpful assistant that summarizes text.

## Instructions
Summarize the following text clearly and concisely:

## Input
{{ input }}
"""
    )

    # Create .lily/modules/chrona/skills directory
    module_skills_dir = Path(".lily/modules/chrona/skills")
    module_skills_dir.mkdir(parents=True, exist_ok=True)

    # Create a module skill (with DEMO prefix)
    module_skill = module_skills_dir / "DEMO-transcribe.md"
    module_skill.write_text(
        """---
name: transcribe
description: Transcribes audio to text
personas: [chrona, research]
tags: [transcription, audio]
kind: atomic
---

## System Prompt
You are a transcription assistant.

## Instructions
Transcribe the following audio content:

## Input
{{ input }}
"""
    )

    print("✅ Created sample skill files:")
    print(f"   - {local_skill}")
    print(f"   - {module_skill}")


def demonstrate_resolver():
    """Demonstrate the skill resolver functionality."""
    print("\n🔍 Demonstrating Skill Resolver")
    print("=" * 50)

    # Create project context
    context = ProjectContext(
        project_root=Path.cwd(),
        persona="life",
        modules=["chrona"],
        skill_overrides={"summarize": "chrona.transcribe"},
    )

    print(f"📁 Project root: {context.project_root}")
    print(f"🧠 Persona: {context.persona}")
    print(f"📦 Modules: {context.modules}")
    print(f"🔄 Skill overrides: {context.skill_overrides}")

    # Create resolver with default registry (includes all strategies)
    resolver = Resolver()

    print("\n🔧 Resolver created with default skill registry")

    # Demonstrate skill resolution
    try:
        # Resolve local skill
        local_skill_path = resolver.resolve_skill("DEMO-summarize-text", context)
        print(f"✅ Found local skill: {local_skill_path}")

        # Resolve module skill
        module_skill_path = resolver.resolve_skill("DEMO-transcribe", context)
        print(f"✅ Found module skill: {module_skill_path}")

        # Demonstrate skill override
        override_skill_path = resolver.resolve_skill("summarize", context)
        print(f"✅ Found override skill: {override_skill_path}")

    except SkillNotFoundError as e:
        print(f"❌ Skill not found: {e}")
    except InvalidSkillError as e:
        print(f"❌ Invalid skill: {e}")


def demonstrate_validation():
    """Demonstrate skill validation."""
    print("\n🔍 Demonstrating Skill Validation")
    print("=" * 50)

    # Create an invalid skill file (with DEMO prefix)
    invalid_skill_dir = Path(".lily/skills")
    invalid_skill = invalid_skill_dir / "DEMO-invalid-skill.md"
    invalid_skill.write_text("This is not a valid skill file - no front matter!")

    context = ProjectContext(project_root=Path.cwd(), persona="life")

    resolver = Resolver()

    try:
        resolver.resolve_skill("DEMO-invalid-skill", context)
        print("❌ Should have failed validation!")
    except InvalidSkillError as e:
        print(f"✅ Correctly caught invalid skill: {e}")

    # Clean up invalid skill
    invalid_skill.unlink()


def main():
    """Run the basic resolver example."""
    print("🌸 Lily Basic Resolver Example")
    print("=" * 50)

    # Create sample skills
    create_sample_skills()

    # Demonstrate resolver functionality
    demonstrate_resolver()

    # Demonstrate validation
    demonstrate_validation()

    print("\n✅ Example completed successfully!")
    print("\n📁 Created files:")
    print("   - .lily/skills/DEMO-summarize-text.md")
    print("   - .lily/modules/chrona/skills/DEMO-transcribe.md")


if __name__ == "__main__":
    main()
