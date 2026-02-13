# OpenClaw Analysis

## Features

### Product Scope
- Personal AI assistant platform that runs on user-controlled infrastructure (local-first Gateway + CLI + optional apps).
- Multi-surface messaging assistant with unified session routing and delivery.
- Agent runtime supports both embedded model execution and external CLI-backed providers.

### Channel + Messaging Features
- Built-in core channels in code: Telegram, WhatsApp, Discord, IRC, Google Chat, Slack, Signal, iMessage (`src/channels/registry.ts`).
- Additional channel integrations exposed via extensions and docs, including Microsoft Teams, Matrix, Zalo, Zalo Personal, BlueBubbles, Feishu, Mattermost, Twitch, Nostr, and others (`extensions/*`, `docs/channels/*`).
- Rich message actions: send, poll, reactions, edits/deletes, pins, permissions/search, thread ops, emoji/sticker actions, Discord admin actions (`src/cli/program/register.message.ts`, `src/channels/plugins/types.ts`).
- Reply-tag system for native quote/reply behavior (`[[reply_to_current]]`, `[[reply_to:<id>]]`) in agent output prompt rules (`src/agents/system-prompt.ts`).

### Agent + Session Features
- Multi-agent model: each agent can have isolated workspace, model config, identity, tool policy, and routing bindings (`src/commands/agents.config.ts`, `src/routing/resolve-route.ts`).
- Session persistence tracks model overrides, thinking/verbose/reasoning/elevated levels, send policy, queue modes, compaction counters, skills snapshot, and delivery context (`src/config/sessions/types.ts`).
- Group-aware behavior includes mention gating, activation modes, and channel-aware command handling (`src/auto-reply/reply/get-reply-directives.ts`, `src/channels/*`).
- Agent-to-agent collaboration tools are built in (`sessions_list`, `sessions_history`, `sessions_send`, `sessions_spawn`) and policy-gated (`src/agents/system-prompt.ts`, `src/agents/pi-tools.ts`).

### Tooling + Automation Features
- Tool stack includes filesystem edit/read/search, shell execution + process management, web tools, browser/canvas/nodes, cron, message actions, gateway control, image analysis, session tools (`src/agents/system-prompt.ts`, `src/agents/pi-tools.ts`).
- Channel-specific tools and capability hints are injected dynamically based on runtime channel (`src/agents/pi-embedded-runner/run/attempt.ts`, `src/agents/channel-tools.ts`).
- Node/device features (camera, screen, notify, location, canvas) are accessible via tooling and Gateway interfaces (`README.md`, `src/agents/system-prompt.ts`).

### Personality + Identity Features
- Personality is explicitly user-shapeable through workspace prompt files loaded into context each run: `SOUL.md`, `AGENTS.md`, `TOOLS.md`, `IDENTITY.md`, `USER.md`, `HEARTBEAT.md`, optional `MEMORY.md`/`memory.md` (`src/agents/workspace.ts`, `src/agents/bootstrap-files.ts`).
- If `SOUL.md` exists, prompt explicitly instructs agent to embody that persona/tone (`src/agents/system-prompt.ts`).
- Identity fields (name, emoji, vibe/theme, avatar) can come from `IDENTITY.md` and agent config; placeholders are ignored (`src/agents/identity-file.ts`, `src/commands/agents.config.ts`).

### Memory + User-Learning Features
- Semantic memory tools (`memory_search`, `memory_get`) are available when memory is enabled and instructive prompt text makes recall mandatory for prior-work/preference/todo/date questions (`src/agents/tools/memory-tool.ts`, `src/agents/system-prompt.ts`).
- Memory backend supports hybrid vector + keyword search, configurable providers (OpenAI/Gemini/Voyage/local/auto), fallback embeddings providers, and indexed file/session sources (`src/agents/memory-search.ts`, `src/memory/manager.ts`).
- Session transcript deltas can be indexed as memory source for ongoing user/context learning (`src/memory/manager.ts`).
- Citation behavior is configurable (`on`/`off`/`auto`) with `auto` defaulting to showing citations mainly for direct chats (`src/agents/tools/memory-tool.ts`).

### Skills Features
- Skills load from multiple precedence tiers: extra dirs, bundled, managed config dir, personal `.agents/skills`, project `.agents/skills`, then workspace `skills/` (`src/agents/skills/workspace.ts`).
- Skills can be filtered by OS/binary/env/config requirements and optional remote-node capabilities (`src/agents/skills/config.ts`, `src/infra/skills-remote.ts`).
- Skills are represented as prompt blocks (`<available_skills>...`) and persisted as session snapshots to keep run context stable (`src/agents/skills/workspace.ts`, `src/config/sessions/types.ts`).
- Native skill commands can be exposed in chat surfaces and support either prompt rewrite invocation or deterministic tool-dispatch via skill frontmatter (`command-dispatch: tool`, `command-tool`) (`src/auto-reply/skill-commands.ts`, `src/auto-reply/reply/get-reply-inline-actions.ts`).

### Reliability + Safety Features
- Model/provider failover and auth-profile rotation are first-class in embedded runs (`src/agents/pi-embedded-runner/run.ts`, `src/agents/model-fallback.ts`).
- Context overflow handling includes auto-compaction retries and oversized-tool-result truncation fallback (`src/agents/pi-embedded-runner/run.ts`).
- Tool policies layer by profile/provider/agent/group/sandbox/subagent and owner-only restrictions (`src/agents/pi-tools.ts`, `src/agents/tool-policy.ts`).
- Optional sandboxing with per-session workspace access controls and runtime prompt awareness (`src/agents/pi-embedded-runner/run/attempt.ts`, `src/agents/system-prompt.ts`).

## How It Works

### 1) Bootstrap and Command Entry
- `src/entry.ts` is the executable entrypoint. It normalizes env/argv, applies profile flags, and starts CLI runtime (`src/cli/run-main.ts`).
- CLI is lazily registered for subcommands to reduce startup overhead (`src/cli/program/register.subclis.ts`).
- Fast-path routes for common commands (`status`, `health`, `sessions`, etc.) bypass full command parse where possible (`src/cli/program/command-registry.ts`).

### 2) Routing to Agent + Session
- Incoming or CLI-originated requests resolve to an agent via channel/account/peer/team/guild bindings with fallback to default agent (`src/routing/resolve-route.ts`).
- Session key is derived from agent + channel context; session entry in store tracks all per-thread runtime state (`src/config/sessions/types.ts`).
- For new/refresh cases, a skills snapshot is generated and stored on session so future turns reuse the same skill context unless watcher-version changes (`src/commands/agent.ts`, `src/auto-reply/reply/session-updates.ts`).

### 3) Personality Assembly per Run
- Before each model run, bootstrap context files are loaded from workspace and injected into project context block (`src/agents/bootstrap-files.ts`).
- System prompt is dynamically built with: available tools, safety policy, memory/skills instructions, messaging behavior, runtime metadata, sandbox metadata, and injected workspace files (`src/agents/system-prompt.ts`, `src/agents/pi-embedded-runner/system-prompt.ts`).
- `SOUL.md` and `IDENTITY.md` influence persona and style; owner numbers and user timezone settings shape identity/time behavior in prompt (`src/agents/system-prompt.ts`, `src/agents/identity-file.ts`, `src/agents/system-prompt-params.ts`).

### 4) Tool Construction + Policy Filtering
- Core tools are created in `createOpenClawCodingTools`, then filtered through layered policy gates and sandbox/owner constraints (`src/agents/pi-tools.ts`).
- Extension/channel tools are merged into toolset; tool schemas are normalized for provider compatibility (notably Google/Claude quirks) (`src/agents/pi-tools.ts`, `src/agents/pi-embedded-runner/run/attempt.ts`).
- Hooks can prepend context before agent start and observe/record outcomes after run (`src/agents/pi-embedded-runner/run/attempt.ts`, `src/plugins/hook-runner-global.ts`).

### 5) Embedded Execution Loop
- `runEmbeddedPiAgent` orchestrates queues, model/auth setup, retries, compaction, and failover (`src/agents/pi-embedded-runner/run.ts`).
- `runEmbeddedAttempt` sets up session manager, loads skills env, creates system prompt override, sanitizes prior history, injects images, and streams prompt (`src/agents/pi-embedded-runner/run/attempt.ts`).
- Streaming subscriber strips reasoning leakage, deduplicates partial text, handles tool summaries/results, tracks usage, and supports block replies (`src/agents/pi-embedded-subscribe.ts`).

### 6) Personality Growth Over Time
- Personality does not "self-train" model weights; it grows through editable workspace artifacts and session state.
- Primary growth levers:
  - `SOUL.md`: persona/voice/values.
  - `IDENTITY.md`: name/emoji/vibe/avatar.
  - `AGENTS.md`/`TOOLS.md`: operating instructions.
  - `MEMORY.md` + `memory/*.md`: long-term and daily memory.
  - session-level settings (`thinking`, `verbose`, model overrides, queue behavior) persisted in session store.
- System prompt explicitly reminds model to embody `SOUL.md` when present and treat workspace files as loaded context.

### 7) How It Learns About the User
- User context is learned from:
  - explicit `USER.md` and identity/persona files in workspace,
  - direct session history persisted to transcripts,
  - indexed memory files and optional session transcript memory source,
  - owner-number mapping in prompt for authoritative-user identity.
- Runtime memory lookup path:
  - `memory_search` retrieves top relevant snippets from indexed memory/session sources,
  - `memory_get` fetches precise file line windows,
  - model is instructed to run this before answering prior-context questions.
- This is retrieval-augmented learning (state + memory files), not model finetuning.

### 8) How Skills Are Executed
- Skill discovery/loading:
  - Skill folders are merged from configured locations with deterministic precedence.
  - Eligibility filtering removes skills missing required OS/bin/env/config.
- Skill injection:
  - Skills become formatted prompt blocks (`<available_skills>`), included in system prompt.
  - Prompt mandates selecting at most one clearly relevant skill first, then reading its `SKILL.md` via `read` tool.
- Invocation modes:
  - Default: natural-language rewrite (`Use the "<skill>" skill for this request`) so model follows SKILL.md workflow.
  - Optional deterministic dispatch: skill command directly invokes a named tool with raw args when frontmatter config enables it.
- Skills are snapshotted into session entries and refreshed by watcher version bumps, keeping multi-turn consistency.

### 9) Extra Important Findings
- The platform is heavily pluginized; channels, tools, hooks, providers, gateway handlers, and commands can all be extension-contributed (`src/plugins/loader.ts`, `src/plugins/discovery.ts`).
- The system is designed to avoid duplicate user-visible replies when messaging tools already sent output (`SILENT_REPLY_TOKEN` and streaming duplicate suppression logic).
- Memory indexing and skill loading both support remote-node-aware eligibility, which matters in split host/device deployments.
- There is substantial defensive code for transcript integrity, role ordering, context overflow, timeout/rate-limit auth profile rotation, and compaction recovery.
