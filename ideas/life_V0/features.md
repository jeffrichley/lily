# OpenClaw Feature Catalog

This file catalogs what OpenClaw already does today, formatted as a wishlist-style checklist you can borrow for your own project.

## Product Model

- [x] Local-first personal AI assistant architecture
- [x] Single Gateway control plane (sessions, tools, channels, automations)
- [x] Multi-surface operation (CLI, chat channels, web UI, companion apps)
- [x] Personal agent workspaces with per-agent isolation
- [x] Multi-agent routing and scoped sessions

## Onboarding And Setup

- [x] Guided onboarding wizard (`openclaw onboard`)
- [x] Setup command path (`openclaw setup`)
- [x] Daemon/service install flow
- [x] Configured-first setup (model + channels + workspace)
- [x] Pairing-based first-contact security flow

## Channels And Messaging Surfaces

- [x] WhatsApp
- [x] Telegram
- [x] Discord
- [x] Slack
- [x] Google Chat
- [x] Signal
- [x] iMessage (legacy)
- [x] BlueBubbles (recommended iMessage path)
- [x] Microsoft Teams
- [x] Matrix
- [x] Feishu
- [x] IRC
- [x] LINE
- [x] Mattermost
- [x] Nextcloud Talk
- [x] Nostr
- [x] TLON
- [x] Twitch
- [x] Zalo
- [x] Zalo Personal
- [x] WebChat (browser client)

## Messaging UX Features

- [x] Direct-message policies (open/pairing allowlist modes)
- [x] Group activation controls (mention vs always)
- [x] Channel-specific routing rules
- [x] Thread/topic-aware reply routing
- [x] Typing indicators and presence signals
- [x] Streaming and chunked message delivery
- [x] Slash-like in-chat command controls (`/status`, `/new`, `/reset`, `/think`, `/verbose`, etc.)

## Agent Runtime And Intelligence

- [x] LLM-driven agent loop with tool calling
- [x] Session-aware context management
- [x] Session compaction and pruning support
- [x] Queueing and lane-based execution
- [x] Tool output handling and formatting modes
- [x] Subagent session support
- [x] Agent-to-agent messaging tools (`sessions_*` tools)
- [x] Retry/failover-aware run orchestration

## Personality And Memory Model

- [x] Workspace persona files (`SOUL.md`, `IDENTITY.md`, `USER.md`)
- [x] Project behavior file (`AGENTS.md`)
- [x] Memory files (`MEMORY.md`, `memory/*.md`)
- [x] System-prompt injection from workspace bootstrap files
- [x] Memory recall tools (`memory_search`, `memory_get`) in runtime
- [x] Personality evolution via editable markdown files

## Built-in Tooling (Agent Tools)

- [x] File editing tools (read, write, edit, apply-patch)
- [x] Shell execution tool (`exec`/bash path)
- [x] Background process management tool (`process`)
- [x] Browser automation toolchain
- [x] Canvas tool
- [x] Nodes tool (device actions)
- [x] Cron tool
- [x] Gateway interaction tool
- [x] Messaging tool
- [x] Web search + web fetch tools
- [x] Image/media helper tool
- [x] TTS tool
- [x] Session status/history/list/send/spawn tools

## Browser Automation

- [x] Managed browser integration
- [x] Page actions and observation flows
- [x] Inspect/debug command surfaces
- [x] Browser login and profile support
- [x] Cookies/storage command utilities
- [x] Chrome extension support

## Nodes And Device Capabilities

- [x] Node pairing and registration
- [x] Node invoke RPC model
- [x] Canvas node actions
- [x] Camera snap/clip flows
- [x] Screen recording flows
- [x] Location command flow
- [x] Device notifications
- [x] Talk mode features
- [x] Voice wake features
- [x] Audio/image/media understanding pipeline hooks

## Automation Features

- [x] Cron job scheduling
- [x] Webhook triggers
- [x] Poll-based automation support
- [x] Gmail Pub/Sub automation support
- [x] Hook system (`before_agent_start`, `agent_end`, etc.)
- [x] Auth monitoring automation support

## Skills Platform

- [x] Bundled first-party skills
- [x] User/workspace skills
- [x] Managed skills directory support
- [x] Plugin-contributed skills
- [x] Skill metadata/frontmatter parsing
- [x] Skill eligibility gating (os/bin/env/config)
- [x] Skill command mapping (`/skill` and generated slash commands)
- [x] Optional deterministic command-dispatch to tool mode
- [x] Skill watch/refresh and snapshot versioning
- [x] Skill install helpers and security scan warnings
- [x] ClawHub ecosystem integration
- [x] 52 bundled skills in current repo snapshot

## Plugins And Extensibility

- [x] Plugin manifest/discovery system
- [x] Plugin tool registration
- [x] Plugin CLI registration hooks
- [x] Plugin channel extensions
- [x] Plugin update/install flow
- [x] Memory-provider plugin slot architecture
- [x] 35 extension packages in current repo snapshot

## Model And Provider Features

- [x] Multi-provider model support
- [x] OAuth + API-key auth profile support
- [x] Auth profile rotation and cooldown logic
- [x] Model failover and fallback behavior
- [x] Provider/model defaults and per-agent overrides
- [x] Thinking level controls
- [x] Usage tracking integrations

### Provider Surface (docs and codebase)

- [x] Anthropic
- [x] OpenAI
- [x] OpenRouter
- [x] AWS Bedrock
- [x] Vercel AI Gateway
- [x] Gemini-related paths
- [x] GitHub Copilot
- [x] Moonshot
- [x] MiniMax
- [x] GLM
- [x] Z.AI
- [x] Qianfan
- [x] Together
- [x] Venice
- [x] Ollama
- [x] LiteLLM
- [x] Synthetic provider for testing/dev flows

## Security And Policy

- [x] Pairing and allowlist protections for inbound DMs
- [x] Tool policy allow/deny layering
- [x] Owner-only tool gating
- [x] Group-level policy resolution
- [x] Optional sandbox runtime
- [x] Docker sandbox hardening options (read-only root, caps, network controls)
- [x] Elevated tool controls and approvals surface
- [x] Session write lock protections
- [x] Security CLI (`openclaw security ...`)
- [x] Doctor command for security posture diagnostics

## Observability And Diagnostics

- [x] Gateway logs CLI
- [x] Diagnostic event streams
- [x] Agent event bus hooks
- [x] System prompt report generation
- [x] Cache trace logging with digests/fingerprints
- [x] Payload logging hooks for model interactions
- [x] Health/status/session CLI diagnostics
- [x] Queue wait instrumentation

## Web And UI Surfaces

- [x] Control UI
- [x] Dashboard
- [x] WebChat
- [x] TUI web/terminal surfaces
- [x] Gateway-served web interfaces

## Platform Support

- [x] macOS companion app and menu bar control
- [x] iOS node app flows
- [x] Android node app flows
- [x] Linux gateway hosting path
- [x] Windows support path (recommended via WSL2)
- [x] Remote gateway support (SSH/tunnels/Tailscale)

## Networking And Remote Access

- [x] Local loopback-first gateway model
- [x] Tailscale Serve/Funnel integration
- [x] Bonjour/discovery support
- [x] Remote gateway patterns and docs

## Operations And Deployment

- [x] Install/update/uninstall flows
- [x] Dev/stable/beta channel strategy
- [x] Docker install path
- [x] Nix install path
- [x] Hosted deployment guides (Fly, Hetzner, GCP, Railway, Render, Northflank, macOS VM, exe.dev)
- [x] Background daemon management
- [x] Migration and doctor tooling

## CLI Surface Areas (Top-level)

- [x] `setup`
- [x] `onboard`
- [x] `configure`
- [x] `config`
- [x] `message`
- [x] `agent`
- [x] `memory`
- [x] `status`
- [x] `health`
- [x] `sessions`
- [x] `browser`
- [x] `gateway`
- [x] `daemon`
- [x] `logs`
- [x] `system`
- [x] `models`
- [x] `approvals`
- [x] `nodes`
- [x] `node`
- [x] `devices`
- [x] `sandbox`
- [x] `cron`
- [x] `dns`
- [x] `docs`
- [x] `hooks`
- [x] `webhooks`
- [x] `pairing`
- [x] `plugins`
- [x] `channels`
- [x] `directory`
- [x] `security`
- [x] `skills`
- [x] `update`
- [x] `completion`
- [x] `acp`
- [x] `tui`

## Good Wishlist Ideas To Borrow For A New Project

- [x] Multi-channel + node/device unified control plane
- [x] Persona and memory files that are human-editable
- [x] Tool policy and sandbox layers, not just one global switch
- [x] Skill system that supports bundled + user + plugin sources
- [x] Explicit pairing allowlists for DM safety
- [x] Strong diagnostics from day one (health, traces, prompt reports)
- [x] Model failover and auth profile rotation as first-class features
- [x] Agent-to-agent tools and session orchestration primitives
- [x] Wizard-first onboarding for non-technical users
- [x] CLI + web + chat + mobile surface parity strategy
