# Context Kiwi: Technical Architecture

## Overview

Context Kiwi is a remote MCP server that provides directive-based code generation capabilities. The server exposes **3 meta-tools** that allow LLMs to discover and fetch directives stored in Supabase.

**Key Design Principle:** The MCP server runs remotely and can ONLY access Supabase. It cannot write to the user's local filesystem. Directives are instructions that the LLM follows using its own file access capabilities.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   Context Kiwi MCP Server (Python)                         │
│                   Hosted remotely (e.g., Fly.io)                        │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              3 Meta-Tools (Exposed via MCP Protocol)            │    │
│  │                                                                 │    │
│  │        search_tool          execute            help             │    │
│  │                                                                 │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Tool Registry                              │    │
│  │                                                                 │    │
│  │    Directive Tools (called via execute):                        │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │  get_directive  │  check_updates  │  publish_directive  │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  │                                                                 │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │              DirectiveLoader / DirectiveDB                      │    │
│  │         Queries Supabase - NO local file access                 │    │
│  └──────────────────────────┬──────────────────────────────────────┘    │
│                             │                                           │
│                             ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Supabase Database                            │    │
│  │            - directives table (metadata)                        │    │
│  │            - directive_versions table (content)                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ MCP Protocol
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          LLM (Cursor/Claude)                            │
│                                                                         │
│   1. Calls meta-tools via MCP                                           │
│   2. Receives directive content (markdown + XML)                        │
│   3. Follows directive steps using LOCAL file access                    │
│   4. Can read/write ~/.context-kiwi/, .ai/, project files                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### How execute() Works

The `execute` meta-tool dispatches to directive tools in the Tool Registry:

```
execute("get_directive", {name: "bootstrap"})
         │
         ▼
    Tool Registry
         │
         ├──► get_directive handler    ──► DirectiveDB ──► Supabase
         ├──► check_updates handler    ──► DirectiveDB ──► Supabase  
         └──► publish_directive handler ──► DirectiveDB ──► Supabase
```

---

## Layer Architecture

### Layer 1: Meta-Tools (3 Exposed)

The LLM sees only these 3 tools:

| Tool | Purpose | Example |
|------|---------|---------|
| `search_tool` | Find directives by intent | `search_tool({query: "create component"})` |
| `execute` | Run directive tools | `execute("get_directive", {name: "bootstrap"})` |
| `help` | Workflow guidance | `help({topic: "workflow"})` |

### Layer 2: Directive Tools (via execute)

These tools run on the server and interact with Supabase:

| Directive Tool | What it Does | Example |
|----------------|--------------|---------|
| `get_directive` | Fetches directive content from registry | `{name: "bootstrap", version: "^1.0.0"}` |
| `check_updates` | Compares local versions with registry | `{local_versions: {"bootstrap": "1.5.0"}}` |
| `publish_directive` | Publishes new version to registry | `{name: "...", version: "1.0.0", content: "..."}` |

### Layer 3: Directives (Instructions for LLM)

Directives are markdown files with embedded XML stored in Supabase. They contain:

- **Metadata**: Name, version, description, category
- **Permissions**: What access the LLM needs (filesystem, shell, etc.)
- **Process**: Step-by-step instructions for the LLM to follow
- **Inputs/Outputs**: Parameters and expected results

**The LLM follows directive instructions to:**
- Create/modify files in the project
- Run shell commands
- Update configuration

---

## Component Details

### DirectiveLoader (`src/directives/loader.py`)

A simple class that queries Supabase. It has NO local file access:

```python
class DirectiveLoader:
    """Loads directives from Supabase registry."""
    
    def get(self, name, version=None):
        """Get directive from registry."""
        return self.db.get(name, version)
    
    def search(self, query, tech_stack=None):
        """Search directives in registry."""
        return self.db.search(query, tech_stack=tech_stack)
    
    def list(self, category=None):
        """List directives in registry."""
        return self.db.list(category=category)
```

### DirectiveDB (`src/db/directives.py`)

Handles CRUD operations against Supabase:

- `get(name, version)` - Fetch specific directive with version constraint
- `search(query, tech_stack)` - Full-text search with compatibility scoring
- `list(category)` - List all directives, optionally filtered
- `publish(name, version, content)` - Add new version
- `get_versions(name)` - Get all versions for a directive

### Server Entry Point (`src/server.py`)

The main server class `CodeKiwiMCPServer` handles:

1. Configuration loading via `ConfigManager`
2. Tool registration via `ToolRegistry`
3. MCP protocol handlers

**Transport Modes:**
- **stdio**: For local development with Cursor
- **HTTP**: Streamable HTTP transport for production

```python
# Run stdio mode (default)
python -m src.server --stdio

# Run HTTP mode
python -m src.server --http --port 8000
```

---

## Data Flow Examples

### Fetching a Directive

```
LLM                          MCP Server                    Supabase
 │                               │                            │
 │ execute("get_directive",      │                            │
 │         {name: "bootstrap"})  │                            │
 │──────────────────────────────►│                            │
 │                               │                            │
 │                               │ SELECT * FROM directives   │
 │                               │ WHERE name = 'bootstrap'   │
 │                               │───────────────────────────►│
 │                               │                            │
 │                               │◄───────────────────────────│
 │                               │ {name, version, content}   │
 │                               │                            │
 │◄──────────────────────────────│                            │
 │ {status: "found",             │                            │
 │  directive: {content: "..."}} │                            │
 │                               │                            │
 │ (LLM follows directive        │                            │
 │  instructions locally)        │                            │
```

### Checking for Updates

```
LLM                          MCP Server                    Supabase
 │                               │                            │
 │ execute("check_updates",      │                            │
 │  {local_versions: {           │                            │
 │    "bootstrap": "1.5.0",      │                            │
 │    "create_component": "1.0.0"│                            │
 │  }})                          │                            │
 │──────────────────────────────►│                            │
 │                               │ SELECT name, latest_version│
 │                               │ FROM directives            │
 │                               │───────────────────────────►│
 │                               │◄───────────────────────────│
 │                               │                            │
 │◄──────────────────────────────│                            │
 │ {updates_available: [         │                            │
 │   {name: "bootstrap",         │                            │
 │    local: "1.5.0",            │                            │
 │    latest: "1.7.0",           │                            │
 │    content: "..."}            │                            │
 │  ]}                           │                            │
 │                               │                            │
 │ (LLM updates local cache)     │                            │
```

---

## Project Structure

```
src/
├── __init__.py              # Package version
├── server.py                # Main MCP server entry point
├── server_http.py           # HTTP transport for production
├── config/
│   ├── __init__.py
│   └── settings.py          # Configuration management
├── db/
│   ├── __init__.py
│   ├── client.py            # Supabase client singleton
│   ├── directives.py        # Directive CRUD operations
│   └── helpers.py           # DB utilities
├── directives/
│   ├── __init__.py
│   └── loader.py            # DirectiveLoader (queries Supabase)
├── tools/
│   ├── __init__.py
│   ├── base.py              # BaseTool class
│   ├── core.py              # 3 meta-tools (search_tool, execute, help)
│   ├── registry.py          # Tool registration
│   └── directives/          # Directive tools
│       ├── __init__.py
│       ├── get.py           # get_directive handler
│       ├── check_updates.py # check_updates handler
│       └── publish.py       # publish_directive handler
├── mcp_types/
│   ├── __init__.py
│   └── tools.py             # Type definitions
└── utils/
    ├── __init__.py
    ├── logger.py            # Logging utilities
    └── semver.py            # Version comparison
```

---

## Database Schema

### directives table

```sql
CREATE TABLE directives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'core',
    is_official BOOLEAN DEFAULT false,
    tech_stack TEXT[],                    -- Compatibility tags
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### directive_versions table

```sql
CREATE TABLE directive_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    directive_id UUID REFERENCES directives(id),
    version TEXT NOT NULL,                -- Semver (e.g., "1.2.0")
    content TEXT NOT NULL,                -- Full markdown + XML
    changelog TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(directive_id, version)
);
```

---

## Adding New Directive Tools

To add a new directive tool:

1. Create handler in `src/tools/directives/`:

```python
# src/tools/directives/my_tool.py
async def my_tool_handler(params, context):
    # Query/write Supabase
    db = DirectiveDB()
    result = db.some_operation(params)
    return {"status": "success", "data": result}
```

2. Export from `src/tools/directives/__init__.py`

3. Register in `server.py`:

```python
def _register_directive_tools(self, execute_tool):
    from context_kiwi.tools.directives import my_tool_handler
    execute_tool.register_directive_tool("my_tool", my_tool_handler)
```

---

## Key Principles

1. **MCP server has NO local file access** - it only queries Supabase
2. **Directives are instructions for the LLM** - the LLM has local file access
3. **Directive tools are registry operations** - get, check, publish
4. **The LLM handles all local file operations** - following directive instructions
