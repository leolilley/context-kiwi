# Context Kiwi: Architecture Trade-offs Analysis

## The Core Question

Should Context Kiwi remain a **remote-only MCP** (like AWS Knowledge MCP), or should it become a **locally-running MCP** that connects to a shared registry?

```
Current: Remote-only
┌─────────────────────────────────────────┐
│  context-kiwi.fly.dev (Remote MCP)         │
│  - 3 tools: search, execute, help       │
│  - Queries Supabase registry            │
│  - Returns directives as text           │
│  - CANNOT access local filesystem       │
└─────────────────────────────────────────┘
         ↓ MCP Protocol
┌─────────────────────────────────────────┐
│  LLM (Cursor)                           │
│  - Follows directive instructions       │
│  - Has local file access                │
│  - Does all the actual work             │
└─────────────────────────────────────────┘

Alternative: Local MCP + Remote Registry
┌─────────────────────────────────────────┐
│  Local MCP Server (runs on your machine)│
│  - Full filesystem access               │
│  - Can read .ai/, .context-kiwi/           │
│  - Can execute scripts, run linters     │
│  - Can enforce patterns programmatically│
│  - Connects to remote registry          │
└─────────────────────────────────────────┘
         ↓ MCP Protocol
┌─────────────────────────────────────────┐
│  LLM (Cursor)                           │
│  - Orchestrates via MCP tools           │
│  - Receives structured results          │
│  - Less "follow these instructions"     │
│  - More "call this tool"                │
└─────────────────────────────────────────┘
         ↓ HTTPS
┌─────────────────────────────────────────┐
│  Registry (Supabase)                    │
│  - Shared directive storage             │
│  - Version management                   │
│  - Community directives                 │
└─────────────────────────────────────────┘
```

---

## What We Have Now

### The Remote MCP Reality

```json
// mcp.json - as simple as AWS
{
  "context-kiwi": {
    "url": "https://context-kiwi.fly.dev/mcp",
    "headers": {}
  }
}
```

**What it can do:**
- Serve directives from a central registry
- Search for directives by intent
- Provide init instructions for new projects
- Track directive versions
- Let users publish directives

**What it CANNOT do:**
- Read your local `.ai/` context
- Enforce patterns programmatically
- Run validation/linting on generated code
- Execute scripts or commands
- Access `~/.context-kiwi/` for user preferences
- Know anything about your actual project

### The Flow Today

```
User: "Create a React component"

1. LLM calls search_tool("create component")
2. Remote MCP returns: [{name: "create_component", ...}]
3. LLM calls execute("get_directive", {name: "create_component"})
4. Remote MCP returns: curl command to download directive
5. LLM runs curl → downloads .ai/directives/core/create_component.md
6. LLM reads the directive file
7. LLM follows the <process> steps manually
8. LLM generates code based on directive instructions
```

**The LLM is doing ALL the work.** The MCP is just a glorified file server.

---

## What the Original Vision Promised

From `og.md`, the vision was a **code generation compiler**:

```
User: "Add pet listing feature"

1. MCP loads project context from .ai/
2. MCP runs pre-flight validation
3. MCP calls codegen handlers:
   - create_migration → SQL file
   - create_api → Express routes
   - create_screen → React components
   - create_tests → Test files
4. MCP validates generated code (lint, typecheck)
5. MCP returns structured result with file paths
6. LLM presents results to user
```

### Key Differences

| Aspect | Current (Remote) | Original Vision (Local) |
|--------|------------------|------------------------|
| **Who generates code** | LLM follows instructions | MCP runs codegen handlers |
| **Context awareness** | None (stateless) | Reads .ai/, knows your patterns |
| **Validation** | None | Lint, typecheck, test generated code |
| **Consistency** | Hope the LLM follows patterns | Programmatically enforced |
| **File operations** | LLM does it | MCP writes files directly |
| **Pattern templates** | Markdown examples | Executable templates with variables |
| **Progressive disclosure** | Directive XML only | Tool can ask questions dynamically |

---

## The Trade-off Matrix

### Remote-Only MCP (Current)

**Pros:**
- Zero setup - just add URL to mcp.json
- No local dependencies
- Works immediately on any machine
- No security concerns (can't touch your files)
- Simple to maintain and deploy
- Scales infinitely (stateless)

**Cons:**
- Can't read local context (`.ai/tech_stack.md`)
- Can't enforce patterns programmatically
- Can't validate generated code
- Can't run scripts or commands
- LLM has to do all the heavy lifting
- No true "automation" - just instructions
- Can't use `~/.context-kiwi/` for user settings
- Directives are just text, not executable

### Local MCP + Remote Registry

**Pros:**
- Full filesystem access
- Can read `.ai/` context and inject into generation
- Can run linters, type checkers, test runners
- Can execute pattern templates with real variable substitution
- Can write files atomically (all or nothing)
- Can track project state in `~/.context-kiwi/`
- Can have codegen handlers that actually generate code
- Can enforce consistency programmatically
- Still shares directives via remote registry

**Cons:**
- Requires local installation
- Need to manage dependencies (Python, Node, etc.)
- Security surface (MCP can touch files)
- More complex setup
- Platform-specific concerns (Windows/Mac/Linux)
- Need to handle MCP server lifecycle

---

## What Local MCP Unlocks

### 1. True Context Injection

```python
# Local MCP can do this:
async def create_component(name: str):
    # Read project context
    tech_stack = read_file(".ai/tech_stack.md")
    patterns = read_file(".ai/patterns/component.md")
    design_system = read_file(".ai/design_system.md")
    
    # Know what framework you're using
    if "React" in tech_stack:
        template = load_template("react_component")
    elif "Vue" in tech_stack:
        template = load_template("vue_component")
    
    # Generate with full context
    code = template.render(
        name=name,
        styling=design_system.colors,
        patterns=patterns
    )
    
    return code
```

**Remote MCP cannot do this** - it doesn't know your tech stack.

### 2. Pattern Enforcement

```python
# Local MCP can validate:
async def validate_against_patterns(generated_code: str):
    patterns = load_patterns(".ai/patterns/")
    
    violations = []
    
    # Check API patterns
    if "fetch(" in generated_code and patterns.api.use_api_client:
        violations.append("Use apiClient instead of raw fetch")
    
    # Check component patterns
    if "class " in generated_code and patterns.components.functional_only:
        violations.append("Use functional components, not classes")
    
    return violations
```

**Remote MCP cannot do this** - it can only suggest patterns in directive text.

### 3. Pre-flight Validation

```python
# Local MCP can check before generating:
async def preflight_check(feature_name: str):
    # Check for conflicts
    existing_files = glob("./**/feature_name*")
    if existing_files:
        return Error(f"Feature {feature_name} already exists")
    
    # Check dependencies
    package_json = read_json("package.json")
    if "react" not in package_json.dependencies:
        return Error("React not installed")
    
    # Check patterns exist
    if not exists(".ai/patterns/component.md"):
        return Error("No component pattern defined")
    
    return Ok("Ready to generate")
```

### 4. Atomic File Operations

```python
# Local MCP can do atomic writes:
async def create_feature(name: str):
    files_to_create = []
    
    try:
        files_to_create.append(generate_migration(name))
        files_to_create.append(generate_api(name))
        files_to_create.append(generate_screen(name))
        files_to_create.append(generate_tests(name))
        
        # All or nothing
        for f in files_to_create:
            write_file(f.path, f.content)
        
        return Success(files_to_create)
    except Exception:
        # Rollback
        for f in files_to_create:
            delete_file(f.path)
        raise
```

### 5. User-level Configuration

```
~/.context-kiwi/
├── config.yaml           # User preferences
├── cache/               # Downloaded directives
├── templates/           # Custom templates
└── patterns/            # User's default patterns

# Local MCP can read this:
user_config = read_yaml("~/.context-kiwi/config.yaml")
default_framework = user_config.defaults.framework  # "React"
```

### 6. Real Codegen Handlers

```python
# Instead of directives being instructions...
# They become tool definitions:

@tool("create_component")
async def create_component(
    name: str,
    style: Literal["css", "tailwind", "styled"] = "css"
):
    """Create a React component following project patterns."""
    
    # This runs ON YOUR MACHINE
    context = await load_project_context()
    template = await get_template("component", context.framework)
    
    code = template.render(name=name, style=style)
    
    # Write the file
    path = f"src/components/{name}.tsx"
    await write_file(path, code)
    
    # Run linter
    lint_result = await run_command(f"eslint {path} --fix")
    
    return {
        "created": path,
        "lint_passed": lint_result.success
    }
```

---

## Hybrid Architecture Proposal

Keep the best of both worlds:

```
┌──────────────────────────────────────────────────────────────┐
│                    Local MCP Server                          │
│                    (runs on your machine)                    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Core Tools (local execution)                          │  │
│  │                                                        │  │
│  │  - create_component  → generates code locally          │  │
│  │  - validate_code     → runs linter/typecheck           │  │
│  │  - load_context      → reads .ai/ files                │  │
│  │  - apply_pattern     → template rendering              │  │
│  └────────────────────────────────────────────────────────┘  │
│                              │                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Registry Tools (remote calls)                         │  │
│  │                                                        │  │
│  │  - search_directives → queries Supabase                │  │
│  │  - get_directive     → downloads from registry         │  │
│  │  - publish_directive → uploads to registry             │  │
│  │  - check_updates     → compares versions               │  │
│  └────────────────────────────────────────────────────────┘  │
│                              │                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Context Layer                                         │  │
│  │                                                        │  │
│  │  - Reads .ai/tech_stack.md                            │  │
│  │  - Reads .ai/patterns/*                               │  │
│  │  - Reads ~/.context-kiwi/config.yaml                     │  │
│  │  - Caches directives locally                          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Supabase Registry                         │
│                    (shared, remote)                          │
│                                                              │
│  - directives table                                          │
│  - directive_versions table                                  │
│  - Community contributions                                   │
│  - Version management                                        │
└──────────────────────────────────────────────────────────────┘
```

### MCP Config for Local Server

```json
{
  "context-kiwi": {
    "command": "context-kiwi",
    "args": ["serve"],
    "env": {
      "CONTEXT_KIWI_REGISTRY": "https://context-kiwi.fly.dev"
    }
  }
}
```

Or with npx/uvx for zero-install:

```json
{
  "context-kiwi": {
    "command": "uvx",
    "args": ["context-kiwi", "serve"]
  }
}
```

---

## What Changes with Local MCP

### Tool Design Shifts

**Remote (current):**
```
Tools: search_tool, execute, help
Everything else: "follow these directive instructions"
```

**Local:**
```
Tools:
  Registry:
    - search_directives
    - sync_directives
    - publish_directive
  
  Context:
    - load_context
    - get_tech_stack
    - get_patterns
  
  Codegen:
    - create_component
    - create_api
    - create_migration
    - create_test
  
  Validation:
    - lint_code
    - typecheck
    - run_tests
  
  Patterns:
    - apply_pattern
    - extract_pattern
    - validate_pattern
```

### Directive Purpose Shifts

**Remote:** Directives are instructions for LLM to follow
**Local:** Directives can define tool behavior, or be instructions

```xml
<!-- Type 1: Tool Definition (local MCP executes this) -->
<directive type="tool">
  <name>create_component</name>
  <handler>codegen.create_component</handler>
  <inputs>
    <input name="name" type="string" required="true" />
    <input name="style" type="enum" values="css,tailwind" />
  </inputs>
</directive>

<!-- Type 2: Instructions (LLM follows these) -->
<directive type="instructions">
  <name>architecture_decision</name>
  <process>
    <step>Analyze the requirements</step>
    <step>Consider trade-offs</step>
    <step>Document in .ai/decisions/</step>
  </process>
</directive>
```

---

## Recommendation

### Short-term: Keep Remote MCP

The current implementation works. It's simple, requires no setup, and provides value (shared directive registry, init workflow).

### Medium-term: Build Local MCP

Add a local MCP server that:
1. Connects to the same Supabase registry
2. Adds filesystem access for context loading
3. Adds basic codegen tools
4. Adds validation tools

### Migration Path

```
Phase 1 (Now):
  Remote MCP → Directive registry + init instructions
  
Phase 2 (Next):
  Local MCP (optional) → Context loading + pattern validation
  Remote MCP → Still works for zero-setup users
  
Phase 3 (Future):
  Local MCP → Full codegen tools
  Remote MCP → Deprecated or kept for simple use cases
```

### The Key Insight

The original vision required **local execution**. A remote MCP fundamentally cannot:
- Read your project context
- Enforce patterns
- Validate code
- Write files

These aren't limitations we can work around - they're architectural constraints of remote execution.

**If we want the original vision, we need a local MCP.**

The remote registry remains valuable as the shared source of truth for directives. But the execution layer needs to run locally.

---

## Decision Points

1. **Is zero-setup worth the limited functionality?**
   - Current: Yes, simple but limited
   - Local: More setup, full functionality

2. **Who should do code generation?**
   - Current: LLM follows instructions
   - Local: MCP runs codegen handlers

3. **How important is pattern enforcement?**
   - Current: "Please follow these patterns" (hope-based)
   - Local: Programmatic validation (guaranteed)

4. **Do users need ~/.context-kiwi/ global config?**
   - Current: Not possible
   - Local: Yes, user preferences, cached directives

5. **Is the "MCP as file server" model enough?**
   - Current: Barely - it's a glorified curl
   - Local: MCP becomes a true development assistant

---

## Conclusion

The current remote MCP is **useful but limited**. It's essentially:
- A directive package manager
- An init workflow provider
- A search interface

It is NOT:
- A code generation engine
- A pattern enforcer
- A validation system
- A context-aware assistant

To achieve the original vision from `og.md`, we need local execution. The good news: we can keep the remote registry for sharing directives while adding a local MCP for execution.

**The remote MCP isn't wrong - it's incomplete.**

