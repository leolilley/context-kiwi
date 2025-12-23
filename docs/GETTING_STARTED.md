# Getting Started with Context Kiwi

This guide covers setup for both **users** (connecting to Context Kiwi) and **developers** (working on Context Kiwi itself).

---

## For Users

### Prerequisites

- Cursor IDE (or any MCP-compatible client)
- Internet connection (for Supabase)

### Quick Start

Add Context Kiwi to your MCP configuration:

```json
// ~/.cursor/mcp.json
{
  "mcpServers": {
    "context-kiwi": {
      "url": "https://codekiwi.fly.dev/mcp"
    }
  }
}
```

That's it! On first use, you'll be guided through bootstrap.

### First Run: Initialize Project

When you first use Context Kiwi in a project:

1. **Navigate to your project root**
2. **Ask:** "Initialize this project for Context Kiwi"
3. **LLM calls:** `run("init")`
4. **Creates:** `.ai/` structure with project-specific context directive

The init process creates:

```
project/.ai/
├── context.md           # Project-specific analysis directive
├── project_context.md   # Generated understanding (after running context directive)
├── patterns/            # Code patterns (created when needed)
└── directives/custom/   # Project-specific directives (created when needed)

~/.context-kiwi/          # Created automatically on first use
├── directives/core/     # Core directives (read-only cache)
└── .runs/               # Execution history
```

### Using Context Kiwi

**Search for directives:**
```
"What can Context Kiwi help me with?"
→ search("auth", "registry", "score")
→ Returns matching directives from registry
```

**Download a directive:**
```
"Help me set up JWT auth"
→ search("jwt auth", "registry", "score")
→ get("jwt_auth_zustand", to="user")
→ Downloads directive to ~/.context-kiwi/directives/core/
```

**Run a directive:**
```
"Run the JWT auth directive"
→ run("jwt_auth_zustand", {"refresh_endpoint": "/auth/refresh"})
→ Loads directive + project context
→ LLM follows the steps to implement
```

**Publish your own directive:**
```
"I want to share my API pattern"
→ publish("my_api_pattern", "1.0.0")
→ Uploads to registry (requires CONTEXT_KIWI_API_KEY)
```

**Get help:**
```
"How does Context Kiwi work?"
→ help("overview")
→ Returns workflow guidance
```

---

## For Developers

### Prerequisites

- Python 3.11+
- pip or uv
- Supabase account (for database)

### Installation

```bash
# Clone the repo
git clone https://github.com/codekiwi/context-kiwi.git
cd context-kiwi

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install with dev dependencies
pip install -e ".[dev]"
```

### Environment Setup

Create a `.env` file:

```bash
# .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key

# Optional
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### Running Locally

**Stdio mode** (for Cursor):
```bash
python -m src.server --stdio
```

**HTTP mode** (for testing):
```bash
python -m src.server --http --port 8000
```

### Connecting Cursor to Local Dev

```json
// ~/.cursor/mcp.json
{
  "mcpServers": {
    "context-kiwi-dev": {
      "command": "/path/to/context-kiwi/.venv/bin/python",
      "args": ["-m", "src.server", "--stdio"],
      "cwd": "/path/to/context-kiwi",
      "env": {
        "PYTHONPATH": "/path/to/context-kiwi"
      }
    }
  }
}
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src

# Specific test
pytest tests/test_tools.py -v
```

### Project Structure

```
context-kiwi/
├── src/
│   ├── server.py          # Entry point
│   ├── db/                # Database layer
│   ├── directives/        # Directive loading
│   ├── tools/             # Meta-tools + directive tools
│   │   ├── core.py        # 3 core meta-tools
│   │   └── directives/    # get, check_updates, publish handlers
│   └── utils/             # Utilities
├── directives/            # Source directive files (for publishing)
│   ├── core/              # bootstrap, initialize_project
│   └── meta/              # bootstrap_check, help_*
├── tests/                 # Test suite
├── docs/                  # Documentation
├── pyproject.toml         # Dependencies
└── Makefile               # Common tasks
```

### Common Tasks

```bash
# Run dev server (stdio)
make dev

# Run HTTP server  
make dev-http

# Run tests
make test

# Type checking
make typecheck

# Format code
make format
```

---

## Database Setup

### Supabase Tables

If setting up a new Supabase project, create these tables:

```sql
-- Directives metadata
CREATE TABLE directives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(20) NOT NULL,
    description TEXT,
    is_official BOOLEAN DEFAULT FALSE,
    download_count INTEGER DEFAULT 0,
    quality_score DECIMAL(3,2) DEFAULT 0.0,
    tech_stack TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- Directive versions (content)
CREATE TABLE directive_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    directive_id UUID REFERENCES directives(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    changelog TEXT,
    is_latest BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(directive_id, version)
);

-- Indexes
CREATE INDEX idx_directives_name ON directives(name);
CREATE INDEX idx_directives_category ON directives(category);
CREATE INDEX idx_directive_versions_latest ON directive_versions(directive_id, is_latest);
```

### Seeding Core Directives

Core directives should be published to the registry. Use the source files in `directives/` folder:

```bash
# Publish bootstrap directive
execute("publish_directive", {
  name: "bootstrap",
  version: "1.0.0",
  content: "<content from directives/core/bootstrap.md>"
})
```

---

## Workflow Overview

### How the 6 Tools Work

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. SEARCH: Find what you need                                   │
│                                                                 │
│    search("jwt auth", "registry", "score")                      │
│    → Returns list of matching directives                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. GET: Download directive from registry                         │
│                                                                 │
│    get("jwt_auth_zustand", to="user")                           │
│    → Downloads directive to local space                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. RUN: Execute the directive                                    │
│                                                                 │
│    run("jwt_auth_zustand", {"refresh_endpoint": "/auth/refresh"})│
│    → Loads directive + project context                          │
│    → Returns directive + context for LLM to follow              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. FOLLOW: LLM executes the directive steps                     │
│                                                                 │
│    - Creates files using LOCAL file access                      │
│    - Runs commands                                              │
│    - Asks clarifying questions                                  │
│    - The MCP server CANNOT do this - the LLM does it            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ HELP: Get guidance when stuck                                   │
│                                                                 │
│    help("run")                                                  │
│    → Explains how to use Context Kiwi                           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Concept

**The MCP server loads directives and context.**
**The LLM follows directive steps using local file access.**

### Common Patterns

**Finding and using a directive:**
```
User: "Help me create an API endpoint"

LLM: 
1. search("create api endpoint", "registry", "score")
   → [{name: "create_api", category: "patterns"}]

2. get("create_api", to="user")
   → Downloads directive to ~/.context-kiwi/directives/core/

3. run("create_api", {"name": "users", "method": "GET"})
   → Loads directive + project context
   → LLM follows steps to create the endpoint
```

**Publishing your own directive:**
```
User: "I want to share my authentication pattern"

LLM:
1. User creates directive file: .ai/directives/custom/my_auth.md

2. publish("my_auth", "1.0.0")
   → Validates directive structure
   → Uploads to registry
   → Others can now find and use it
```

---

## Troubleshooting

### Server Won't Start

**Error: "SUPABASE_URL and SUPABASE_SECRET_KEY must be set"**
- Create `.env` file with Supabase credentials
- Or set environment variables directly
- For publishing: `CONTEXT_KIWI_API_KEY` or `SUPABASE_SECRET_KEY` required

**Error: "Address already in use"**
- Another server is running on the port
- Use `--port` flag to specify different port

### Initialization Issues

**"Directive not found locally"**
- Use `get()` first to download from registry
- Check directive exists: `search("directive_name", "local", "score")`
- Verify project_path if not in workspace root

**"Project not initialized"**
- Run `run("init")` to create `.ai/` structure
- Check `.ai/context.md` exists
- Run `run("context")` to generate project understanding

### Database Connection

**"Database not configured"**
- Check `.env` file has correct Supabase credentials
- Verify Supabase project is accessible
- Check network connectivity

---

## Next Steps

- Read [Architecture](./ARCHITECTURE.md) for technical details
- Read [Permissions](./PERMISSIONS.md) for security model
- Check [Roadmap](./ROADMAP.md) for planned features
