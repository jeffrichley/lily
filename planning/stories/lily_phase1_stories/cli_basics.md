# 📘 Story: Cli Basics

## 🧭 Overview
Enable CLI commands to run skills, flows, switch personas, and view tasks.

## ✅ Requirements
- [x] Support for `cli_basics` via CLI or flow engine ✅ **Completed 2025-07-22**
- [x] Proper error handling and validation for `cli_basics` ✅ **Completed 2025-07-22**
- [ ] Persona-aware execution in `cli_basics`

## 🛠 Development Checklist
- [x] Create `cli_basics.py` ✅ **Completed 2025-07-22** (Implemented as `src/lily/cli/main.py`)
- [x] Implement `cli_basics_runner()` ✅ **Completed 2025-07-22** (Implemented as CLI command router)
- [x] Write tests for `test_cli_basics()` ✅ **Completed 2025-07-22** (Tests in `tests/lily/cli/`)
- [ ] Validate with a real skill/flow
- [ ] Confirm with different personas
- [ ] Save `result.md` correctly
- [ ] Log task status to `FEATURES_LIST.md` or `tasks.db`

## 🧪 Acceptance Criteria
- [x] Can be run via CLI (`lily run ...`) ✅ **Completed 2025-07-22** (Implemented in `src/lily/cli/main.py`)
- [ ] Displays table of features with status emojis (📝/🔄/♻️/✅) (shows skills but no status tracking)
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
