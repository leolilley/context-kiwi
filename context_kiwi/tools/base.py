"""
Base Tool Classes
Abstract base classes for tool implementations.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from context_kiwi.mcp_types import (
    Tool, ToolInput, ToolResult, ToolError, ToolContext,
    ToolHandlerResult, ToolValidationResult, ToolValidationError,
    MCPErrorCode, TextContent, ToolCategory, ToolMetadata
)
from context_kiwi import __version__


class BaseTool(ABC):
    """Abstract base class for all tool implementations."""
    
    def __init__(self, logger, metadata: Optional[Dict[str, Any]] = None):
        self.logger = logger
        
        # Set default metadata values
        default_metadata = {
            'category': ToolCategory.UTILITY,
            'version': __version__,
            'requiresAuth': False,
            'rateLimited': False
        }
        
        # Merge with provided metadata
        if metadata:
            default_metadata.update(metadata)
        
        self.metadata = ToolMetadata(**default_metadata)
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass
    
    @property
    @abstractmethod
    def inputSchema(self) -> Dict[str, Any]:
        """Tool input schema (JSON Schema)."""
        pass
    
    @abstractmethod
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        """Execute the tool with input and context."""
        pass
    
    def validateInput(self, input: ToolInput) -> ToolValidationResult:
        """Validate tool input against schema."""
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = self.inputSchema.get('required', [])
        for field in required_fields:
            if field not in input or input.get(field) is None:
                errors.append(ToolValidationError(
                    field=field,
                    message=f"Required field '{field}' is missing",
                    code="MISSING_REQUIRED_FIELD"
                ))
        
        # Check field types
        properties = self.inputSchema.get('properties', {})
        for field, value in input.items():
            if field in properties:
                field_schema = properties[field]
                expected_type = field_schema.get('type')
                
                if expected_type == 'string' and not isinstance(value, str):
                    errors.append(ToolValidationError(
                        field=field,
                        message=f"Field '{field}' must be a string",
                        code="INVALID_TYPE"
                    ))
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    errors.append(ToolValidationError(
                        field=field,
                        message=f"Field '{field}' must be a number",
                        code="INVALID_TYPE"
                    ))
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    errors.append(ToolValidationError(
                        field=field,
                        message=f"Field '{field}' must be a boolean",
                        code="INVALID_TYPE"
                    ))
                elif expected_type == 'object' and not isinstance(value, dict):
                    errors.append(ToolValidationError(
                        field=field,
                        message=f"Field '{field}' must be an object",
                        code="INVALID_TYPE"
                    ))
        
        return ToolValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def createSuccessResult(self, data: Any) -> ToolResult:
        """Create a successful tool result - follows MCP specification."""
        try:
            if isinstance(data, str):
                text = data
                # Validate JSON if it looks like JSON
                if data.strip().startswith(('{', '[')):
                    try:
                        json.loads(data)
                    except json.JSONDecodeError:
                        text = json.dumps({"message": data}, indent=2)
            else:
                text = json.dumps(data, indent=2, default=str, ensure_ascii=False)
            
            text = text.strip()
            
        except (TypeError, ValueError) as e:
            self.logger.warning(f"Failed to serialize tool result: {e}")
            text = json.dumps({"error": "Failed to serialize result"}, indent=2)
        
        return ToolResult(
            content=[TextContent(type="text", text=text)],
            isError=False
        )
    
    def createErrorResult(self, error_or_code, message: str | None = None) -> ToolResult:
        """Create an error tool result - follows MCP specification.
        
        Can be called as:
            createErrorResult(ToolError(...))
            createErrorResult(code, message)
        """
        if isinstance(error_or_code, ToolError):
            error_message = error_or_code.message
        else:
            # Called with (code, message) - create error message
            error_message = message or str(error_or_code)
        
        return ToolResult(
            content=[TextContent(type="text", text=error_message)],
            isError=True
        )
    
    async def handleError(self, error: Exception, context: ToolContext) -> ToolHandlerResult:
        """Handle errors during tool execution."""
        self.logger.error(f"Tool execution error: {error}")
        
        return ToolHandlerResult(
            success=False,
            error=ToolError(
                code=MCPErrorCode.TOOL_EXECUTION_ERROR,
                message=str(error),
                details=str(error)
            )
        )
    
    def logExecution(self, input: ToolInput, context: ToolContext, success: bool):
        """Log tool execution."""
        self.logger.debug(f"Tool executed: {self.name}", extra={
            'tool': self.name,
            'success': success,
            'userId': context.userId,
            'requestId': context.requestId
        })
    
    def getCurrentTimestamp(self) -> str:
        """Get current timestamp for database storage."""
        return datetime.now(timezone.utc).isoformat()

