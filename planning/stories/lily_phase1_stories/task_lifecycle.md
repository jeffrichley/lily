# 📘 Story: Task Lifecycle

## 🧭 Overview
Track tasks through todo → in_progress → complete → needs_rework stages.

## ✅ Requirements
- [ ] Support for `task_lifecycle` via CLI or flow engine
- [ ] Proper error handling and validation for `task_lifecycle`
- [ ] Persona-aware execution in `task_lifecycle`

## 🛠 Development Checklist
- [ ] Create `task_lifecycle.py`
- [ ] Implement `task_lifecycle_runner()`
- [ ] Write tests for `test_task_lifecycle()`
- [ ] Validate with a real skill/flow
- [ ] Confirm with different personas
- [ ] Save `result.md` correctly
- [ ] Log task status to `FEATURES_LIST.md` or `tasks.db`

## 🧪 Acceptance Criteria
- [ ] Can be run via CLI (`lily run ...`)
- [ ] Produces valid output in `.lily/prthreadsp/<task>/result.md`
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
