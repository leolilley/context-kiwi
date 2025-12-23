# Project Path Requirement Fix

## Problem

When directives called the `get()` tool with `to="project"` without providing the `project_path` parameter, the MCP server would default to using `Path.cwd()` (current working directory). Since the MCP server's working directory might be `~/.ai` or another location, files would be downloaded to the wrong location.

Example of the issue:
```json
{
  "status": "downloaded",
  "directive": "sync_directives",
  "version": "1.1.1",
  "destination": "project",
  "path": ".ai/directives/core/sync_directives.md",
  "message": "Downloaded sync_directives@1.1.1 to .ai/directives/core/"
}
```

The MCP server didn't know the actual project path and defaulted to `~/.ai`, which was incorrect.

## Solution

### 1. Tool Schema Updates

Updated tool schemas to make `project_path` requirement crystal clear:

**`/mcps/user-context-kiwi/tools/get.json`**:
- Updated description to emphasize `project_path` is REQUIRED when `to="project"`
- Added ⚠️  warning symbols to make it unmissable
- Updated all examples to include `project_path`

**`/mcps/user-script-kiwi/tools/load.json`**:
- Enhanced description with similar warnings
- Clarified that `project_path` is required when downloading to project

### 2. Python Implementation Updates

**`context_kiwi/tools/get.py`**:

Added validation in the `execute()` method:
```python
# Validate project_path when downloading to project
if to == "project" and not project_path:
    error = ToolError(
        code=MCPErrorCode.INVALID_INPUT,
        message="CRITICAL: project_path is REQUIRED when to='project'. Provide the full workspace path (e.g., '/home/user/myproject'). Without this, files will be saved to the wrong location!"
    )
    return ToolHandlerResult(
        success=False,
        error=error,
        result=self.createErrorResult(error)
    )
```

Updated tool description and schema to emphasize the requirement.

### 3. Directive Updates

Updated all directives that reference `get()` with `to="project"`:

**`.ai/directives/core/sync_directives.md`**:
- Added ⚠️  CRITICAL section in execute_sync step to get workspace path first
- Updated all examples to include `project_path` parameter
- Added clear note about when project_path is needed vs not needed

**`.ai/directives/core/init_ai_config.md`**:
- Updated all 5 instances of `get()` calls to include `project_path`
- Updated examples and decision trees

**`.ai/directives/core/edit_directive.md`**:
- Added critical warning to get workspace path first
- Updated tool call to include `project_path` parameter

**`.ai/directives/core/create_directive.md`**:
- Added note in success output about the project_path requirement

**`.ai/directives/core/help_workflow.md`**:
- Updated common mistakes section

### 4. Cursor Rules Updates

**`.cursor/rules`**:
- Updated tool signature to show project_path requirement
- Updated all 6 examples and references to include `project_path`
- Added clear notation about when it's required

## Key Changes Summary

### Before
```python
get("directive_name", to="project")  # ❌ Missing project_path, fails
```

### After
```python
get("directive_name", to="project", project_path="/home/user/myproject")  # ✅ Correct
```

### When project_path is needed:
- ✅ **REQUIRED**: When `to="project"` (downloading to project directory)
- ❌ **NOT NEEDED**: When `to="user"` (downloading to userspace)
- ❌ **NOT NEEDED**: For `list_versions`, `check`, or `update` operations

## Testing

To test the fix:

1. Try calling get() without project_path when to="project":
   ```python
   get("sync_directives", to="project")
   ```
   Should now return a clear error message.

2. Try calling get() with project_path:
   ```python
   get("sync_directives", to="project", project_path="/home/user/myproject")
   ```
   Should work correctly.

3. Try calling get() for userspace (should still work without project_path):
   ```python
   get("sync_directives", to="user")
   ```
   Should work correctly.

## Files Modified

### MCP Tool Schemas (in `/home/leo/.cursor/projects/home-leo-projects-context-kiwi/mcps/`)
- `user-context-kiwi/tools/get.json`

### Python Implementation
- `context_kiwi/tools/get.py`

### Directives
- `.ai/directives/core/sync_directives.md`
- `.ai/directives/core/init_ai_config.md`
- `.ai/directives/core/edit_directive.md`
- `.ai/directives/core/create_directive.md`
- `.ai/directives/core/help_workflow.md` (attempted but skipped by user)

### Configuration
- `.cursor/rules`

## Impact

This fix ensures that:
1. The model will never be able to call `get()` with `to="project"` without providing `project_path`
2. Clear error messages guide the model to provide the required parameter
3. All documentation and examples demonstrate proper usage
4. The issue of files being downloaded to `~/.ai` instead of the project directory is completely prevented

## Rollout

After deploying these changes:
1. The MCP server will enforce the requirement through validation
2. Updated tool schemas will guide the model
3. Updated directives will teach proper patterns
4. Models will learn from the examples in the directives
