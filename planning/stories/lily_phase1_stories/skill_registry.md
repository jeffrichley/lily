# 📘 Story: Skill Registry

## 🧭 Overview
Index skills from local, module, and global locations with override logic.

## ✅ Requirements
- [x] Support for `skill_registry` via CLI or flow engine ✅ **Completed 2025-07-22**
- [x] Proper error handling and validation for `skill_registry` ✅ **Completed 2025-07-22**
- [ ] Persona-aware execution in `skill_registry`

## 🛠 Development Checklist
- [x] Create `skill_registry.py` ✅ **Completed 2025-07-22** (Implemented as `src/lily/core/registry.py`)
- [x] Implement `skill_registry_runner()` ✅ **Completed 2025-07-22** (Implemented as `SkillRegistry.discover_skills()`)
- [x] Write tests for `test_skill_registry()` ✅ **Completed 2025-07-22** (Tests in `tests/lily/core/test_resolver.py`)
- [ ] Validate with a real skill/flow
- [ ] Confirm with different personas
- [ ] Save `result.md` correctly
- [ ] Log task status to `FEATURES_LIST.md` or `tasks.db`

## 🧪 Acceptance Criteria
- [x] Can be run via CLI (`lily run ...`) ✅ **Completed 2025-07-22** (Implemented in `src/lily/cli/main.py`)
- [ ] Produces valid output in `.lily/threads/<task>/result.md` (only if tracked)
- [ ] Persona tone/voice/tool is respected
- [ ] Works from both fresh and ongoing project directories

## 🧵 Example Flow
```bash
lily run summarize --input transcript.md
```

## 📁 Output Artifacts
- `initial.md`
- `result.md`
- `logs/`
