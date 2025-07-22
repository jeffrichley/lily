# 📘 Story: Voice Capture

## 🧭 Overview
Use WhisperFlow to capture user voice input and transcribe to `initial.md`.

## ✅ Requirements
- [ ] Support for `voice_capture` via CLI or flow engine
- [ ] Proper error handling and validation for `voice_capture`
- [ ] Persona-aware execution in `voice_capture`

## 🛠 Development Checklist
- [ ] Create `voice_capture.py`
- [ ] Implement `voice_capture_runner()`
- [ ] Write tests for `test_voice_capture()`
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
