# Context Meta-Directive Architecture

## Conceptual Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    THE META-DIRECTIVE PATTERN                │
└─────────────────────────────────────────────────────────────┘

context.md (Meta-Directive)
    │
    │ Contains instructions for LLM:
    │ "How to analyze this project"
    │
    ├─ Step 1: Scan codebase
    ├─ Step 2: Analyze structure  
    ├─ Step 3: Extract patterns
    ├─ Step 4: Generate documentation
    └─ Step 5: Integrate Context Kiwi
    │
    ↓ (LLM executes these steps)
    │
project_context.md (Generated Documentation)
    │
    │ Contains actual project information:
    │ "What this project is"
    │
    ├─ Identity
    ├─ Technology Stack
    ├─ Dependencies
    ├─ Project Structure
    ├─ Conventions & Patterns
    └─ Context Kiwi Integration
```

## Current vs New Architecture

### Current (Static)
```
User manually edits
    │
    ↓
tech_stack.md (static file)
    │
    ↓
load_context() reads it
    │
    ↓
Directives use context
```

**Problems:**
- Manual maintenance
- Becomes stale
- Limited scope (just tech stack)

### New (Dynamic)
```
context.md (meta-directive)
    │
    ↓
run("context") executes directive
    │
    ↓
LLM analyzes codebase
    │
    ↓
project_context.md (auto-generated)
    │
    ↓
load_context() reads it
    │
    ↓
Directives use context
```

**Benefits:**
- Always current
- Comprehensive analysis
- Automated generation
- Self-documenting process

## File Flow

### Initialization Flow
```
run("init")
    │
    ├─ Creates .ai/ structure
    ├─ Creates context.md (or suggests it)
    └─ Suggests: run("context")
        │
        ↓
    run("context")
        │
        ├─ Loads context.md directive
        ├─ LLM executes analysis steps
        └─ Generates project_context.md
```

### Context Loading Flow
```
Any directive execution
    │
    ↓
load_context()
    │
    ├─ Check: .ai/project_context.md exists?
    │   ├─ YES → Load it (preferred)
    │   └─ NO  → Check tech_stack.md (fallback)
    │
    ├─ Load patterns/
    └─ Return combined context
```

## Directory Structure

### Project Root
```
project/
├── context.md              # Meta-directive (if project-specific)
├── .ai/
│   ├── project_context.md  # Auto-generated (comprehensive)
│   ├── tech_stack.md       # Legacy (optional, backward compat)
│   ├── patterns/
│   │   ├── component.md
│   │   └── api.md
│   └── directives/
│       └── custom/
└── [project files]
```

### User Space (Core Directives)
```
~/.context-kiwi/
└── directives/core/
    ├── context.md          # Core meta-directive (shared)
    ├── init.md
    └── [other core directives]
```

## Data Flow Diagram

```
┌──────────────┐
│   User       │
└──────┬───────┘
       │
       │ run("context")
       ↓
┌─────────────────────┐
│  RunTool            │
│  - Load directive   │
│  - Run preflight    │
│  - Load context     │
└──────┬──────────────┘
       │
       │ Returns directive + context
       ↓
┌─────────────────────┐
│  LLM                │
│  - Reads context.md │
│  - Executes steps   │
│  - Analyzes code    │
└──────┬──────────────┘
       │
       │ Generates content
       ↓
┌─────────────────────┐
│  project_context.md │
│  (written to disk)  │
└──────┬──────────────┘
       │
       │ Available for future use
       ↓
┌─────────────────────┐
│  load_context()     │
│  - Reads file       │
│  - Returns to tools │
└─────────────────────┘
```

## Component Interactions

### 1. Directive System
- `context.md` is a standard directive
- Loaded via `DirectiveLoader`
- Executed via `run("context")`
- Follows same pattern as other directives

### 2. Context System
- `load_context()` reads generated files
- Prefers `project_context.md` over `tech_stack.md`
- Backward compatible with existing projects
- Returns structured context dict

### 3. Init System
- Creates `.ai/` structure
- Creates or references `context.md`
- Suggests running `context` directive
- No longer directly creates `tech_stack.md`

## Key Design Decisions

### 1. Meta-Directive Pattern
**Why:** Separates "how to analyze" from "what was analyzed"
- `context.md` = Instructions (reusable, shareable)
- `project_context.md` = Results (project-specific, generated)

### 2. Auto-Generation
**Why:** Keeps documentation current without manual effort
- Run `context` anytime to refresh
- Always reflects current codebase state
- No manual maintenance required

### 3. Backward Compatibility
**Why:** Don't break existing projects
- `tech_stack.md` still works
- Gradual migration path
- Both can coexist

### 4. Core Directive Location
**Why:** `context.md` in core, not project
- Reusable across all projects
- Shared improvements benefit everyone
- Project-specific customization via `.ai/directives/custom/`

## Example Usage

### First Time Setup
```bash
# Initialize project
run("init")
# → Creates .ai/ structure
# → Creates context.md (or suggests it)

# Generate context
run("context")
# → Analyzes codebase
# → Generates .ai/project_context.md
```

### Ongoing Development
```bash
# After major changes, refresh context
run("context")
# → Re-analyzes codebase
# → Updates .ai/project_context.md
```

### Using Context
```bash
# Any directive automatically loads context
run("some_directive")
# → load_context() reads project_context.md
# → Directive uses context for code generation
```

## Migration Path

### Existing Projects
1. Project has `.ai/tech_stack.md` (manual)
2. Run `run("context")` to generate `project_context.md`
3. Both files coexist
4. `load_context()` prefers `project_context.md`
5. Eventually remove `tech_stack.md` (optional)

### New Projects
1. Run `run("init")` → Creates structure
2. Run `run("context")` → Generates `project_context.md`
3. No `tech_stack.md` needed

## Benefits Summary

### For Users
- ✅ Always current documentation
- ✅ Comprehensive analysis (not just tech stack)
- ✅ No manual maintenance
- ✅ Self-documenting process

### For Context Kiwi
- ✅ Dynamic analysis (AI-powered)
- ✅ Rich context (patterns, structure, conventions)
- ✅ Extensible (add new analysis types)
- ✅ Transferable (same directive works everywhere)
