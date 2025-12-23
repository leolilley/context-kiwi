# Context Meta-Directive: Implementation Summary

## Quick Overview

Transform project context from **static manual file** (`tech_stack.md`) to **auto-generated comprehensive documentation** (`project_context.md`) via a meta-directive (`context.md`).

## Key Concept

**Meta-Directive Pattern:**
- `context.md` = **Instructions** (how to analyze)
- `project_context.md` = **Results** (what was analyzed)

The directive teaches the LLM how to understand any project, then generates documentation automatically.

## Implementation Checklist

### Phase 1: Core Directive ✅
- [ ] Create `.ai/directives/core/context.md`
  - [ ] Define analysis steps (scan, analyze, extract, generate)
  - [ ] Include template for `project_context.md` structure
  - [ ] Add integration with existing `.ai/patterns/`
  - [ ] Test directive XML structure

### Phase 2: Context Loading ✅
- [ ] Update `context_kiwi/execution/context.py`
  - [ ] Add `load_project_context()` function
  - [ ] Update `load_context()` to prefer `project_context.md`
  - [ ] Implement fallback to `tech_stack.md` (backward compat)
  - [ ] Test with both files present
  - [ ] Test with only `tech_stack.md` (legacy)
  - [ ] Test with only `project_context.md` (new)

### Phase 3: Init Integration ✅
- [ ] Update `.ai/directives/core/init.md`
  - [ ] Remove direct `tech_stack.md` creation
  - [ ] Add suggestion to run `context` directive
  - [ ] Keep `tech_stack.md` as optional/legacy
  - [ ] Test init flow on new project
  - [ ] Test init flow on existing project

### Phase 4: Documentation ✅
- [ ] Update `README.md`
  - [ ] Update "Where Things Live" section
  - [ ] Add `context.md` and `project_context.md` to structure
  - [ ] Update examples to show `run("context")`
- [ ] Update `.ai/directives/core/help_context.md`
  - [ ] Document new context system
  - [ ] Explain meta-directive pattern
  - [ ] Show migration path
- [ ] Create migration guide (if needed)

### Phase 5: Testing ✅
- [ ] Test with new project (no context files)
- [ ] Test with existing project (has `tech_stack.md`)
- [ ] Test `run("context")` generates `project_context.md`
- [ ] Test `load_context()` prefers `project_context.md`
- [ ] Test backward compatibility
- [ ] Test specialized inits (e.g., `init_python_mcp`) still work

## Files to Modify

### Must Modify
1. **`context_kiwi/execution/context.py`**
   - Add `project_context.md` loading
   - Update `load_context()` priority

2. **`.ai/directives/core/init.md`**
   - Update to suggest `context` directive
   - Remove direct `tech_stack.md` creation

3. **`README.md`**
   - Update documentation structure
   - Add `context` directive usage

### Create New
1. **`.ai/directives/core/context.md`**
   - Meta-directive for context generation

### May Need Updates (Review)
- `.ai/directives/core/help_context.md` - Update context documentation
- `.ai/directives/core/init_python_mcp.md` - May reference `tech_stack.md`
- Other specialized init directives - Check for `tech_stack.md` references

## Design Decisions

### ✅ Decision: Core Directive Location
**Answer:** `~/.context-kiwi/directives/core/context.md`
- Reusable across all projects
- Shared improvements benefit everyone
- Follows existing core directive pattern

### ✅ Decision: Backward Compatibility
**Answer:** Keep `tech_stack.md` support
- `load_context()` checks `project_context.md` first
- Falls back to `tech_stack.md` if not found
- Both can coexist during transition
- No breaking changes

### ✅ Decision: Auto-Generation
**Answer:** User explicitly runs `run("context")`
- `init` suggests it, doesn't run it
- User controls when to generate/update
- Can be run anytime to refresh

### ✅ Decision: File Overwrite
**Answer:** `project_context.md` is auto-generated
- Overwrite on each run (it's generated, not edited)
- User shouldn't manually edit it
- If customization needed, extend the directive

### ✅ Decision: Git Tracking
**Answer:** Commit `project_context.md`
- It's documentation (like `tech_stack.md`)
- Helps team understand project
- Can be regenerated if needed

## Migration Path

### For Existing Projects
1. Project has `.ai/tech_stack.md` (manual)
2. Run `run("context")` → Generates `.ai/project_context.md`
3. Both files coexist
4. `load_context()` uses `project_context.md` (preferred)
5. Eventually remove `tech_stack.md` (optional, future)

### For New Projects
1. Run `run("init")` → Creates structure
2. Run `run("context")` → Generates `project_context.md`
3. No `tech_stack.md` needed

## Success Metrics

- [ ] `run("context")` successfully generates `project_context.md`
- [ ] Generated context is comprehensive (more than just tech stack)
- [ ] Existing projects continue working (backward compat)
- [ ] `load_context()` correctly prioritizes files
- [ ] Documentation is updated and clear
- [ ] No breaking changes to existing workflows

## Open Questions (Resolved)

1. ✅ **Where should `context.md` live?**
   - **Answer:** Core directive in `~/.context-kiwi/directives/core/`

2. ✅ **Should `tech_stack.md` be deprecated immediately?**
   - **Answer:** No, keep for backward compatibility

3. ✅ **Should `context` run automatically in `init`?**
   - **Answer:** No, make it explicit (user runs it)

4. ✅ **What if `project_context.md` already exists?**
   - **Answer:** Overwrite it (it's auto-generated)

5. ✅ **Should `project_context.md` be gitignored?**
   - **Answer:** No, commit it (it's documentation)

## Example `project_context.md` Structure

```markdown
# Project Context: [Auto-detected Name]

## Identity
- Name: [Auto-detected from package.json, pyproject.toml, etc.]
- Type: [Web/API/Library/etc - auto-detected]
- Description: [Generated from README/code analysis]

## Technology Stack
[Auto-detected from package.json, requirements.txt, etc.]
- Languages
- Frameworks
- Libraries
- Tools

## Dependencies & Environment
[Auto-detected from lockfiles, env files]
- Runtime dependencies
- Dev dependencies
- Environment variables
- Build tools

## Project Structure
[Auto-generated directory tree]
- Key directories
- File organization
- Entry points

## Conventions & Patterns
[Auto-detected from code analysis]
- File naming conventions
- Code style
- Component patterns
- API patterns
- Error handling

## Development Workflow
[Auto-detected from package.json scripts, Makefile, etc.]
- Build commands
- Test commands
- Dev commands
- Deployment

## Context Kiwi Integration
[Auto-generated based on .ai/ contents]
- Available patterns
- Custom directives
- Exported contexts
```

## Next Steps

1. **Review scope documents** (this file + ARCHITECTURE.md + SCOPE.md)
2. **Create `context.md` directive** (start with core directive)
3. **Update context loading** (implement file priority)
4. **Update init directive** (remove direct tech_stack creation)
5. **Test thoroughly** (new + existing projects)
6. **Update documentation** (README + help directives)

## Related Documents

- `docs/CONTEXT_META_DIRECTIVE_SCOPE.md` - Detailed implementation scope
- `docs/CONTEXT_META_DIRECTIVE_ARCHITECTURE.md` - Architecture diagrams and flows
- `docs/CONTEXT_META_DIRECTIVE_SUMMARY.md` - This file (quick reference)
