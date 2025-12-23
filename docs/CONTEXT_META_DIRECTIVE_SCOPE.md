# Context Meta-Directive Implementation Scope

## Overview

Transform `context.md` from a static document into a **meta-directive** that automatically generates `project_context.md` by analyzing the codebase. This makes project context documentation self-updating and comprehensive.

## Current State

### Files & Structure
- `.ai/tech_stack.md` - Manually maintained project context
- `context_kiwi/execution/context.py` - Loads `tech_stack.md` and patterns
- `.ai/directives/core/init.md` - Creates `.ai/` structure and `tech_stack.md`

### Current Flow
```
run("init")
  → Creates .ai/tech_stack.md (static, manual)
  → Creates .ai/patterns/
  → Creates .ai/directives/custom/
```

## Target State

### New Files & Structure
- `context.md` (root) - **Meta-directive** that analyzes project
- `.ai/project_context.md` - **Auto-generated** comprehensive context documentation
- `.ai/tech_stack.md` - **Optional** (backward compatibility, can be deprecated later)

### New Flow
```
run("init")
  → Creates .ai/ structure
  → Creates context.md (meta-directive) in project root
  → Suggests: run("context") to generate project_context.md

run("context")
  → Analyzes codebase
  → Generates .ai/project_context.md
  → Updates existing project_context.md if present
```

## Implementation Tasks

### 1. Create `context.md` Meta-Directive

**Location:** `.ai/directives/core/context.md`

**Purpose:** Directive that instructs LLM how to analyze a project and generate comprehensive context documentation.

**Key Features:**
- Analyzes codebase structure
- Detects technology stack from dependency files
- Extracts coding patterns and conventions
- Identifies project structure and organization
- Generates `project_context.md` with all findings

**Structure:**
```xml
<directive name="context" version="1.0.0">
  <metadata>
    <description>Meta-directive that analyzes project and generates comprehensive context documentation</description>
    <category>core</category>
  </metadata>
  
  <process>
    <step name="scan_codebase">...</step>
    <step name="analyze_structure">...</step>
    <step name="extract_patterns">...</step>
    <step name="generate_documentation">...</step>
    <step name="integrate_context_kiwi">...</step>
  </process>
</directive>
```

**Dependencies:**
- Must work on projects with or without `.ai/` directory
- Should reference existing `.ai/patterns/` if present
- Should integrate with existing `tech_stack.md` if present

### 2. Update Context Loading System

**File:** `context_kiwi/execution/context.py`

**Changes:**
- Add `load_project_context()` function to load `project_context.md`
- Update `load_context()` to prefer `project_context.md` over `tech_stack.md`
- Maintain backward compatibility: if `project_context.md` doesn't exist, fall back to `tech_stack.md`
- Add helper to check if `project_context.md` exists

**New Function Signature:**
```python
def load_project_context(project_path: Path | None = None) -> str | None:
    """Load project_context.md if it exists."""
    
def load_context(project_path: Path | None = None) -> Dict[str, Any]:
    """
    Load project context from .ai/ directory.
    
    Priority:
    1. project_context.md (auto-generated, comprehensive)
    2. tech_stack.md (legacy, manual)
    
    Returns:
        {
            "project_context": str,    # Contents of project_context.md (if exists)
            "tech_stack": str,         # Contents of tech_stack.md (if exists, fallback)
            "design_system": str,       # Optional
            "patterns": {...}          # All patterns
        }
    """
```

### 3. Update `init` Directive

**File:** `.ai/directives/core/init.md`

**Changes:**
- Remove direct creation of `tech_stack.md`
- Add step to create `context.md` in project root (or `.ai/context.md`?)
- Update final step to suggest running `context` directive
- Keep `tech_stack.md` creation as optional/legacy for backward compatibility

**New Flow:**
```xml
<step name="create_structure">
  <action>
    Create:
      .ai/
      ├── patterns/
      └── directives/custom/
    
    Create in project root:
      context.md  ← Meta-directive for context generation
  </action>
</step>

<step name="suggest_context_generation">
  <action>
    Suggest: "Run run('context') to generate project_context.md"
  </action>
</step>
```

**Decision Needed:** Where should `context.md` live?
- **Option A:** Project root (`/context.md`) - More discoverable, but clutters root
- **Option B:** `.ai/context.md` - Keeps all Context Kiwi files together
- **Option C:** `~/.context-kiwi/directives/core/context.md` - Core directive, shared across projects

**Recommendation:** Option C (core directive) - It's a reusable directive, not project-specific.

### 4. Update Documentation

**Files to Update:**
- `README.md` - Update "Where Things Live" section
- `.ai/directives/core/help_context.md` - Document new context system
- Create migration guide for existing projects

**Documentation Updates:**
- Explain `context.md` is a meta-directive
- Show `project_context.md` is auto-generated
- Explain backward compatibility with `tech_stack.md`
- Update examples to show `run("context")` usage

### 5. Backward Compatibility

**Requirements:**
- Projects with existing `tech_stack.md` should continue working
- `load_context()` should handle both files gracefully
- Migration path: existing projects can run `context` directive to generate `project_context.md`

**Strategy:**
- `load_context()` checks for `project_context.md` first
- Falls back to `tech_stack.md` if `project_context.md` doesn't exist
- Both can coexist during transition period
- Eventually deprecate `tech_stack.md` (future work)

### 6. Integration Points

**Files That Reference `tech_stack.md`:**
- `context_kiwi/execution/context.py` - ✅ Already identified
- `context_kiwi/tools/run.py` - Uses `load_context()`, should work automatically
- Any directives that reference tech stack - Should work with new system

**Testing:**
- Test with existing project (has `tech_stack.md`)
- Test with new project (no context files)
- Test `run("context")` generates `project_context.md`
- Test `load_context()` prefers `project_context.md` over `tech_stack.md`

## File Structure After Implementation

```
project/
├── context.md                    # Meta-directive (if in root, or in .ai/)
├── .ai/
│   ├── project_context.md       # Auto-generated (comprehensive)
│   ├── tech_stack.md            # Legacy (optional, for backward compat)
│   ├── patterns/
│   └── directives/
│       └── custom/
└── [project files]

~/.context-kiwi/
└── directives/core/
    └── context.md               # Core directive (shared)
```

## Implementation Order

1. **Create `context.md` directive** (`.ai/directives/core/context.md`)
   - Write comprehensive directive with all analysis steps
   - Test directive structure and XML validity

2. **Update `load_context()` function**
   - Add `project_context.md` loading
   - Implement fallback to `tech_stack.md`
   - Test backward compatibility

3. **Update `init` directive**
   - Remove direct `tech_stack.md` creation
   - Add suggestion to run `context` directive
   - Test init flow

4. **Update documentation**
   - README updates
   - Help directive updates
   - Migration guide

5. **Testing & Validation**
   - Test with existing projects
   - Test with new projects
   - Verify backward compatibility
   - Test context generation quality

## Open Questions

1. **Where should `context.md` live?**
   - Core directive (shared) vs project-specific?
   - Recommendation: Core directive in `~/.context-kiwi/directives/core/`

2. **Should `tech_stack.md` be deprecated immediately?**
   - Recommendation: No, keep for backward compatibility, deprecate in future version

3. **Should `context` directive be run automatically by `init`?**
   - Recommendation: No, make it explicit (`init` suggests it, user runs it)

4. **What if `project_context.md` already exists?**
   - Recommendation: Overwrite/update it (it's auto-generated, user shouldn't edit manually)

5. **Should `project_context.md` be gitignored?**
   - Recommendation: No, it's documentation that should be committed (like `tech_stack.md`)

## Success Criteria

- [ ] `context.md` directive exists and can be run
- [ ] `run("context")` generates comprehensive `project_context.md`
- [ ] `load_context()` prefers `project_context.md` over `tech_stack.md`
- [ ] Existing projects with `tech_stack.md` continue working
- [ ] `init` directive creates `context.md` or suggests running it
- [ ] Documentation updated to reflect new system
- [ ] Backward compatibility maintained

## Future Enhancements (Out of Scope)

- Auto-run `context` directive on project changes (file watcher)
- Incremental updates to `project_context.md` (only update changed sections)
- Custom analysis plugins for specific project types
- Integration with CI/CD to keep context updated
- Deprecation of `tech_stack.md` (future version)
