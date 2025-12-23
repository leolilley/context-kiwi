# Context Kiwi Documentation

Welcome to Context Kiwi - a directive-based MCP server for deterministic code generation.

## Quick Links

| Document | Description |
|----------|-------------|
| [Getting Started](./GETTING_STARTED.md) | Setup, installation, and first steps |
| [Architecture](./ARCHITECTURE.md) | Technical architecture and design |
| [Permissions](./PERMISSIONS.md) | Permissions and safety system |
| [Roadmap](./ROADMAP.md) | Future plans and milestones |

## What is Context Kiwi?

Context Kiwi is an MCP (Model Context Protocol) server that exposes **6 tools** to LLMs. These tools allow the LLM to:

1. **Search** for directives (local or registry)
2. **Run** directives from local space
3. **Get** directives from registry (download to local)
4. **Publish** directives to registry
5. **Delete** directives from registry/user/project
6. Get **help** on workflows

**Key Concept:** Directives are reusable instructions that combine with your project context (.ai/) to generate code that fits YOUR codebase. The MCP server loads directives and context - the LLM follows the directive steps using local file access.

## The 6 Tools

| Tool | Purpose |
|------|---------|
| `search` | Find directives by name/keywords (local, registry, or all) |
| `run` | Execute directive from local space (project > user) |
| `get` | Download directive from registry to local |
| `publish` | Upload local directive to registry |
| `delete` | Delete directive from registry/user/project/all |
| `help` | Get workflow guidance |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│              Context Kiwi MCP Server (Python)                          │
│                                                                     │
│  Exposed Tools (6 tools the LLM sees):                              │
│  ├── search     → Find directives (local/registry/all)             │
│  ├── run        → Execute directive from local                      │
│  ├── get        → Download from registry to local                  │
│  ├── publish    → Upload local to registry                          │
│  ├── delete     → Delete from registry/user/project                │
│  └── help       → Workflow guidance                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol (stdio or HTTP)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM (Cursor/Claude/etc)                          │
│                                                                     │
│  - Calls MCP tools                                                  │
│  - Receives directive + project context                            │
│  - Follows directive steps (creates files, runs commands)           │
│  - Has access to local file system                                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Local operations
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    User's Local Machine                             │
│                                                                     │
│  ~/.context-kiwi/              # User space                         │
│  ├── directives/core/        # Core directives (read-only)          │
│  └── .runs/                   # Execution history                   │
│                                                                     │
│  project/.ai/               # Per-project context                   │
│  ├── context.md             # Project-specific analysis directive   │
│  ├── project_context.md     # Generated comprehensive understanding │
│  ├── patterns/              # Code patterns (lazy creation)        │
│  └── directives/custom/     # Project-specific directives           │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### How It Works

1. **Search** for directives: `search("auth", "registry", "score")`
2. **Get** directive from registry: `get("jwt_auth_zustand", to="user")`
3. **Run** directive locally: `run("jwt_auth_zustand", {"refresh_endpoint": "/auth/refresh"})`
4. **Publish** your own: `publish("my_directive", "1.0.0")`
5. **Delete** when needed: `delete("my_directive", from="all", confirm=True)`
6. **Help** when stuck: `help("run")`

### First Time Setup

1. Initialize project: `run("init")` - Creates `.ai/` structure
2. Add deep context (optional): `run("init_python_mcp")` - Adds patterns
3. Search for directives: `search("auth", "registry", "score")`
4. Download and run: `get("jwt_auth")` then `run("jwt_auth")`

### Directive Storage

All directives are stored in **Supabase** with:
- Semver versioning (`1.0.0`, `1.1.0`, etc.)
- Categories (`core`, `meta`, `community`)
- Tech stack compatibility tags
- Quality scores and download counts

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| MCP Library | Official `mcp` package |
| Transport | stdio (dev) / Streamable HTTP (prod) |
| Database | Supabase (PostgreSQL) |
| Directive Format | Markdown with embedded XML |

## Development

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run locally (stdio mode for Cursor)
python -m src.server --stdio

# Run tests
pytest
```

See [Getting Started](./GETTING_STARTED.md) for detailed setup instructions.

