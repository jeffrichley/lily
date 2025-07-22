# 📘 Story: Skill Registry

## 🧭 Overview
Index skills from local, module, and global locations with override logic.

## ✅ Requirements
- [ ] Support for `skill_registry` via CLI or flow engine
- [ ] Proper error handling and validation for `skill_registry`
- [ ] Persona-aware execution in `skill_registry`

## 🛠 Development Checklist
- [ ] Create `skill_registry.py`
- [ ] Implement `skill_registry_runner()`
- [ ] Write tests for `test_skill_registry()`
- [ ] Validate with a real skill/flow
- [ ] Confirm with different personas
- [ ] Save `result.md` correctly
- [ ] Log task status to `FEATURES_LIST.md` or `tasks.db`

## 🧪 Acceptance Criteria
- [ ] Can be run via CLI (`lily run ...`)
- [ ] Produces valid output in `.lily/threads/<task>/result.md`
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
