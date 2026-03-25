---
owner: "@team"
last_updated: "2026-03-25"
status: "reference"
source_of_truth: false
---

## Alignment bullets (your points)

1. **“Skills are a special directory structure … by industry leaders.”**  
   Mostly yes. The Claude guide’s baseline structure is: a folder for the skill containing **`SKILL.md` (required)** plus optional `scripts/`, `references/`, `assets/`. It does *not* require `playbooks/` / `procedures/` / `agents/` subdirectories.  
   Pushback: your Lily spec currently uses those subdirectories as an *internal* way to map to execution adapters (playbook/procedural/agent), but the public/industry standard is simpler. We can keep the internal adapter mapping without requiring authors to follow it.

2. **“We will use `python-frontmatter` to parse md files yaml frontmatter.”**  
   That library exists and is explicitly about parsing frontmatter ([PyPI: python-frontmatter](https://pypi.org/project/python-frontmatter/)). However, in *this repo’s existing runtime config loading*, the code currently uses `yaml.safe_load` directly (`src/lily/runtime/config_loader.py` and `src/lily/runtime/tool_catalog.py`).  
   Pushback: you can still use `python-frontmatter`, but you must ensure the same security posture as the skills spec (safe YAML parsing, strict schema validation, and the “forbidden `<`/`>` in frontmatter values” rules).

3. **“There are a few minimum frontmatter required.”**  
   Yes: the Claude guide’s minimal required format is **`name`** and **`description`** only. Your skills spec aligns with that (only those two are required; everything else is optional).

4. **“Inject available skills + how to use them into the system prompt; do it via LangChain middleware.”**  
   The Claude guide explicitly describes the **three-level progressive disclosure**, where **the first level (YAML frontmatter) is always loaded in Claude’s system prompt**. So the *concept* matches.  
   Pushback on “LangChain middleware”: LangChain’s middleware is mainly for things like routing/call limiting; prompt shaping is typically done by how you construct messages / the `system_prompt` you pass into the chain. Practically, Lily’s “skill injection” should happen at the *supervisor prompt construction step* (based on enabled skills +/or selected skills), not be something you hope middleware will “magically” do.

5. **“Give the agent the correct tools; also use middleware; don’t rely on the model reading FS.”**  
   This is aligned with the Lily boundary language: skills should operate *inside* the existing `tools.*` catalog + `agent.*` allowlist/policy gates. Your spec even calls out tool-access resolution as an **intersection with runtime-available tools** (skills may restrict, but not expand beyond the runtime boundary).  
   Pushback: you probably don’t want “middleware for tool access” in the sense of “let the model request arbitrary file reads.” Instead, the system should bind a controlled tool set to the agent run, and skills should be executed by wrappers/adapters that only can call those allowed tools.

6. **“Agent will need to read files due to progressive disclosure.”**  
   This is the main place I want to push back. In the Claude model, progressive disclosure means *the platform* loads levels as needed. In Lily, your **progressive disclosure loader** is the component that should read `SKILL.md` and hydrate additional content at the right time (summary/index vs full body vs linked assets).  
   Meaning: the agent shouldn’t need broad filesystem read for progressive disclosure; Lily’s loader can do the reading deterministically before/while assembling the next prompt context. File reading should still exist as a tool *if* skills/scripts need it, but it should remain policy-gated.

7. **“Don’t require playbooks/procedural/agent placement; allow ‘just a skill’.”**  
   This aligns with the Claude guide: it treats a skill as a folder with `SKILL.md` + optional components—there’s no “playbook/procedural/agent” taxonomy for authors.  
   Pushback on current spec naming: Lily can still keep internal execution modes, but it should not force authors to choose a subdirectory. A clean reconciliation is: **determine skill execution mode from what the package contains** (e.g., if there’s no procedural/agent adapter content, treat it as “instruction-only/playbook-like”).

---

## Questions (your points)

1. **“What does ‘integrate with tool registry boundary (`tools.*` + `agent.*`)’ mean?”**  
   Concretely: Lily already has (a) a tool catalog that defines what tools exist (`tools.*`) and (b) an allowlist that defines what the agent run is permitted to call (`agent.* tools.allowlist`).  
   The skills layer must not “bypass” that. The skills spec’s normative tool resolution says: compute tools available to the runtime, then intersect with any skill-level allowed-tools constraints—so skills cannot grant access beyond what the runtime policy allows (`.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md`, “Tool access resolution (normative)” and policy boundary language).

2. **“Is `skills/playbooks/literature_review/SKILL.md` the correct directory structure? Can we scan down until we find `SKILL.md`?”**  
   That specific path is Lily’s *illustrative* internal structure from the PRD. The Claude guide’s “canonical” structure is simply `your-skill-name/SKILL.md` (no intermediary `playbooks/` / `procedures/` / `agents/`).  
   Yes, scanning for `SKILL.md` under the configured skill root is a reasonable feature, and it would make Lily accept industry-standard skill layout. The key is to keep discovery deterministic (stable sorting), and keep the skill identity anchored in `name` frontmatter (not just “directory depth”).

3. **“Explicit invocation syntax: does the Claude guide support something like that?”**  
   The guide clearly supports explicit “use this skill” in natural language. For example, it gives: **`Use the skill-creator skill to help me build a skill for [your use case]`**.  
   It does *not* prescribe `$skill:<id>` markup (that’s Lily-specific). So industry-aligned options for Lily are:
   - Support `$skill:<id>` for deterministic operator control (Lily internal).
   - Also support a natural-language form like “Use the `<name>` skill” mapped into the same explicit routing logic.
   Implicit/automatic triggering remains the description-driven mechanism (also standard in the guide).

4. **“Repository target surfaces (MVP) section looks wrong—skills shouldn’t ‘have anything about agents’.”**  
   Your read is partly right: the current “Repository target surfaces” snippet lists `.lily/skills/agents/<skill_id>.py`, but that’s describing an *internal adapter implementation location* for “agent skills” mode. It does not mean “skills don’t live under the skills directory.”  
   Still, you’re justified in wanting the docs clarified: authors should see “skills are `SKILL.md` packages,” while the internal adapter code layout should be framed as an implementation detail.

5. **“Why not just have the LLM request it by name? What’s the point of invocation keywords?”**  
   The main reason in your spec is deterministic + auditable routing:  
   - If the LLM decides “which skill to use” based on its own reasoning, it becomes harder to guarantee reproducible behavior and make governance/policy enforcement transparent.  
   - Explicit invocation (`$skill:<id>`) is a hard override parsed by Lily (deterministic).  
   - Implicit invocation is handled by deterministic selection/ranking logic based on skill metadata/description triggers (also inspectable).  
   In other words: invocation keywords are a control plane, not a “let the LLM improvise” mechanism.

6. **“Why do we need a progressive disclosure loader? Couldn’t Phase A/B just read files via a tool?”**  
   Yes, the “read files when needed” idea is exactly what progressive disclosure does—but the loader is still the system component that ensures:
   - only the **summary/index** is loaded during indexing,
   - only the **full `SKILL.md`** is hydrated after selection,
   - optional linked assets are loaded only when needed,
   - caching + bounded hydration + deterministic error taxonomy are in place.  
   It’s not “extra complication”; it’s the mechanism that makes the progressive disclosure strategy reliable and token-bounded (and aligns with the Claude guide’s 3-level model).

7. **“Does LangChain have built-in capabilities to handle skills?”**  
   Not as a first-class “skills packaging + discovery + progressive disclosure + deterministic routing” concept. LangChain gives you:
   - tools,
   - agent prompting/tool-calling,
   - routing patterns (multi-agent/deep agents), etc.  
   But Lily’s “SKILL.md contract + discovery + summary-vs-body hydration + policy gates + explicit invocation control plane” is application-specific logic you’d build.

8. **“Most CLI tools use `$<skill-name>`, not `$skill:<skill-name>`—should we change?”**  
   You can support that ergonomically. Your spec currently uses `$skill:<id>` mostly for unambiguous parsing and consistency with the “explicit invocation has highest precedence” contract.  
   Practical compromise: support **both** syntaxes and normalize them internally to the same explicit routing path, keeping determinism intact.

---

If you want to make this perfectly consistent, the biggest doc/spec alignment I’d suggest is: treat the Claude-standard “skill folder + `SKILL.md`” as the author-facing canonical layout, and treat `playbooks/procedures/agents` as Lily-only internal adapter locations (optional, inferred, not required).