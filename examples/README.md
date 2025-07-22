# Lily Examples

This directory contains examples demonstrating Lily's functionality.

## Basic Resolver Example

**File**: `basic_resolver_example.py`

This example demonstrates the core skill resolution functionality we've implemented:

### What it shows:
- ✅ **Project Context Creation** - Setting up persona, modules, and skill overrides
- ✅ **Skill Resolution** - Finding skills in local, module, and global locations
- ✅ **Skill Validation** - Validating skill files have proper front matter
- ✅ **Strategy Pattern** - Using different resolution strategies
- ✅ **Error Handling** - Proper exception handling for missing/invalid skills

### How to run:
```bash
# From the project root
uv run python examples/basic_resolver_example.py

# Or if you're in the examples directory
cd examples
uv run python basic_resolver_example.py
```

### What it creates:
- `.lily/skills/DEMO-summarize-text.md` - A local skill file (demo)
- `.lily/modules/chrona/skills/DEMO-transcribe.md` - A module skill file (demo)

### Expected output:
```
🌸 Lily Basic Resolver Example
==================================================
✅ Created sample skill files:
   - .lily/skills/DEMO-summarize-text.md
   - .lily/modules/chrona/skills/DEMO-transcribe.md

🔍 Demonstrating Skill Resolver
==================================================
📁 Project root: /path/to/lily
🧠 Persona: life
📦 Modules: ['chrona']
🔄 Skill overrides: {'summarize': 'chrona.transcribe'}

🔧 Resolver created with 3 strategies
✅ Found local skill: .lily/skills/DEMO-summarize-text.md
✅ Found module skill: .lily/modules/chrona/skills/DEMO-transcribe.md
✅ Found override skill: .lily/modules/chrona/skills/DEMO-transcribe.md

🔍 Demonstrating Skill Validation
==================================================
✅ Correctly caught invalid skill: Skill file .lily/skills/invalid-skill.md must start with front matter (---)

✅ Example completed successfully!
```

## What's Not Yet Implemented

The following functionality is planned but not yet implemented:
- ❌ CLI commands (`lily run <skill-name>`)
- ❌ Skill execution (running skills with LLM)
- ❌ Input substitution (`{{ input }}` replacement)
- ❌ Result writing (saving to `.lily/tasks/`)
- ❌ Persona management
- ❌ Task tracking

## Note on Demo Files

All files created by examples are prefixed with `DEMO-` to clearly identify them as demonstration files. This prevents confusion with real project files and makes it easy to clean up demo files when needed.
