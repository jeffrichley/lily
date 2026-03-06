---
owner: "@team"
last_updated: "2026-03-06"
status: "active"
source_of_truth: true
---

# Lily Roadmap

This roadmap is the source of truth for reboot prioritization.

## User-visible Features

| User story | Priority | Status |
|---|---:|---|
| As a user, I can run Lily via CLI and a basic Textual TUI against local or remote models. | 5 | Completed |
| As a user, I can start new conversations by default and resume prior conversations by id or last-used id in CLI/TUI. | 5 | Completed |

## System Improvements (Internal Work)

| ID | Improvement | Priority | Status | Enables |
|---|---|---:|---|---|
| SI-001 | Establish reboot-ready project skeleton and validation gates. | 5 | Completed | Reliable iteration |
| SI-002 | Add runtime capability/skill registry beyond fixed in-code tool wiring. | 4 | Completed | Dynamic skill selection |
| SI-003 | Add sub-agent delegation runtime on top of supervisor kernel. | 3 | Deferred | Specialized worker routing |
| SI-004 | Add structured execution logging for future reflection/evolution loops. | 3 | Deferred | Capability evolution foundation |
| SI-006 | Add persistent conversation attach/resume surfaces across CLI/TUI and runtime threading continuity. | 5 | Completed | Cross-run conversational continuity |
