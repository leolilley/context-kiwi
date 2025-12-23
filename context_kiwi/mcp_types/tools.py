"""
Tool-related types
Types specific to tool implementations - follows MCP specification.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum


class ToolCategory(Enum):
    """Tool categories for organization."""
    CORE = "core"           # Core meta-tools (search_directive, load_directive, execute, help)
    DIRECTIVE = "directive" # Directive management
    COMPONENT = "component" # Component generation
    PATTERN = "pattern"     # Pattern management
    PROJECT = "project"     # Project setup
    UTILITY = "utility"     # Utilities


class MCPErrorCode(Enum):
    """MCP Error codes - follows MCP specification."""
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    INVALID_INPUT = "INVALID_INPUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_PARAMS = "INVALID_PARAMS"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"


@dataclass
class TextContent:
    """Text content for tool results - follows MCP specification."""
    type: str
    text: str


@dataclass
class ToolInput(dict):
    """Tool input data - behaves like a dict for compatibility."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def get(self, key: str, default=None):
        return super().get(key, default)


@dataclass
class ToolContext:
    """Tool execution context."""
    userId: str
    requestId: str
    permissions: List[str]
    accessLevel: str
    timestamp: float
    toolName: Optional[str] = None


@dataclass
class ToolResult:
    """Tool execution result - follows MCP specification."""
    content: List[TextContent]
    isError: bool = False


@dataclass
class ToolError:
    """Tool error information."""
    code: MCPErrorCode
    message: str
    details: Optional[str] = None


@dataclass
class ToolHandlerResult:
    """Tool handler result."""
    success: bool
    result: Optional[ToolResult] = None
    error: Optional[ToolError] = None


@dataclass
class Tool:
    """MCP Tool definition - follows MCP specification."""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    title: Optional[str] = None
    outputSchema: Optional[Dict[str, Any]] = None
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class ToolMetadata:
    """Tool metadata."""
    category: ToolCategory
    version: str
    requiresAuth: bool = False
    rateLimited: bool = False
    description: Optional[str] = None


@dataclass
class ToolValidationError:
    """Tool validation error."""
    field: str
    message: str
    code: str


@dataclass
class ToolValidationResult:
    """Tool validation result."""
    valid: bool
    errors: List[ToolValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ToolExecution:
    """Tool execution record."""
    id: str
    toolName: str
    input: Dict[str, Any]
    context: ToolContext
    startTime: str
    status: str
    endTime: Optional[str] = None
    duration: Optional[int] = None
    result: Optional[ToolResult] = None
    error: Optional[ToolError] = None


@dataclass
class ToolExecutionResult:
    """Tool execution result."""
    execution: ToolExecution
    success: bool
    result: Optional[ToolResult] = None
    error: Optional[ToolError] = None


@dataclass
class ToolCapabilities:
    """Tool capabilities."""
    tools: List[Any]
    count: int
    categories: List[str]
    permissions: List[str]


@dataclass
class ToolRateLimit:
    """Tool rate limiting."""
    toolName: str
    maxRequests: int
    windowMs: int
    currentRequests: int
    resetTime: float


@dataclass
class ToolMetrics:
    """Tool execution metrics."""
    toolName: str
    totalExecutions: int
    successfulExecutions: int
    failedExecutions: int
    averageExecutionTime: float
    errorRate: float
    lastExecutionTime: Optional[str] = None


class ToolCache:
    """Tool cache interface."""
    
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    def set(self, key: str, value: Any, ttl: int = 300000) -> None:
        raise NotImplementedError
    
    def delete(self, key: str) -> bool:
        raise NotImplementedError
    
    def clear(self) -> None:
        raise NotImplementedError
    
    def has(self, key: str) -> bool:
        raise NotImplementedError


class ToolMonitoring:
    """Tool monitoring interface."""
    
    def recordExecution(self, execution: ToolExecution) -> None:
        raise NotImplementedError
    
    def getMetrics(self, toolName: str) -> ToolMetrics:
        raise NotImplementedError
    
    def getAllMetrics(self) -> Dict[str, ToolMetrics]:
        raise NotImplementedError
    
    def resetMetrics(self, toolName: Optional[str] = None) -> None:
        raise NotImplementedError


# Type alias for tool handlers
ToolHandler = Callable[[Dict[str, Any], ToolContext], Awaitable[ToolHandlerResult]]

