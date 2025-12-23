# 🥝 Context Kiwi

> *"Give me a lever long enough and a fulcrum on which to place it, and I shall move the world."*  
> — Archimedes

**Solve once, solve everywhere.**

Context Kiwi is a directive-based system that turns hard-won coding solutions into transferable, reusable instructions. When you solve a tricky implementation problem, you capture it as a directive. Others can pull that directive, apply their own context, and derive the same solution—without needing to figure it out from scratch.

---

## Quick Start

### 1. Install

```bash
pip install context-kiwi
# or
uvx context-kiwi
```

### 2. Configure MCP

```json
// .cursor/mcp.json
{
  "mcpServers": {
    "context-kiwi": {
      "command": "context-kiwi",
      "env": {
        "CONTEXT_KIWI_HOME": "~/.context-kiwi",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_ANON_KEY": "your-anon-key-here"
      }
    }
  }
}
```

First run automatically creates `~/.context-kiwi/` and downloads core directives from the registry.

### 3. Initialize a Project

```
You: "Initialize this project for Context Kiwi"

LLM: run("init")
     → Detects: Python project (found pyproject.toml)
     → Creates: .ai/patterns/, .ai/directives/
     → Suggests: run("context") to generate project context
     → Suggests: run("init_python_mcp") for deep context
```

### 4. Add Deep Context (Optional)

```
You: "Run the Python MCP init"

LLM: run("init_python_mcp")
     → Creates: .ai/patterns/tool.md (how to write tools)
     → Creates: .ai/patterns/types.md (type system reference)
     → Creates: .ai/patterns/imports.md (import conventions)
     → Suggests: run("context") to generate full project context
```

Now even basic LLMs can generate correct code for your project.

### 5. Generate Project Context

```
You: "Generate project context"

LLM: run("context")
     → Analyzes codebase automatically
     → Generates: .ai/project_context.md (comprehensive context)
     → Includes: tech stack, structure, conventions, patterns
```

The `context` directive is a meta-directive that analyzes your project and generates comprehensive documentation. Re-run it anytime to refresh.

### 6. Find and Run Directives

```
You: "I need JWT auth"

LLM: search("jwt auth", source="registry")
     → Found: jwt_auth_zustand@1.0.0

LLM: get("jwt_auth_zustand", to="user")
     → Downloaded to ~/.context-kiwi/directives/core/

LLM: run("jwt_auth_zustand", project_path="/path/to/project")
     → Preflight: ✓ Validates inputs, checks packages
     → Context: Loads your .ai/ files
     → Returns: Directive + context for LLM to follow
```

---

## The 6 Tools

| Tool | What It Does |
|------|--------------|
| `search(query, source, project_path, sort_by)` | Find directives. `source`: "local", "registry", or "all". `project_path` required for "local"/"all". `sort_by` optional (default: "score"). |
| `run(directive, inputs)` | Execute directive with preflight + context loading |
| `get(directive, to)` | Download from registry. `to`: "project" or "user" |
| `publish(directive, version)` | Upload to registry for others |
| `delete(name, from, confirm)` | Delete directive from registry/user/project/all |
| `help(topic)` | Workflow guidance |

---

## Multi-Step Init System

Instead of one monolithic init, Context Kiwi uses specialized inits for deep context:

```
run("init")                    # Base: creates .ai/, detects project type
    ↓
run("init_python_mcp")         # Specialized: Python MCP patterns
run("init_react")              # Specialized: React component patterns  
run("init_fastapi")            # Specialized: FastAPI route patterns
...
```

**Create your own init:**

```
run("create_init", inputs={
    "tech_stack": "nextjs_app_router",
    "key_patterns": "server components, API routes, middleware"
})
→ Creates init_nextjs_app_router directive
→ Publish for others to use
```

---

## Where Things Live

```
~/.context-kiwi/                    # User space (created on first run)
├── directives/core/             # Core directives (read-only cache)
│   ├── init.md
│   ├── create_directive.md
│   ├── edit_core_directive.md
│   └── ...
├── directives.lock.json         # Version tracking for efficient sync
├── .runs/history.jsonl          # Run logs across all projects
└── .runs/anneals.jsonl          # Directive improvement logs

your-project/.ai/                # Project space (created by init)
├── project_context.md           # Auto-generated project context
├── patterns/                    # Code patterns
│   ├── tool.md                  # How to write tools
│   ├── types.md                 # Type reference
│   └── imports.md               # Import conventions
└── directives/
    └── custom/                  # Project-specific only
```

**Note:** Core directives live in user space only. Project `core/` is only created when editing a directive.

**Resolution order:** Project → User → Registry

---

## How It Works

```
run("some_directive")
    │
    ├─ LOAD: Find directive (project → user → registry)
    │
    ├─ PREFLIGHT: 
    │   ├─ Validate inputs (JSON Schema)
    │   ├─ Check credentials (env vars)
    │   ├─ Check packages (npm/pip)
    │   ├─ Check required files
    │   └─ Check required commands
    │
    ├─ CONTEXT: Load .ai/project_context.md, .ai/patterns/*
    │
    ├─ RETURN: Directive + context to LLM
    │
    └─ LOG: Record to ~/.context-kiwi/.runs/history.jsonl
```

The MCP doesn't generate code—it loads context and returns everything to the LLM. The LLM follows the directive's `<process>` steps using your project's patterns.

---

## The Vision

Most coding problems aren't unique. The auth flow you struggled with yesterday? Someone solved it last week.

**The problem:** Solutions are locked in people's heads, scattered across Stack Overflow.

**The solution:** Directives capture *how* to implement something. Combined with your project's context, they produce code that fits *your* codebase.

```
Directive (How)           +    Context (Your setup)
─────────────────              ──────────────────
"JWT auth with refresh          "React + TypeScript
tokens using Zustand            Zustand for state
and Axios interceptors"         src/lib/ for utils"
                           
                    ↓
                           
        Code that matches YOUR codebase
```

### Why This Works

1. **Context is leverage** — Simpler LLMs execute complex tasks when given proper patterns
2. **Transferable** — Same directive works across projects, frameworks, even LLMs
3. **Compounds** — Your `.ai/` folder gets richer over time

---

## Creating Directives

### Structure

```markdown
# My Directive

Description of what this does.

```xml
<directive name="my_directive" version="1.0.0">
  <metadata>
    <description>What it does</description>
    <category>core</category>
  </metadata>
  
  <context>
    <tech_stack>react, typescript</tech_stack>
    <assumptions>
      - User has React 18+
      - TypeScript configured
    </assumptions>
  </context>
  
  <inputs>
    <input name="component_name" type="string" required="true">
      Name of the component to create
    </input>
  </inputs>
  
  <!-- Optional: Preflight checks -->
  <preflight>
    <packages>
      <package manager="npm">zustand</package>
    </packages>
    <files>
      <file>tsconfig.json</file>
    </files>
  </preflight>
  
  <process>
    <step name="create_file">
      <description>Create the component file</description>
      <pattern><![CDATA[
// Full code example here
export const {component_name} = () => {
  return <div>Hello</div>
}
      ]]></pattern>
    </step>
  </process>
  
  <!-- Optional: Output validation -->
  <validation>
    <check name="lint">Run eslint</check>
    <check name="types">Run tsc</check>
  </validation>
</directive>
```

### Good Directives Have

1. **Specific context** — Tech stack, versions, dependencies
2. **Concrete patterns** — Actual code, not descriptions
3. **Clear assumptions** — What must be true for this to work

---

## Syncing & Editing

### Sync All Core Directives

```
get(update=true, to="user")
→ Fetches ALL core directives from registry
→ Skips unchanged (uses lock file)
→ Fast: only downloads what changed
```

### Edit a Core Directive

Core directives in `~/.context-kiwi/` are read-only. To edit:

```
run("edit_core_directive", {directive_name: "init"})
→ Step 1: get() copies to project .ai/directives/core/
→ Step 2: Edit the project copy
→ Step 3: publish() to registry
→ Step 4: get(update=true, to="user") to sync
→ Step 5: Delete project copy (optional)
```

---

## Self-Improvement

When a directive fails, improve it:

```
run("anneal_directive", inputs={
    "directive_name": "init",
    "error_description": "Creates design_system.md for backend projects"
})
→ Analyzes failure
→ Creates improved version
→ Optionally publishes fix
```

---

## Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `CONTEXT_KIWI_HOME` | User space location | No (defaults to `~/.context-kiwi`) |
| `SUPABASE_URL` | Your Supabase project URL | **Yes** |
| `SUPABASE_ANON_KEY` | Your Supabase anon/publishable key | **Yes** |
| `SUPABASE_SECRET_KEY` or `CONTEXT_KIWI_API_KEY` | For publishing directives | No (only needed for publishing) |

---

## For Developers

```bash
git clone https://github.com/yourusername/context-kiwi
cd context-kiwi
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Run MCP locally
context-kiwi --stdio
```

---

## Contributing

The best way to contribute is to **publish directives**. Solved a common problem? Capture it and share it.

```
publish("your_pattern", version="1.0.0")
```

---

## License

MIT

---

*Stop solving the same problems over and over. Capture it once, share it, move on.*
