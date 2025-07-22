# 📘 Story: Project Context

## 🧭 Overview
Detect and merge `.lily/project.yaml` configs for context-aware behavior.

## ✅ Requirements
- [ ] Support for `project_context` via CLI or flow engine
- [ ] Proper error handling and validation for `project_context`
- [ ] Persona-aware execution in `project_context`

## 🛠 Development Checklist
- [ ] Create `project_context.py`
- [ ] Implement `project_context_runner()`
- [ ] Write tests for `test_project_context()`
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
