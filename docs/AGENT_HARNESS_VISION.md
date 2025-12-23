# Agent Harness Vision: Steno + Kiwi Meta-Framework

## What I Understand You Want

You're building a **meta-framework for creating complex AI agents** where:

1. **Human-LLM interaction is fluid** via steno chord prompting (clip-kiwi, cache-kiwi)
2. **Agent architecture is standardized** via the Kiwi MCP ecosystem (Context, Script, Knowledge)
3. **Almost everything is LLM-generatable** - directives, scripts, knowledge entries, even the agents themselves

The quant-kiwi project is just ONE example of an agent built with this system. The real product is the harness itself.

---

## The Two Layers

### Layer 1: The Harness (Human → LLM Interface)

```
┌─────────────────────────────────────────────────────────────────┐
│  STENO CHORD PROMPTING                                          │
│  "Collapse repeated workflows to single chords"                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Clip-Kiwi (24 slots)          Cache-Kiwi (file search)        │
│  ├── Curated prompts           ├── Directive files             │
│  ├── Code snippets             ├── Script files                │
│  ├── Context fragments         ├── Knowledge entries           │
│  └── Reusable instructions     └── Project docs                │
│                                                                 │
│  Chord: paste context → paste instruction → execute             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  KIWI MCP ECOSYSTEM                                             │
│  "The structured substrate for agent building"                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Context Kiwi (HOW)     Script Kiwi (DO)     Knowledge (KNOW)   │
│  ├── Directives         ├── Executable .py   ├── Domain facts   │
│  ├── Workflows          ├── Versioned        ├── Learnings      │
│  ├── Preflight          ├── Cost-tracked     ├── Patterns       │
│  └── Orchestration      └── Lib architecture └── Failures       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 2: The Agents (Built WITH the Harness)

Agents like quant-kiwi are **outputs** of the harness, not the harness itself.

Each agent is:
- A `.ai/` folder structure with directives, scripts, knowledge
- Domain-specific workflows (extract_strategy_from_video.md)
- Domain-specific execution (backtest_engine.py)
- Domain-specific memory (when-backtests-smell-wrong.md)

---

## The Core Insight

**Your working memory becomes externalized into:**

| Component | Contains | Access Method |
|-----------|----------|---------------|
| Clip-Kiwi slots | Curated prompts, context, snippets | Steno chord → instant paste |
| Cache-Kiwi | Live file search across projects | Steno chord → dmenu → content |
| Context Kiwi | Reusable workflows | `search()` → `run()` |
| Script Kiwi | Executable operations | `search()` → `load()` → `run()` |
| Knowledge Kiwi | Domain expertise, learnings | `search()` → `get()` |

**The workflow collapses to:**
```
Chord (context) → Chord (instruction) → LLM executes via Kiwi tools
```

---

## Building Agents with the Harness

### The Meta-Pattern

To create a new agent (like quant-kiwi):

1. **Bootstrap** - `run("init")` creates .ai/ structure
2. **Define workflows** - Create directives for domain-specific processes
3. **Implement execution** - Write scripts for actual operations
4. **Accumulate knowledge** - Store learnings, failures, patterns
5. **Iterate** - Anneal directives when they fail, scripts when they break

### What Gets LLM-Generated

| Artifact | How It's Generated |
|----------|-------------------|
| Directives | `run("create_directive")` with domain description |
| Scripts | LLM writes .py with SCRIPT_METADATA interface |
| Knowledge entries | `knowledge_kiwi.manage(create, ...)` after learnings |
| Project structure | Directives define folder layout |
| Even the agent's behavior | Directives orchestrate script+knowledge |

### The Virtuous Loop

```
Human provides high-level intent
        │
        ▼
LLM searches for existing directives/scripts/knowledge
        │
        ├── Found? Execute and extend
        └── Not found? Generate new ones
        │
        ▼
Execution produces results + learnings
        │
        ▼
Learnings stored in Knowledge Kiwi
        │
        ▼
Next iteration is smarter
```

---

## Quant-Kiwi as Example

The quant trading agent demonstrates the pattern:

**Directives** (Context Kiwi):
- `extract_strategy_from_video.md` - Learn from YouTube
- `identify_missing_components.md` - Fill implementation gaps
- `run_generation.md` - Evolutionary portfolio cycle

**Scripts** (Script Kiwi):
- `transcribe_video.py` - Extract content
- `backtest_engine.py` - Test strategies
- `evolutionary_portfolio.py` - Core EA engine

**Knowledge** (Knowledge Kiwi):
- `when-backtests-smell-wrong.md` - Tacit expertise
- `strategy-graveyard.md` - What failed and why
- `broker-api-quirks.md` - Production learnings

The THREE-LAYER ARCHITECTURE (Strategic → Tactical → Execution) maps directly onto:
- Strategic = Claude + full Kiwi stack (slow, thoughtful)
- Tactical = Fast models + Script Kiwi (quick decisions)
- Execution = Deterministic code + pre-loaded knowledge (milliseconds)

---

## The Steno Integration

Steno chords make the BUILD process fast:

```
# Building an agent directive
AGTS        → Find similar directive (cache-kiwi)
R-LTS       → Paste directive template (clip-kiwi slot 1)
W-LTS       → Paste domain context (clip-kiwi slot 2)
[LLM fills in the directive based on context]

# Running agent workflows
KW*EUP/LEAD → Context Kiwi run("lead_generation_workflow")
AGTS        → Find relevant knowledge entry
K-LTS       → Paste parameters from saved slot
[LLM executes via Script Kiwi]
```

The slots become **curated building blocks**:
- Slot 1: Current directive template
- Slot 2: Current project context
- Slot 3: Common script parameters
- Slot 4: Error patterns to check
- etc.

---

## What This Enables

### For Agent Builders (You)

- Rapid prototyping of new agents
- Reusable patterns across domains
- Accumulated expertise that compounds
- Fluid interaction via steno

### For the Agents Themselves

- Structured architecture that scales
- Self-improvement through knowledge accumulation
- Portability (just copy .ai/ folder)
- Version control friendly

### The End State

A system where:
1. You describe a domain ("quant trading", "customer support", "code review")
2. LLM generates the agent architecture using kiwi_ecosystem directive as reference
3. You refine via steno-fast iterations
4. Agent accumulates domain expertise over time
5. Repeat for any domain

---

## Resolved Gaps (2025-12-22)

1. ✅ **Init directive created .cursor** - Found culprit: `kiwi_dev_bootstrap.md` and `init_ai_config.md` were creating .cursor files. Both DELETED from registry and userspace.

2. ✅ **Steno → Kiwi bridge** - Already implemented in plover dictionaries (clip-kiwi.json, cache-kiwi.json)

3. ✅ **Agent bootstrap directive** - Created `create_agent.md` v1.0.0:
   - Takes domain description and project path
   - Creates full .ai/ structure (directives/, scripts/, knowledge/)
   - Generates AGENTS.md with three-layer architecture
   - Optional steno setup: runs `cache-kiwi add` and `clip-kiwi save` commands
   - Published to registry

4. ✅ **Registry population** - Core directives synced:
   - `create_agent` v1.0.0 - The meta-directive
   - `init` v6.0.3 - Project initialization  
   - `context` v2.0.1 - Context generation
   - `create_directive` v2.6.2 - Create new directives
   - `sync_directives` v2.0.0 - Sync all locations

**Deprecated/Removed:**
- `bootstrap.md` → merged into `create_agent`
- `kiwi_dev_bootstrap.md` → merged into `create_agent`
- `init_ai_config.md` → removed (.cursor creation deprecated)

---

## Summary

You're building **the harness for building agents**, not just agents.

The harness = steno chords (fast human input) + kiwi ecosystem (structured LLM substrate)

Agents are outputs. The quant-kiwi is proof of concept. The real value is the meta-framework that lets you (or LLMs) create agents for any domain by:
- Defining workflows (directives)
- Implementing operations (scripts)  
- Accumulating expertise (knowledge)
- Iterating rapidly (steno + kiwi)

Everything flows through the Kiwi MCP tools, making it introspectable, versionable, and LLM-generatable.
