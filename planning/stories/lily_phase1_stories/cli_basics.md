# 📘 Story: Cli Basics

## 🧭 Overview
Enable CLI commands to run skills, flows, switch personas, and view tasks.

## ✅ Requirements
- [ ] Support for `cli_basics` via CLI or flow engine
- [ ] Proper error handling and validation for `cli_basics`
- [ ] Persona-aware execution in `cli_basics`

## 🛠 Development Checklist
- [ ] Create `cli_basics.py`
- [ ] Implement `cli_basics_runner()`
- [ ] Write tests for `test_cli_basics()`
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
