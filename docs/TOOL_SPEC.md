# Context Kiwi Tool Specification

## 6 MCP Tools

| Tool | Purpose |
|------|---------|
| `search` | Find directives (local or registry) |
| `run` | Execute directive from local (project > user) |
| `get` | Download from registry → local |
| `publish` | Upload from local → registry |
| `delete` | Delete directive from registry/user/project |
| `help` | Guidance |

---

## 1. `search`

Find directives using natural language search with multi-term matching.

```python
@server.tool()
def search(
    query: str,  # REQUIRED: Natural language query (supports multiple terms)
    source: str,  # REQUIRED: "local" | "registry" | "all"
    project_path: str = None,  # REQUIRED for "local"/"all": absolute path to project root
    sort_by: str = "score"  # OPTIONAL: "score" (default) | "success_rate" | "date" | "downloads"
) -> list[DirectiveMatch]
```

### Search Features

- **Multi-term matching**: "JWT auth" matches directives containing both "JWT" and "auth"
- **Smart scoring**: Name matches ranked higher than description matches
- **Context-aware**: Registry search auto-includes your tech stack for better ranking
- **Scalable**: Uses improved term matching (PostgreSQL full-text search ready)

### Source Options

| Source | Searches | Requires project_path? | Context |
|--------|----------|------------------------|---------|
| `"local"` | Project + User space | **Yes** | No |
| `"registry"` | Remote registry | No | Yes - auto-injects tech stack |
| `"all"` | Everything | **Yes** | Yes for registry portion |

**IMPORTANT:** `project_path` is required when searching "local" or "all" because the MCP doesn't automatically know where your project is located. User space is found via the `CONTEXT_KIWI_HOME` environment variable, but project space (`.ai/directives/`) requires an explicit path.

### Examples

**Local search (single term):**
```
search("auth", "local", project_path="/path/to/project")

→ [
    { name: "our_auth", score: 80, source: "project" },
    { name: "auth_helper", score: 60, source: "user" }
  ]
```

**Registry search (multi-term, context-aware):**
```
search("JWT authentication", "registry")

# Behind the scenes:
# → Parses query into terms: ["JWT", "authentication"]
# → Reads .ai/project_context.md → detects ["React", "TypeScript", "Zustand"]
# → Searches registry with all terms + detected tech stack
# → Ranks by relevance (70%) + compatibility (30%)

→ [
    { name: "jwt_auth_zustand", score: 95, source: "registry", 
      tech_stack: ["React", "Zustand"], version: "1.2.0" },
    { name: "jwt_auth_redux", score: 70, source: "registry",
      tech_stack: ["React", "Redux"], version: "1.0.0" }
  ]
```

**Search everywhere (multi-term):**
```
search("form validation", "all", project_path="/path/to/project")

→ [
    { name: "form_validator", score: 80, source: "project" },
    { name: "react_form_validation", score: 75, source: "registry" }
  ]
```

---

## 2. `run`

Execute a directive with preflight validation and context loading.

**Source: Local only (project > user)**

```python
@server.tool()
def run(
    directive: str,  # REQUIRED: Directive name (must exist locally)
    inputs: dict = None,  # Optional: Input parameters
    project_path: str = None  # Optional: use if workspace != current directory
) -> RunResult
```

### Execution Flow

```
run("jwt_auth_zustand", {refresh_endpoint: "/auth/refresh"})
    │
    ├─ LOAD
    │   ├─ Check .ai/directives/ (project)
    │   ├─ Check ~/.context-kiwi/directives/ (user)
    │   └─ Fail if not found locally
    │
    ├─ PREFLIGHT
    │   ├─ Validate inputs against JSON Schema
    │   └─ Check required credentials (env vars)
    │
    ├─ CONTEXT
    │   ├─ Load .ai/project_context.md
    │   ├─ Load .ai/patterns/*.md
    │   └─ Load .ai/design_system.md (optional)
    │
    └─ RETURN
        ├─ Directive content + parsed structure
        ├─ Project context
        ├─ Validated inputs
        └─ Instructions for LLM to follow

→ {
    status: "ready",
    directive: { ... },      # Parsed directive
    context: { ... },        # Project context
    inputs: { ... },         # Validated inputs
    instructions: "Follow the <process> steps..."
  }
```

### Error Cases

```
run("unknown_directive")
→ { status: "error", message: "Directive not found. Use search() or get() first." }

run("jwt_auth", {})  # Missing required input
→ { status: "validation_failed", errors: ["'refresh_endpoint' is required"] }
```

---

## 3. `get`

Download directive from registry to local.

**Source: Registry only**
**Destination: Project (default) or User**

```python
@server.tool()
def get(
    directive: str,  # REQUIRED: Directive name
    source: str = "registry",  # Where to get from
    to: str = "project",  # "project" | "user"
    version: str = None,  # Specific version (default: latest)
    project_path: str = None  # Optional: use if workspace != current directory
) -> GetResult
```

### Examples

**Download to project (for team):**
```
get("jwt_auth_zustand")

→ Downloaded jwt_auth_zustand@1.2.0 to .ai/directives/core/
```

**Download to user space (personal):**
```
get("my_helper", to="user")

→ Downloaded my_helper@1.0.0 to ~/.context-kiwi/directives/core/
```

**Get specific version:**
```
get("jwt_auth_zustand", version="1.0.0")

→ Downloaded jwt_auth_zustand@1.0.0 to .ai/directives/core/
```

**List available versions:**
```
get("jwt_auth_zustand", list_versions=True)

→ {
    name: "jwt_auth_zustand",
    versions: ["1.2.0", "1.1.0", "1.0.0"],
    latest: "1.2.0",
    local: "1.1.0"  # Currently in project
  }
```

**Check for updates:**
```
get(check=True)

→ {
    updates_available: [
      { name: "jwt_auth_zustand", local: "1.1.0", latest: "1.2.0" }
    ],
    up_to_date: ["create_component@1.0.0"]
  }
```

**Update all:**
```
get(update=True)

→ {
    updated: ["jwt_auth_zustand: 1.1.0 → 1.2.0"],
    already_current: ["create_component@1.0.0"]
  }
```

---

## 4. `publish`

Upload local directive to registry.

**Source: Local (project or user)**
**Destination: Registry**

```python
@server.tool()
def publish(
    directive: str,  # REQUIRED: Directive name
    version: str,  # REQUIRED: Semver version (e.g., "1.0.0")
    source: str = "project",  # "project" | "user"
    project_path: str = None  # Optional: use if workspace != current directory
) -> PublishResult
```

**Requires:** `CONTEXT_KIWI_API_KEY` or `SUPABASE_SECRET_KEY` environment variable

### Example

```
publish("our_api_pattern", version="1.0.0")

→ {
    status: "published",
    name: "our_api_pattern",
    version: "1.0.0",
    url: "https://codekiwi.dev/d/our_api_pattern"
  }
```

**Publish from user space:**
```
publish("my_helper", version="1.0.0", source="user")
```

### Validation

Before publishing:
- Valid XML structure in directive
- Required fields: name, version, description, process
- Tech stack declared
- At least one step in process

---

## 5. `delete`

Delete a directive from registry, user space, project space, or all.

```python
@server.tool()
def delete(
    name: str,  # REQUIRED: Directive name
    from: str = "registry",  # "registry" | "user" | "project" | "all"
    confirm: bool = False,  # REQUIRED: Must be True (safety check)
    cleanup_empty_dirs: bool = False,  # Remove empty folders
    project_path: str = None  # Optional: use if workspace != current directory
) -> DeleteResult
```

### Examples

**Delete from registry:**
```
delete("my_directive", from="registry", confirm=True)

→ { status: "deleted", deleted_from: { registry: { success: true } } }
```

**Delete from all locations:**
```
delete("my_directive", from="all", confirm=True)

→ { 
    status: "deleted",
    deleted_from: {
      registry: { success: true },
      user: { success: true },
      project: { success: true }
    }
  }
```

**Delete from project with cleanup:**
```
delete("my_directive", from="project", confirm=True, cleanup_empty_dirs=True, project_path="/path/to/project")
```

**IMPORTANT:** Always set `confirm=True`. This prevents accidental deletions.

---

## 6. `help`

Workflow guidance.

```python
@server.tool()
def help(topic: str = None) -> str
```

### Topics

```
help()              → Overview
help("search")      → How to find directives
help("run")         → Execution flow
help("get")         → Registry download
help("publish")     → Sharing directives
help("context")     → The .ai/ folder
help("directives")  → Writing good directives
```

---

## Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                     Context Kiwi MCP Tools                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  search(query, source, project_path, sort_by)                   │
│    - source: "local" | "registry" | "all"                      │
│    - project_path: Required for "local"/"all"                 │
│    - sort_by: "score" (default) | "success_rate" | "date" | ...│
│    - project_path: Optional (use if workspace != cwd)          │
│                                                                 │
│  run(directive, inputs, project_path)                           │
│    - Execute from LOCAL only (project > user)                  │
│    - Preflight → Context → Return                              │
│                                                                 │
│  get(directive, source, to, version, project_path)              │
│    - Download from registry to local                            │
│    - to: "project" (default) | "user"                          │
│                                                                 │
│  publish(directive, version, source, project_path)              │
│    - Upload local → registry                                   │
│    - Requires: CONTEXT_KIWI_API_KEY or SUPABASE_SECRET_KEY     │
│                                                                 │
│  delete(name, from, confirm, project_path)                      │
│    - Delete from registry/user/project/all                     │
│    - confirm=True REQUIRED (safety check)                      │
│                                                                 │
│  help(topic)                    Guidance                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
              search ←───────────────────────────────────┐
                │                                        │
                ▼                                        │
┌─────────────────────────────┐    get    ┌─────────────────────────┐
│          LOCAL              │ ◄──────── │        REGISTRY         │
│                             │           │                         │
│  .ai/directives/ (project)  │  publish  │    Community directives │
│  ~/.context-kiwi/ (user)   │ ────────► │    Version control      │
│                             │           │    Search + discovery   │
│                             │  delete   │                         │
└─────────────────────────────┘ ────────► └─────────────────────────┘
                │
                │ run
                ▼
        ┌───────────────┐
        │   EXECUTION   │
        │               │
        │  Preflight    │
        │  Context      │
        │  Return to LLM│
        └───────────────┘
```

## Key Parameters

**project_path:** All tools accept a `project_path` parameter. Requirements vary by tool and operation:

**For `search` tool:**
- **Required** when `source="local"` or `source="all"` (to find `.ai/directives/` in your project)
- **Not needed** when `source="registry"` (searches remote only)
- Example: `project_path="/home/user/myproject"`
- Why: The MCP doesn't automatically know where your project is. User space comes from `CONTEXT_KIWI_HOME` env var, but project space needs an explicit path.

**For other tools:**
- Generally required when operating on project-specific resources
- Example: `run("directive", project_path="/home/user/myproject")`

**Common mistake:** Forgetting `project_path` when searching "local" or "all" will cause an error (previously would silently search only user space).
