# Context Kiwi: Permissions & Safety System

## Overview

Context Kiwi uses a **declarative permissions model** where directives explicitly state what access they need. Since the MCP server cannot write to local files, all file operations are performed by the LLM following directive instructions.

**Key Principle:** Transparency through declaration. Users can always see what a directive intends to do before execution.

---

## How Permissions Work

### The Trust Model

```
┌─────────────────────────────────────────────────────────────────┐
│   Supabase Database                                             │
│   • Stores directive content                                    │
│   • Managed by Context Kiwi team                                   │
│   • Official directives reviewed before publishing              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│   MCP Server (Context Kiwi)                                        │
│   • Read-only access to Supabase                                │
│   • Returns directive content to LLM                            │
│   • CANNOT write to user's filesystem                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│   LLM (Cursor/Claude)                                           │
│   • Receives directive with permissions declaration             │
│   • Should inform user of required permissions                  │
│   • Executes steps using local file access                      │
│   • User can observe all actions in IDE                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│   User's Filesystem                                             │
│   • Files created/modified by LLM                               │
│   • User has full visibility                                    │
│   • Can be reviewed via git diff                                │
└─────────────────────────────────────────────────────────────────┘
```

### Permission Declaration in Directives

Each directive includes a `<permissions>` block:

```xml
<permissions>
  <filesystem>
    <read paths="package.json, src/**/*.ts" />
    <write paths=".ai/**, src/components/**" />
  </filesystem>
  <shell>
    <command pattern="npm install *" />
    <command pattern="mkdir -p *" />
  </shell>
  <network>
    <fetch hosts="api.anthropic.com" reason="Vision API" />
  </network>
</permissions>
```

---

## Permission Types

### Filesystem Permissions

| Permission | Scope | Description |
|------------|-------|-------------|
| `read` | Paths | Read files for context |
| `write` | Paths | Create or modify files |
| `delete` | Paths | Remove files (rarely used) |

**Path patterns:**
- `package.json` - Specific file
- `src/**` - Directory and all subdirectories
- `*.config.*` - Glob pattern
- `~/.context-kiwi/**` - Home directory paths

### Shell Permissions

```xml
<shell>
  <command pattern="npm install *" reason="Install dependencies" />
  <command pattern="mkdir -p .ai/*" reason="Create directories" />
</shell>
```

### Network Permissions

```xml
<network>
  <fetch hosts="api.anthropic.com" reason="Vision API for pattern extraction" />
</network>
```

### Environment Permissions

```xml
<environment>
  <variable name="ANTHROPIC_API_KEY" access="read" reason="API authentication" />
</environment>
```

---

## Scope Constraints

Permissions are scoped to prevent overreach:

| Scope | Description | Example |
|-------|-------------|---------|
| `project` | Within project root only | `.ai/**`, `src/**` |
| `home` | Within user's home directory | `~/.context-kiwi/**` |
| `codekiwi` | Within Context Kiwi config only | `~/.context-kiwi/**` |

**Blocked patterns:**
- System paths (`/etc/**`, `/usr/**`)
- Other users' directories
- Sensitive files (`.ssh/**`, credentials)

---

## Example: Bootstrap Directive Permissions

```xml
<directive name="bootstrap" version="1.0.0">
  <permissions>
    <filesystem>
      <read paths="~/.context-kiwi/**" reason="Check if already set up" />
      <write paths="~/.context-kiwi/**" reason="Create config directory" />
    </filesystem>
    <shell>
      <command pattern="mkdir -p ~/.context-kiwi/*" />
    </shell>
  </permissions>
  
  <process>
    <step name="check">
      Check if ~/.context-kiwi/config.yaml exists
    </step>
    <step name="create">
      Create ~/.context-kiwi/ directory structure:
      - ~/.context-kiwi/config.yaml
      - ~/.context-kiwi/lock.yaml
      - ~/.context-kiwi/cache/
    </step>
    <step name="verify">
      Verify setup is complete
    </step>
  </process>
</directive>
```

---

## How the LLM Should Handle Permissions

### Before Execution

The LLM should:

1. **Parse the permissions block** from the directive
2. **Inform the user** what access is needed
3. **Wait for confirmation** if sensitive operations

Example LLM response:
```
This directive needs to:
📁 READ: package.json, src/**
📝 WRITE: .ai/**
🖥️ RUN: mkdir -p .ai/patterns

Proceed? (yes/no)
```

### During Execution

The LLM should:
- **Stay within declared permissions**
- **Not access files outside the scope**
- **Report what was actually done**

### After Execution

The LLM should:
- **Summarize actions taken**
- **Report any errors**
- **Suggest next steps**

---

## Safety Features

### 1. Transparency

All directives are visible in Supabase. Anyone can review:
- What permissions a directive requests
- What steps it will execute
- Historical versions and changes

### 2. Scoped Access

Directives can only request access to:
- Project directories
- Context Kiwi config (`~/.context-kiwi/`)
- Explicitly named files

### 3. User Observation

The LLM executes in the user's IDE where:
- All file changes are visible
- Terminal commands are shown
- Git can track modifications

### 4. No Server-Side Execution

The MCP server:
- **Cannot** execute shell commands
- **Cannot** write files
- **Cannot** make HTTP requests on behalf of the user

All execution happens client-side via the LLM.

---

## Permission Presets (Future)

Common permission combinations as reusable presets:

| Preset | Includes |
|--------|----------|
| `readonly` | Read project files only |
| `project_init` | Create `.ai/`, read project files |
| `component_gen` | Read `.ai/`, write to `src/components/` |
| `full_codegen` | Read/write within project root |

Usage in directive:
```xml
<permissions preset="project_init">
  <!-- Additional permissions beyond preset -->
  <shell>
    <command pattern="npm list" />
  </shell>
</permissions>
```

---

## Community Directives

### Trust Levels

| Level | Description | Review Process |
|-------|-------------|----------------|
| **Official** | Created by Context Kiwi team | Thoroughly reviewed |
| **Verified** | Community, reviewed | Basic security check |
| **Community** | User-submitted | Use with caution |

### Quality Indicators

When browsing directives, look for:
- `is_official: true` - Team-maintained
- `quality_score` - Based on success rate
- `download_count` - Usage popularity

---

## Reporting Issues

If you find a directive with:
- Overly broad permissions
- Suspicious behavior
- Security concerns

Report via:
1. GitHub Issues
2. Discord (when available)
3. Email: security@codekiwi.dev

---

## Best Practices for Directive Authors

### Do:
- Request **minimum necessary** permissions
- Provide **clear reasons** for each permission
- Scope paths as **narrowly as possible**
- Document **what the directive does**

### Don't:
- Request `**/**` (all files)
- Require shell access without justification
- Access user credentials or secrets
- Modify files outside project scope

### Example of Good Permissions

```xml
<!-- Good: Specific and minimal -->
<permissions>
  <filesystem>
    <read paths="package.json" reason="Detect framework" />
    <read paths="src/components/**" reason="Analyze existing components" />
    <write paths="src/components/Button.tsx" reason="Create component" />
  </filesystem>
</permissions>
```

### Example of Bad Permissions

```xml
<!-- Bad: Too broad -->
<permissions>
  <filesystem>
    <read paths="**/*" />
    <write paths="**/*" />
  </filesystem>
  <shell>
    <command pattern="*" />
  </shell>
</permissions>
```

---

## Related Documentation

- [Architecture](./ARCHITECTURE.md) - System design
- [Getting Started](./GETTING_STARTED.md) - Setup guide
- [Roadmap](./ROADMAP.md) - Planned security features

