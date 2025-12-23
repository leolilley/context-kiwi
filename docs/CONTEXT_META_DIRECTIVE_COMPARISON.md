# Before & After: Context Meta-Directive

## Before (Current System)

### File Structure
```
project/
└── .ai/
    ├── tech_stack.md        ← Manual, static file
    ├── patterns/
    └── directives/custom/
```

### How It Works
1. User runs `run("init")`
2. `init` directive creates `tech_stack.md` with basic info
3. User manually edits `tech_stack.md` to add details
4. File becomes stale as project evolves
5. User must remember to update it

### Problems
- ❌ Manual maintenance required
- ❌ Becomes outdated quickly
- ❌ Limited scope (just tech stack)
- ❌ Inconsistent across projects
- ❌ No analysis of actual codebase

### Example `tech_stack.md`
```markdown
# Tech Stack

## Language
- Primary: TypeScript
- Version: 5.0+

## Framework
- Name: Next.js
- Version: 14.x

[User manually adds more...]
```

## After (New System)

### File Structure
```
project/
├── context.md              ← Meta-directive (core, shared)
└── .ai/
    ├── project_context.md  ← Auto-generated, comprehensive
    ├── tech_stack.md       ← Legacy (optional, backward compat)
    ├── patterns/
    └── directives/custom/
```

### How It Works
1. User runs `run("init")`
   - Creates `.ai/` structure
   - Suggests: `run("context")`
2. User runs `run("context")`
   - Loads `context.md` directive
   - LLM analyzes codebase automatically
   - Generates `project_context.md`
3. File stays current
   - Re-run `run("context")` anytime to refresh
   - Always reflects current codebase

### Benefits
- ✅ Automatic generation
- ✅ Always current (re-run anytime)
- ✅ Comprehensive analysis (not just tech stack)
- ✅ Consistent across projects
- ✅ Analyzes actual codebase patterns

### Example `project_context.md`
```markdown
# Project Context: My Next.js App

## Identity
- Name: my-nextjs-app
- Type: Web Application
- Description: E-commerce platform built with Next.js

## Technology Stack
- Language: TypeScript 5.0+
- Framework: Next.js 14.x (App Router)
- State: Zustand for client, React Query for server
- Styling: Tailwind CSS + shadcn/ui
- Testing: Vitest + Playwright

## Dependencies & Environment
[Auto-detected from package.json, lockfile]
- Runtime: next@14.0.0, react@18.2.0, zustand@4.4.0
- Dev: typescript@5.0.0, vitest@1.0.0
- Env vars: NEXT_PUBLIC_API_URL, DATABASE_URL

## Project Structure
```
src/
├── app/              # Next.js App Router pages
├── components/       # React components
├── lib/              # Utilities
└── hooks/            # Custom hooks
```

## Conventions & Patterns
[Auto-detected from code analysis]
- File naming: kebab-case for components
- Component style: Functional components with TypeScript
- State management: Zustand stores in src/stores/
- API calls: React Query hooks in src/hooks/
- Styling: Tailwind utility classes
- Error handling: try/catch with error boundaries

## Development Workflow
[Auto-detected from package.json scripts]
- Build: `npm run build`
- Dev: `npm run dev`
- Test: `npm test`
- Lint: `npm run lint`

## Context Kiwi Integration
- Patterns: component.md, api.md, hook.md
- Custom directives: checkout_flow.md
```

## Side-by-Side Comparison

| Aspect | Before | After |
|--------|--------|-------|
| **Creation** | Manual (user edits) | Automatic (AI analyzes) |
| **Maintenance** | User must remember | Re-run directive |
| **Scope** | Tech stack only | Comprehensive analysis |
| **Accuracy** | Can become stale | Always current |
| **Consistency** | Varies by project | Standardized format |
| **Code Analysis** | None | Analyzes actual code |
| **Pattern Detection** | Manual | Automatic |
| **Structure Detection** | Manual | Automatic |
| **Convention Detection** | Manual | Automatic |

## Usage Comparison

### Before
```bash
# Initialize
run("init")
# → Creates tech_stack.md (basic)

# User manually edits tech_stack.md
# → Adds languages, frameworks, etc.
# → Forgets to update when project changes
```

### After
```bash
# Initialize
run("init")
# → Creates structure
# → Suggests: run("context")

# Generate context
run("context")
# → Analyzes codebase
# → Generates project_context.md (comprehensive)

# Refresh anytime
run("context")
# → Re-analyzes
# → Updates project_context.md
```

## Migration Example

### Existing Project (Has `tech_stack.md`)
```bash
# Current state
.ai/
└── tech_stack.md  ← Manual file

# Run context directive
run("context")
# → Analyzes codebase
# → Generates project_context.md

# New state
.ai/
├── tech_stack.md         ← Still exists (backward compat)
└── project_context.md    ← New comprehensive file

# load_context() uses project_context.md (preferred)
# Falls back to tech_stack.md if needed
```

### New Project
```bash
# Initialize
run("init")
# → Creates .ai/ structure

# Generate context
run("context")
# → Analyzes codebase
# → Generates project_context.md

# Result
.ai/
└── project_context.md  ← Comprehensive, auto-generated
# No tech_stack.md needed
```

## Key Insight

**Before:** Context is a **static document** you maintain.

**After:** Context is a **living document** that analyzes your project.

The meta-directive pattern (`context.md`) teaches the AI how to understand any project, then generates documentation (`project_context.md`) that reflects the actual codebase.
