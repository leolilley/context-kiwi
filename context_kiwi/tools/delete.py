"""
Delete Tool

Delete directives from registry, user space, or project space.
"""

from pathlib import Path
from typing import Any

from context_kiwi.mcp_types import (
    MCPErrorCode,
    ToolCategory,
    ToolContext,
    ToolError,
    ToolHandlerResult,
    ToolInput,
)
from context_kiwi.tools.base import BaseTool
from context_kiwi.tools.directives.delete import delete_directive_handler
from context_kiwi.utils import Logger


class DeleteTool(BaseTool):
    """
    Delete a directive from registry, user space, project space, or all tiers.
    """
    
    def __init__(self, logger: Logger):
        super().__init__(logger, {
            'category': ToolCategory.CORE,
            'requiresAuth': False,
            'rateLimited': False
        })
    
    @property
    def name(self) -> str:
        return "delete"
    
    @property
    def description(self) -> str:
        return """Delete a directive from registry, user space, project space, or all.

REQUIRED: name (directive name), confirm=True (safety check)
OPTIONAL: from ("registry"|"user"|"project"|"all"), project_path

Examples:
- delete("my_directive", confirm=True, from="registry") - Delete from registry only
- delete("my_directive", confirm=True, from="all") - Delete everywhere
- delete("my_directive", confirm=True, from="project", project_path="/path/to/project")

IMPORTANT: Always set confirm=True. This prevents accidental deletions.

Common mistake: Forgetting confirm=True (will fail) or using wrong "from" value."""
    
    @property
    def inputSchema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "REQUIRED: Directive name to delete"
                },
                "from": {
                    "type": "string",
                    "enum": ["registry", "user", "project", "all"],
                    "default": "registry",
                    "description": "Where to delete: 'registry' (default), 'user', 'project', or 'all' (all locations)"
                },
                "cleanup_empty_dirs": {
                    "type": "boolean",
                    "default": False,
                    "description": "Remove empty folders after deletion (default: false)"
                },
                "confirm": {
                    "type": "boolean",
                    "default": False,
                    "description": "REQUIRED: Must be true to confirm deletion (safety check)"
                },
                "project_path": {
                    "type": "string",
                    "description": "CRITICAL: Project root path if workspace != current directory. Example: '/home/user/myproject'. Defaults to current working directory."
                }
            },
            "required": ["name"]
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        """Execute delete."""
        name = input.get("name")
        from_tier = input.get("from", "registry")
        cleanup_empty_dirs = input.get("cleanup_empty_dirs", False)
        project_path = input.get("project_path")
        
        if not name:
            error = ToolError(
                code=MCPErrorCode.INVALID_INPUT,
                message="Directive name is required"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error)
            )
        
        try:
            # Call the delete handler
            result = await delete_directive_handler(
                {
                    "name": name,
                    "from": from_tier,
                    "cleanup_empty_dirs": cleanup_empty_dirs,
                    "project_path": project_path
                },
                context
            )
            
            # Transform result to ToolHandlerResult
            if result.get("status") == "error":
                error = ToolError(
                    code=MCPErrorCode.TOOL_EXECUTION_ERROR,
                    message=result.get("message", "Delete failed")
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            else:
                return ToolHandlerResult(
                    success=True,
                    result=self.createSuccessResult(result)
                )
        except Exception as e:
            error = ToolError(
                code=MCPErrorCode.TOOL_EXECUTION_ERROR,
                message=f"Delete failed: {str(e)}"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error)
            )

