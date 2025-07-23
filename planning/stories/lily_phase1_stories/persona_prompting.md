# 📘 Story: Persona Prompting

## 🧭 Overview
Load and apply persona tone, tools, and memory configs to all prompt executions.

## ✅ Requirements
- [ ] Support for `persona_prompting` via CLI or flow engine
- [ ] Proper error handling and validation for `persona_prompting`
- [ ] Persona-aware execution in `persona_prompting`

## 🛠 Development Checklist
- [ ] Create `persona_prompting.py`
- [ ] Implement `persona_prompting_runner()`
- [ ] Write tests for `test_persona_prompting()`
- [ ] Validate with a real skill/flow
- [ ] Confirm with different personas
- [ ] Save `result.md` correctly
- [ ] Log task status to `FEATURES_LIST.md` or `tasks.db`

## 🧪 Acceptance Criteria
- [ ] Can be run via CLI (`lily run ...`)
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
