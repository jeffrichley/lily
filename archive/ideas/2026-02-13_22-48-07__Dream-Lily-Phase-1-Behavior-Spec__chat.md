# Chat Export

### User

we are now going through the process.md and keeping needed.md in mind.

---

### Assistant

Good. We’re exactly where we should be. Right now we are walking process.md, while holding needed.md like a guardrail so we don’t drift into OpenClaw-OS cosplay. You already have the structure laid out in process.mdprocess . You already clarified we are only building Lily agent mode v0 needed . And Phase 1 is explicitly: define scope, no architecture LILY_AGENT_MODE_V0 . So let’s slow this down and do this properly. 🧭 Where We Actually Are We are in: Phase 1 — Behavior Spec(process-first, not architecture-first) From process.md, Phase 1 output is: lily_agent_mode_behaviors.md Not features. Not plugins. Not gateway. Not 52 skills. Observable runtime behaviors. 🎯 What needed.md Is Protecting Us From needed.md makes something very clear needed : We are NOT building: Gateway Channels Nodes Plugin ecosystem Marketplace OAuth Browser automation platform We are building: Lily agent mode as a local, skill-driven operator. If a behavior doesn’t directly support: skill loading skill selection deterministic override persona preservation safe execution …it does not belong in v0. 🪓 So What Do We Do Right Now? We write the behavior spec. Not a feature list. Not a comparison to OpenClaw. Not architecture. We define runtime truths. 📄 What lily_agent_mode_behaviors.md Must Contain It should answer only this: 1️⃣ Skill Loading Behavior Lily loads skills from: bundled directory workspace directory user directory (optional in v0?) Deterministic precedence: workspace overrides user overrides bundled Skills are snapshotted per session Skill eligibility filtering exists (basic: OS/env check) No hot reloading logic yet. No watchers. No plugin packs. 2️⃣ Skill Selection Behavior Lily supports two invocation modes: A. Conversational Mode LLM chooses skill Must select at most one skill Must read SKILL.md before execution Skill selection is probabilistic B. Deterministic Mode /skill <name> forces that skill Optional: command-dispatch: tool bypasses LLM reasoning Deterministic always wins over conversational That’s it. 3️⃣ Session Behavior From SESSION_MODEL_V0.mdSESSION_MODEL_V0 : Session tracks: active agent skill snapshot version active model config conversation state No multi-channel routing. No distributed session store. No remote execution. Local only. 4️⃣ Persona Behavior Lily loads: SOUL.mdIDENTITY.mdUSER.mdAGENTS.mdThese: Inject into system context Are human-editable Persist across sessions No dynamic evolution engine. No memory indexing engine in v0. Just file-backed persona. 5️⃣ Tool Policy Behavior Minimal: Skills can hint required tools Deterministic commands may require owner-only mode A basic allow/deny tool filter exists No sandbox yet. No container isolation yet. No security scanner yet. 🚫 What Explicitly Does NOT Exist in v0 This is critical. The behavior spec must explicitly say: No plugin system No multi-channel routing No distributed nodes No marketplace No skill registry server No memory embedding search No cron No background jobs No typed execution graph yet If it’s not required to prove skill-driven agent mode, it’s out. 🧠 The Hidden Strategic Goal We are proving this minimal equation: pgsql persona files
+ deterministic skill system
+ sessionsnapshot
+ dual invocation mode
= stable agent operatorIf that works, everything else becomes modular later. ⚡ So Here’s My Question For You Do you want me to: Draft lily_agent_mode_behaviors.md in final form (tight, 1–2 pages), Or outline it in bullet skeleton form so you refine it? Given how you work, I’d recommend I draft it cleanly and you redline it. This is the foundation layer. We get this right, and the rest of Lily stops being fuzzy.

---

### User

sure, lets do it. i just need to know which files to put what in to keep it organized

---

### Assistant

Perfect — here’s the clean “what goes where” layout so we don’t end up with a junk-drawer repo. Folder + file map for this phase (Agent Mode v0) docs/specs/agent_mode_v0/ (the canonical specs) Put the contracts here — short, stable, versioned. LILY_AGENT_MODE_V0.mdScope + boundaries (what Lily is / is not in v0). This is your 1-page “constitution.” LILY_AGENT_MODE_V0 lily_agent_mode_behaviors.mdObservable behaviors only (load, select, dispatch, session persistence, persona bootstrap, tool policy). No architecture. This is what we’re drafting now. process SKILL_SPEC_V0.mdSkill contract: frontmatter, metadata, invocation modes, command mapping, permission hints. SKILL_SPEC_V0 SESSION_MODEL_V0.mdSession model: fields Lily persists + what it never persists in v0. SESSION_MODEL_V0 docs/process/ (how we work) process.mdThe step-by-step process you’re following (what file each phase produces). Keep it here and don’t mix it with specs. process needed.mdThe guardrails / “nope list” for this phase (prevents scope creep). needed skills/ (actual first-party skills) This folder should be the same shape as “user skills,” so first-party skills prove the mechanism. Example: skills/plan_compiler/SKILL.mdskills/repo_maintainer/SKILL.mdskills/research_assistant/SKILL.md(We’ll keep it to 3–5 skills in v0 per the process. needed ) persona/ (editable persona bootstrap files) These are not “docs.” They are runtime inputs. persona/SOUL.mdpersona/IDENTITY.mdpersona/USER.mdpersona/AGENTS.mdtests/manual/ (smoke tests + golden transcripts) tests/manual/agent_mode_smoke_tests.mdtests/manual/golden_transcripts/…This is how we verify “deterministic override works” and “precedence is stable” without building a full harness yet. process Where we write the behavior spec we’re about to draft Put it here: docs/specs/agent_mode_v0/lily_agent_mode_behaviors.mdprocess That keeps all v0 agent-mode contracts together and makes it obvious what is “source of truth.” If you want, I’ll now write the full lily_agent_mode_behaviors.md in that style (tight, minimal, enforceable) and you can drop it straight into that path.

---

### User

go for it. i'll let you know anything we should tweak

---

### Assistant

Alright. Below is the full draft for: bash docs/specs/agent_mode_v0/lily_agent_mode_behaviors.md Tight. Contract-focused. No architecture leakage. Lily Agent Mode — Observable Behaviors (V0) This document defines the runtime behaviors of Lily Agent Mode v0. This is not an architecture document. This is not an implementation guide. This is a contract describing what Lily must do at runtime. If a behavior is not defined here, it does not exist in v0.
1. Runtime Scope
Lily Agent Mode v0 is: A local, skill-driven conversational operator with deterministic override capabilities. It supports: Skill loading Skill selection Deterministic skill invocation Persona bootstrap Session tracking Minimal tool policy gating It does not support: Multi-channel routing Remote nodes Plugin marketplace Background jobs Distributed execution Embedded memory indexing Typed execution graph Workflow compiler layer
2. Skill Loading Behavior
2.1 Skill Sources At session start, Lily loads skills from the following sources: Bundled skills directory User-level skills directory (optional in v0) Workspace skills directory 2.2 Deterministic Precedence If duplicate skill names exist: sql Workspace >User> Bundled The highest-precedence version wins. This precedence must be deterministic and stable across runs. 2.3 Eligibility Filtering A skill may include optional eligibility metadata (OS, environment variables, binaries). If eligibility conditions fail: The skill is excluded from the available skills index. No partial loading. 2.4 Session Skill Snapshot At session creation: Lily builds an “available skills snapshot.” This snapshot is stored in the session. The snapshot remains stable for the duration of the session. Snapshot updates require explicit reload. This prevents mid-session skill drift.
3. Skill Selection Behavior
Lily supports two invocation modes. 3.1 Conversational Mode (LLM-driven) The model may select at most one relevant skill. If selecting a skill, it must read SKILL.md before executing. Skill selection is probabilistic. Selection must be explicitly declared before use. If no skill is relevant, Lily may answer directly. 3.2 Deterministic Mode (User-forced) The user may invoke: bash /skill <name> This behavior: Bypasses skill selection reasoning. Forces the named skill. Fails clearly if the skill does not exist. Cannot silently fallback to another skill. If a skill supports deterministic command dispatch: It may bypass prompt rewriting. It may directly invoke a mapped tool. Deterministic invocation always overrides conversational routing.
4. Session Behavior
Each session tracks: Active agent Skill snapshot version Active model configuration Conversation state Sessions are local-only. There is no: Multi-channel session routing Remote session store Distributed execution context Session behavior must be stable and replayable within the same runtime.
5. Persona Bootstrap Behavior
At runtime start, Lily loads persona files if present: SOUL.mdIDENTITY.mdUSER.mdAGENTS.mdThese files: Are injected into the system context. Are human-editable. Persist across sessions. Override default persona. If a file does not exist, it is ignored. There is no dynamic persona mutation engine in v0.
6. Tool Policy Behavior
Lily supports minimal tool gating. Skills may declare required tools. Tool access may be filtered. Deterministic commands may require owner-only execution. There is no sandbox engine in v0. There is no plugin trust tier system in v0. Tool policy behavior must be explicit and inspectable.
7. Command Surface (V0)
Lily must support: /skills — list available skills /skill <name> — force skill usage /help <skill> — show skill summary /agent <name> — switch active agent (if supported) /reload_skills — rebuild skill snapshot All command behavior must be deterministic. Commands must not rely on probabilistic routing.
8. Stability Rules
Lily Agent Mode v0 must guarantee: Deterministic skill precedence Stable session snapshot Deterministic command dispatch Explicit failure when ambiguity exists No silent fallback behavior If the system cannot deterministically resolve an action, it must fail clearly.
9. Out of Scope (Explicitly Not Included)
The following are not part of v0: Plugin registry Skill marketplace Multi-agent orchestration Agent-to-agent messaging Background execution lanes Typed execution graph Workflow compiler Memory vector search External provider rotation logic Cron scheduler Webhook engine Container sandboxing Enterprise governance layer These may exist in future versions, but they do not exist in v0.
10. Definition of Done (V0)
Lily Agent Mode v0 is complete when: Skills load deterministically from multiple directories. Skill precedence behaves exactly as specified. Conversational and deterministic invocation modes both work. Persona files inject correctly. Session snapshot prevents drift. Command surface behaves predictably. Three first-party skills execute successfully. Manual smoke tests pass. If any of these behaviors are unstable, v0 is not complete. There you go. Now tell me: Too strict? Not strict enough? Do you want to tighten failure semantics even more? Should we explicitly forbid multi-skill chaining in v0? Let’s sharpen it until it feels like a compiler contract, not a vibe.

---

### User

I think this is great. What’s next

---

### Assistant

Next is Phase 2: lock the Skill Contract — because the behavior spec only tells us what Lily must do, but not what a skill is or how Lily can safely reason about skills. process needed What we create next 1) docs/specs/agent_mode_v0/SKILL_SPEC_V0.mdThis is the v0 schema + rules for a skill. Keep it tiny and execution-relevant. SKILL_SPEC_V0 It must define (v0): Directory shape (minimum required files) Frontmatter keys (required vs optional) Invocation modesprompt-rewrite (default) deterministic tool dispatch (optional) Command mappingEligibility gates (OS/env/bin) Permission hints (what tools it expects) 2) (Optional but highly recommended) docs/specs/agent_mode_v0/skills_loader_contract.mdIf you want maximum cleanliness: split “skill file format” from “how discovery/precedence works.” But if you’d rather stay lean, we can fold loader rules into SKILL_SPEC_V0 and keep only one doc. After that (Phase 3) Then we do SESSION_MODEL_V0.md (if it isn’t already finalized) and define the session fields precisely. SESSION_MODEL_V0 Then we start proving it works (Phase 4) Create 3 first-party skills under skills/ and run manual smoke tests. needed If you’re good with that flow, I’ll draft SKILL_SPEC_V0.md next in the same “compiler contract” tone, including a copy-paste example skill frontmatter + folder layout.

---

### User

Write skills_loader_contract.md

---

### Assistant

Here you go — draft for: bash docs/specs/agent_mode_v0/skills_loader_contract.md (Aligned with process.md and scoped by needed.md.) process needed Skills Loader Contract (V0) This document specifies how Lily discovers, loads, filters, and snapshots skills in Agent Mode v0. This is a behavioral contract for the loader. It is not an implementation guide. If a loader behavior is not defined here, it does not exist in v0.
1. Definitions
SkillA skill is a directory containing at minimum SKILL.md. (Exact skill format is defined in SKILL_SPEC_V0.md.) Skill ID / NameA skill’s identity is the directory name (e.g., skills/plan_compiler/). Within a given loader run, skill IDs must be unique after precedence resolution. SourceA root directory that may contain multiple skill directories. Resolved SkillThe final selected version of a skill after: discovery, 2) precedence resolution, 3) eligibility filtering. SnapshotA stable list (index) of resolved skills stored in the session to prevent drift.
2. Skill Source Roots (V0)
Lily loads skills from a fixed ordered set of source roots. 2.1 Required Source Roots V0 requires the following sources: Bundled: SKILLS_BUNDLED_DIRFirst-party skills shipped with Lily. Workspace: SKILLS_WORKSPACE_DIRProject-local overrides and project-specific skills. 2.2 Optional Source Roots V0 may support: User: SKILLS_USER_DIRPersonal skills available across projects. If user skills are not implemented in v0, the loader must behave as if this source root is empty. 2.3 No Other Sources in V0 V0 explicitly does not include: plugin-contributed skills remote skill registries marketplace installs network-fetched skills
3. Discovery Rules
3.1 Directory Traversal For each source root, Lily scans only immediate child directories as candidate skills. A candidate directory is a skill if it contains: SKILL.md (required) No recursive nested skill discovery in v0. 3.2 Skill Name Extraction The skill name is: the directory name (basename) of the skill folder Example: /…/skills/plan_compiler/SKILL.md → skill name plan_compiler3.3 Discovery Output The loader produces a set of discovered candidates: ini Candidate = (skill_name, source_root, absolute_path)
4. Precedence Resolution
4.1 Precedence Order (V0) When two or more candidates share the same skill_name, Lily resolves the winner by precedence: sql Workspace >User> Bundled Meaning: the highest-precedence source provides the resolved skill. 4.2 Determinism Requirement Given the same filesystem state and the same configured source roots: the same resolved skill set must be produced with identical precedence winners There must be no nondeterministic ordering (e.g., OS directory listing order must not affect results). 4.3 Conflict Visibility When conflicts exist (same skill name in multiple sources): loader must record conflict metadata for debugging (non-user-facing is fine) but must still deterministically choose a winner No interactive prompting in v0.
5. Eligibility Filtering
Eligibility filtering occurs after precedence resolution (winner chosen), not before. Rationale: precedence is a deterministic contract; eligibility decides whether the resolved winner is usable. 5.1 Eligibility Inputs Eligibility conditions are read from skill metadata (per SKILL_SPEC_V0.md) and may include: OS constraints (e.g., darwin, linux, win32) required environment variables required binaries available on PATH required config keys (optional in v0; may be deferred) 5.2 Eligibility Outcomes For each resolved skill: If eligible → included If ineligible → excluded 5.3 No Fallback-to-Lower-Precedence in V0 If the highest-precedence resolved skill is ineligible, Lily must not automatically fall back to a lower-precedence version. Reason: silent fallback creates surprising behavior and breaks auditability. Instead, the skill is excluded and the system must surface an inspectable reason via diagnostics. (If we ever want fallback behavior, it becomes a vNext feature with explicit rules and strong logging.)
6. Index Construction (Available Skills)
The loader constructs an Available Skills Index from eligible resolved skills. 6.1 Required Fields (per entry) Each entry must include at minimum: skill_namesource (bundled/user/workspace) pathsummary (if available; otherwise empty) invocation_modes (if declared; otherwise default) 6.2 Stable Sort Order The index must be ordered deterministically. Recommended order: alphabetical by skill_nameNo “most relevant” ordering in the loader. Relevance is runtime/LLM territory.
7. Snapshot Semantics
7.1 When a Snapshot Is Created A skills snapshot is created: when a session is created, or when /reload_skills is executed 7.2 Snapshot Contents The snapshot stores: the Available Skills Index a snapshot_version token (monotonic integer or hash) optional diagnostic metadata (conflicts, ineligible reasons) 7.3 Snapshot Stability Guarantee Within a session: Lily uses the snapshot for all skill selection and command resolution filesystem changes do not take effect until explicit reload This prevents mid-session drift and “it worked 5 minutes ago” failures.
8. Command-Level Behaviors
8.1 /skillsLists skills from the current snapshot only Does not trigger discovery Deterministic ordering 8.2 /skill <name>Resolution rules: Match <name> exactly against snapshot skill names. If not found, fail clearly (no fuzzy match in v0). If found, return the resolved skill entry. No fallback to other names. No “did you mean” in v0 unless you want it (optional UX sugar). 8.3 /reload_skillsRe-runs discovery → precedence → eligibility → index construction Creates a new snapshot version Replaces the session’s active snapshot
9. Error Handling Contract
The loader must distinguish: Loader errors (cannot read directories, invalid permissions, corrupt metadata) Skill errors (missing SKILL.md, invalid frontmatter, etc.) Eligibility failures (requirements not met) 9.1 Loader Errors If a required source root cannot be read: loader fails (hard fail) unless explicitly configured as optional 9.2 Skill Errors If a candidate skill is malformed: exclude it record diagnostics No hard fail for a single bad skill. 9.3 Eligibility Failures Exclude the skill and record the reason.
10. Out of Scope (Explicitly Not Included)
The skills loader v0 does not include: file watchers / auto-refresh skill installation skill signing / provenance verification plugin-contributed skill sources dependency resolution between skills “fallback to lower precedence if winner is ineligible” semantic search over skills remote loading
11. Definition of Done (Loader Contract)
This contract is satisfied when: skills are discovered deterministically from defined roots precedence resolution is stable and matches: Workspace > User > Bundledeligibility filtering excludes ineligible skills without silent fallback available skills index is stable and sorted deterministically session snapshot prevents drift until explicit reload commands /skills, /skill, /reload_skills operate strictly against the snapshot If you want, next I can draft SKILL_SPEC_V0.md with: the minimal frontmatter keys needed to support this loader contract, and a single canonical example skill folder you can copy/paste.

---

### User

Write SESSION_MODEL_V0.md

---

### Assistant

Here you go — draft for: bash docs/specs/agent_mode_v0/SESSION_MODEL_V0.md This is tight, explicit, and intentionally boring in the best way. Session Model (V0) This document defines the session state model for Lily Agent Mode v0. The session model specifies: What state Lily persists What state Lily must not persist What guarantees a session provides What boundaries exist between sessions This is a behavioral contract, not an implementation guide. If state is not defined here, it does not exist in v0.
1. Purpose of a Session
A session represents: A stable conversational execution context with a fixed skill snapshot and persona configuration. Sessions exist to: Preserve conversational continuity Prevent skill drift mid-run Ensure deterministic command resolution Track active agent configuration A session is local-only in v0. There is no distributed session layer.
2. Required Session Fields
A session must track the following fields. 2.1 session_idUnique identifier for the session Stable for the lifetime of the session Format is implementation-defined. 2.2 active_agentName or identifier of the currently active agent/persona Defaults to the system default agent Changing agent via /agent <name> updates this field. 2.3 skill_snapshotThe resolved skill index at session creation or reload. This must include: snapshot_versionList of available skills Resolved source for each skill Optional diagnostic metadata This snapshot is immutable unless explicitly reloaded. 2.4 model_configThe active model configuration for this session. This may include: model name temperature reasoning/thinking level (if applicable) verbosity mode (if applicable) Model configuration must remain stable unless explicitly changed. 2.5 conversation_stateThe conversation history required for LLM context. This includes: Ordered list of prior messages Role attribution (user/system/assistant/tool) Any structured tool invocation results The session must maintain proper role ordering. No implicit reordering.
3. Optional Session Fields (V0)
These may exist but are not required: created_atlast_updated_atreload_countcommand_historylightweight debug metadata These fields must not affect runtime behavior unless explicitly defined elsewhere.
4. Snapshot Stability Guarantees
Within a session: Skill selection uses only the stored skill_snapshotCommand resolution uses only the stored skill_snapshotFilesystem changes do not affect available skills Persona file edits do not affect the session unless reloaded (implementation choice; see below)
5. Persona Loading Semantics
Persona files ( SOUL.md, IDENTITY.md, USER.md, AGENTS.md) are loaded: At session start Or at runtime start before session creation In v0, persona injection behavior must be consistent for the entire session. Recommended rule: Persona files are read at session creation and treated as fixed for that session. If you prefer dynamic reload, it must be explicit (e.g., /reload_persona), not automatic. No silent persona drift.
6. Session Lifecycle
6.1 Session Creation A session is created when: A new conversation begins Or explicitly via /new (if supported) At creation: Skills are loaded and snapshot is stored Persona files are injected Model configuration is initialized Conversation state is empty (or system bootstrapped) 6.2 Session Continuation For each new message: Conversation state is appended Model context is rebuilt using session state Skill snapshot remains unchanged 6.3 Session Reload Reload operations may include: /reload_skills/agent <name>/reload_persona (optional future command) Reload must: Explicitly update the relevant field Not mutate unrelated session fields No implicit reload behavior. 6.4 Session Termination When a session ends: Session state may be discarded Or serialized locally (implementation choice) V0 does not require persistent storage across runtime restarts.
7. Determinism Requirements
Within a session: Given the same conversation state and model configuration, and the same skill snapshot, The system must: Resolve deterministic commands identically Provide identical skill index results Avoid mid-session capability changes LLM outputs may remain probabilistic. Loader and command behavior must not.
8. Isolation Guarantees
Each session must be isolated from other sessions. A session must not: Access another session’s skill snapshot Mutate another session’s model configuration Share conversation state No global mutable session state in v0.
9. Out of Scope (Explicitly Not Included)
V0 session model does not include: Multi-channel session routing Cross-device synchronization Distributed session stores Session locking across processes Long-term vector memory indexing Background job tracking Enterprise audit trails Full replay bundles Deterministic execution logs with artifact hashing These may exist in future versions. They do not exist in v0.
10. Definition of Done (Session Model V0)
The session model is complete when: A session correctly captures: active agent skill snapshot model configuration conversation state Skill snapshot remains stable unless explicitly reloaded Persona injection remains stable within a session Deterministic commands operate strictly against session state Multiple sessions can run without state bleed If any state mutates implicitly or leaks across sessions, v0 is not satisfied. Now we’re clean: Loader contract ✔ Session model ✔ Behavior spec ✔ Next step is either: Write SKILL_SPEC_V0.md (to close the loop on format), Or define the minimal command surface contract ( commands_v0.md), Or start implementing 3 first-party skills to pressure-test all of this. Tell me which direction you want to push.

---

### User

draft SKILL_SPEC_V0.md with:
	•	the minimal frontmatter keys needed to support this loader contract,
	•	and a single canonical example skill folder you can copy/paste.

---

### Assistant

Alright. This one is important. We are going to keep this minimal, and everything in it must directly support: loader contract deterministic command dispatch eligibility filtering invocation mode Nothing else. Below is the full draft for: swift docs/specs/agent_mode_v0/SKILL_SPEC_V0.md Skill Specification (V0) This document defines the minimal skill format required for Lily Agent Mode v0. This specification exists to support: deterministic skill loading eligibility filtering deterministic command dispatch controlled LLM-driven invocation If metadata does not influence execution decisions, it does not belong in v0.
1. Skill Directory Structure
A skill is a directory with the following structure: swift <skill_name>/├──SKILL.md          (required) └── assets/           (optional, ignored by loader) Only SKILL.md is required in v0. No code files. No Python modules. No nested skills. No manifest file. The skill directory name defines the skill_name.
2. SKILL.md Structure
SKILL.md contains: Optional YAML frontmatter (bounded by ---) Markdown body (the skill instructions) Example structure: markdown --- summary: Short description of what the skill does. invocation_mode: prompt_rewrite command: plan requires_tools:
  - read
  - write
eligibility: os: [darwin, linux] env: [] binaries: [] ---

# Plan Compiler

When invoked, this skill converts conversation into a structured work plan. ... Frontmatter is optional. If absent, defaults apply.
3. Minimal Frontmatter Keys (V0)
Only the following keys are recognized in v0. Anything else must be ignored. 3.1 summary (optional) Type: string Purpose: Short human-readable description used in /skills output. If missing: summary defaults to empty string. 3.2 invocation_mode (optional) Type: string Allowed values: prompt_rewrite (default) tool_dispatchprompt_rewriteDefault behavior. Lily: Selects skill Reads SKILL.mdInjects skill instructions into model context Model executes via reasoning + tool calls tool_dispatchDeterministic mode. Requires command_tool field (see below). Lily: Bypasses skill instruction rewrite Directly invokes the specified tool Does not allow LLM to reinterpret the skill If tool_dispatch is declared but command_tool is missing: Loader must treat skill as malformed and exclude it. 3.3 command (optional) Type: string Purpose: Enables /skill shorthand invocation. If present: bash /skill <skill_name> may also be invoked via: bash /<command> Example: yaml command:planAllows: bash /plan Command names must: Match ^[a-z0-9_-]+$Not collide with built-in commands Collision behavior: Built-in commands win. Skill is excluded if collision occurs. 3.4 command_tool (required if invocation_mode: tool_dispatch) Type: string Purpose: Tool name to invoke deterministically. Example: yaml invocation_mode:tool_dispatchcommand_tool:compile_planMust match an existing registered tool. If tool does not exist: Skill is excluded at load time. No runtime fallback. 3.5 requires_tools (optional) Type: list of strings Purpose: Hint for tool policy gating. Example: yaml requires_tools:-read-write-shellBehavior: If required tools are unavailable in current tool policy, Skill is excluded from Available Skills Index. No partial capability. 3.6 eligibility (optional) Type: object Supported keys: yaml eligibility:os: [darwin, linux] env: [OPENAI_API_KEY] binaries: [git] osAllowed operating systems. If current OS not listed: Skill excluded. envList of required environment variables. If any missing: Skill excluded. binariesList of required binaries on PATH. If any missing: Skill excluded. No fallback to lower precedence skill (per loader contract).
4. Skill Body Semantics
The Markdown body of SKILL.md: Is treated as instructional content Is injected into context when skill is selected (prompt_rewrite mode) Must not contain executable code Must not reference hidden runtime APIs In v0: The body is trusted content There is no security scanning layer There is no sandbox isolation layer
5. Skill Execution Rules
5.1 Single-Skill Rule (V0) Lily may select at most one skill per request. Skill chaining is explicitly not supported in v0. 5.2 Deterministic Override If user invokes: bash /skill <name> or /command alias: Lily must use that skill Must not fall back to another skill Must fail clearly if not available 5.3 No Fuzzy Matching (V0) Skill names must match exactly. No semantic similarity search. No "did you mean". No alias expansion beyond explicit command.
6. Malformed Skill Handling
A skill must be excluded if: SKILL.md missing Invalid YAML frontmatter tool_dispatch declared without command_toolcommand_tool references nonexistent tool command collides with built-in command Eligibility conditions fail Malformed skills must not crash loader. Diagnostics must record reason.
7. Canonical Example Skill (Copy/Paste Ready)
Folder Structure objectivec skills/ └── plan_compiler/
    └── SKILL.md
skills/plan_compiler/SKILL.mdmarkdown --- summary: Convert conversation into a structured implementation plan. invocation_mode: prompt_rewrite command: plan requires_tools:
  - read
  - write
eligibility: os: [darwin, linux, win32] env: [] binaries: [] ---

# Plan Compiler

You are the Plan Compiler skill.

## Purpose

Transform the current conversation into a structured, actionable plan.

## Rules

1. Extract goals from the conversation.
2. Identify constraints.
3. Break work into ordered steps.
4. Output structured markdown with:
   - Objective
   - Constraints
   - Phases
   - Step list
5. Do not execute filesystem changes unless explicitly requested.

## Output Format

```markdown
# Plan

## Objective
...

## Constraints
...

## Phases
1. ...
2. ...

## Steps
- [ ] Step 1
- [ ] Step 2
yaml
---
# 8. Definition of Done (Skill Spec V0)This spec is satisfied when:-Loadercanparsefrontmatterdeterministically-Eligibilityfilteringworks-Commanddispatchworksdeterministically-Malformedskillsareexcludedsafely-Acanonicalexampleskillloadsandexecutes-`/skills`,`/skill`,`/plan`behaveasdefined---
We now have:-Behaviorcontract✔-Loadercontract✔-Sessionmodel✔-Skillspec✔Atthispoint,youhaveafullydefined**agent-modekernellayer**.Now the real question:Do you want to:1.Write`commands_v0.md`toclosetheloopondeterministiccommandbehavior,2.Orimmediatelycreatethe3first-partyskillsandpressuretestthisdesign,3.Orbeginimplementingtheloaderincodeagainstthesecontracts?Thisiswhereitstopsbeingtheoryandstartsbeingreal.

---

### User

define the minimal command surface contract (commands_v0.md)

---

### Assistant

Perfect. This is where we make sure Lily doesn’t become “LLM vibes with slash sugar.”

We are defining the deterministic control layer.

Below is the full draft for:

bash Copy code docs/specs/agent_mode_v0/commands_v0.md

Command Surface Contract (V0)

This document defines the minimal deterministic command surface for Lily Agent Mode v0.

Commands exist to:

Override probabilistic behavior

Control session state

Inspect skill availability

Maintain deterministic execution boundaries

If a behavior is not defined here, it does not exist in v0.

1. Design Principles

The command surface must be:

Deterministic

Explicit

Snapshot-aware

Session-scoped

Non-probabilistic

Commands must:

Never rely on LLM interpretation

Never silently fallback

Fail clearly when invalid

Operate strictly against session state

2. Command Parsing Rules
2.1 Prefix

Commands must begin with:

Copy code /

Example:

bash Copy code /skills /skill plan_compiler /plan

If a message begins with /, it is parsed as a command.

No fuzzy parsing. No LLM classification. No "maybe it's a command."

2.2 Exact Match Requirement

Command names must match exactly.

No semantic matching. No partial matching. No prefix inference.

3. Required Commands (V0)

The following commands must exist.

3.1 /skills Purpose

List available skills from the current session snapshot.

Behavior

Reads skill_snapshot

Outputs skill names

Includes optional summary (if available)

Must not trigger skill reload

Must not re-scan filesystem

Determinism

Given the same snapshot, output must be identical.

3.2 /skill <name> Purpose

Force invocation of a specific skill.

Behavior

Look up <name> in session snapshot.

If not found:

Fail clearly.

Do not fallback.

If found:

Invoke skill deterministically.

Invocation rules:

If invocation_mode: prompt_rewrite

Inject skill instructions.

If invocation_mode: tool_dispatch

Call command_tool directly.

Must not select another skill.

Must not reinterpret request.

3.3 /reload_skills Purpose

Rebuild skill snapshot.

Behavior

Re-run skill discovery

Apply precedence resolution

Apply eligibility filtering

Build new snapshot

Replace session skill_snapshot

Increment snapshot_version

Must not alter:

conversation_state

active_agent

model_config

3.4 /agent <name> Purpose

Switch active agent/persona.

Behavior

Validate <name> exists.

Update active_agent.

Rebuild system context with persona files.

Must not mutate:

skill_snapshot

conversation history

model configuration (unless agent defines override; optional future feature)

3.5 /help <skill> Purpose

Display skill summary and metadata.

Behavior

Look up skill in snapshot.

Output:

summary

invocation_mode

required tools

eligibility requirements

Must not execute the skill.

Must not read filesystem.

4. Optional Alias Commands (Skill-Defined)

If a skill declares:

yaml Copy code command: plan

Then:

bash Copy code /plan

is treated as:

bash Copy code /skill plan_compiler

Rules:

Alias must not collide with built-in commands.

Built-ins always win.

If collision occurs, skill is excluded at load time.

Alias resolution must occur before LLM involvement.

5. Command Resolution Order

When parsing input:

If input starts with /

Parse as command.

Do not pass to LLM.

If no leading /

Normal conversational flow.

LLM may select skill.

Commands always override conversational routing.

6. Error Handling Contract
6.1 Unknown Command

If command does not exist:

Return clear error.

Do not fallback to conversation.

6.2 Missing Arguments

If required argument missing:

Example:

bash Copy code /skill

Must return:

arduino Copy code Error: /skill requires a skill name.

No interpretation.

6.3 Invalid Skill Name

If /skill <name> not in snapshot:

Return explicit failure.

Do not fallback.

Do not suggest alternatives (optional future UX feature).

7. Determinism Guarantees

Commands must:

Operate strictly on session state

Not depend on LLM reasoning

Not mutate unrelated session fields

Produce identical behavior given identical session state

LLM outputs may remain probabilistic.

Command behavior must not.

8. Out of Scope (V0)

Command surface does not include:

/think

/verbose

/reset

/status

/memory

/models

/approve

/sessions

Multi-lane execution controls

Elevated privilege mode

Admin controls

Queue inspection

Policy debugging

We are not building OpenClaw OS.

We are building a minimal deterministic operator.

9. Definition of Done (Commands V0)

Command surface is complete when:

/skills lists snapshot deterministically

/skill <name> forces deterministic invocation

/reload_skills rebuilds snapshot cleanly

/agent <name> switches persona deterministically

/help <skill> inspects metadata without execution

Alias commands work when defined

No command path relies on LLM routing

If any command can silently fall back into probabilistic behavior, V0 is not satisfied.

Now we have:

Behavior spec ✔

Loader contract ✔

Skill spec ✔

Session model ✔

Command surface ✔

At this point, the design layer is complete.

Next move:

Implement loader + command parsing in code,

Or create the three first-party skills and manually simulate flows,

Or write a minimal runtime skeleton that wires all contracts together.

You’re officially past the “idea” stage.
