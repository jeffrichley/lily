# 📘 Story: Skill Execution

## 🧭 Overview
Execute a single skill with front matter parsing, persona/context awareness, and output logging.

## ✅ Requirements
- [ ] Support for `skill_execution` via CLI or flow engine
- [ ] Proper error handling and validation for `skill_execution`
- [ ] Persona-aware execution in `skill_execution`

## 🛠 Development Checklist
- [ ] Create `skill_execution.py`
- [ ] Implement `skill_execution_runner()`
- [ ] Write tests for `test_skill_execution()`
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
