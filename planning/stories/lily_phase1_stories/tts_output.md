# 📘 Story: Tts Output

## 🧭 Overview
Speak results from `result.md` using configured TTS voice.

## ✅ Requirements
- [ ] Support for `tts_output` via CLI or flow engine
- [ ] Proper error handling and validation for `tts_output`
- [ ] Persona-aware execution in `tts_output`

## 🛠 Development Checklist
- [ ] Create `tts_output.py`
- [ ] Implement `tts_output_runner()`
- [ ] Write tests for `test_tts_output()`
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
