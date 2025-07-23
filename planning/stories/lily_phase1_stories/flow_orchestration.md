# 📘 Story: Flow Orchestration

## 🧭 Overview
Parse and run flow.yaml, chaining skill execution and passing outputs between steps.

## ✅ Requirements
- [ ] Support for `flow_orchestration` via CLI or flow engine
- [ ] Proper error handling and validation for `flow_orchestration`
- [ ] Persona-aware execution in `flow_orchestration`

## 🛠 Development Checklist
- [ ] Create `flow_orchestration.py`
- [ ] Implement `flow_orchestration_runner()`
- [ ] Write tests for `test_flow_orchestration()`
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
