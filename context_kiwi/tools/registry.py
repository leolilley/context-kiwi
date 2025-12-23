"""
Tool Registry
Manages tool registration, discovery, and execution.
"""

import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from context_kiwi.mcp_types import (
    ToolHandler, ToolContext, ToolResult, ToolError,
    ToolExecution, ToolExecutionResult, MCPErrorCode, TextContent,
    ToolCapabilities, ToolRateLimit, ToolMetrics, ToolCache, ToolMonitoring
)
from mcp.types import Tool as MCPTool
from context_kiwi.tools.base import BaseTool


class MapToolCache(ToolCache):
    """Simple Map-based Tool Cache Implementation."""
    
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 300000) -> None:
        self.cache[key] = value
    
    def delete(self, key: str) -> bool:
        return self.cache.pop(key, None) is not None
    
    def clear(self) -> None:
        self.cache.clear()
    
    def has(self, key: str) -> bool:
        return key in self.cache


class MapToolMonitoring(ToolMonitoring):
    """Simple Map-based Tool Monitoring Implementation."""
    
    def __init__(self):
        self.metrics = {}
    
    def recordExecution(self, execution: ToolExecution) -> None:
        existing = self.metrics.get(execution.toolName) or ToolMetrics(
            toolName=execution.toolName,
            totalExecutions=0,
            successfulExecutions=0,
            failedExecutions=0,
            averageExecutionTime=0,
            errorRate=0
        )
        
        existing.totalExecutions += 1
        existing.lastExecutionTime = execution.startTime
        
        if execution.status == 'completed' and execution.result:
            existing.successfulExecutions += 1
        elif execution.status == 'failed':
            existing.failedExecutions += 1
        
        if execution.duration:
            total_time = existing.averageExecutionTime * (existing.totalExecutions - 1) + execution.duration
            existing.averageExecutionTime = total_time / existing.totalExecutions
        
        existing.errorRate = existing.failedExecutions / existing.totalExecutions if existing.totalExecutions > 0 else 0
        
        self.metrics[execution.toolName] = existing
    
    def getMetrics(self, toolName: str) -> ToolMetrics:
        return self.metrics.get(toolName) or ToolMetrics(
            toolName=toolName,
            totalExecutions=0,
            successfulExecutions=0,
            failedExecutions=0,
            averageExecutionTime=0,
            errorRate=0
        )
    
    def getAllMetrics(self) -> Dict[str, ToolMetrics]:
        return dict(self.metrics)
    
    def resetMetrics(self, toolName: Optional[str] = None) -> None:
        if toolName:
            self.metrics.pop(toolName, None)
        else:
            self.metrics.clear()


class ToolRegistry:
    """Tool Registry Implementation."""
    
    def __init__(self, logger, cache: Optional[ToolCache] = None, monitoring: Optional[ToolMonitoring] = None):
        self.logger = logger
        self.tools: Dict[str, BaseTool] = {}
        self.handlers: Dict[str, ToolHandler] = {}
        self.rateLimits: Dict[str, ToolRateLimit] = {}
        self.cache = cache or MapToolCache()
        self.monitoring = monitoring or MapToolMonitoring()
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool with the registry."""
        if tool.name in self.tools:
            raise ValueError(f"Tool {tool.name} is already registered")
        
        self.tools[tool.name] = tool
        self.logger.info(f"Tool registered: {tool.name}")
    
    def registerHandler(self, toolName: str, handler: ToolHandler) -> None:
        """Register a tool handler."""
        if toolName not in self.tools:
            raise ValueError(f"Tool {toolName} not found in registry")
        
        self.handlers[toolName] = handler
        self.logger.debug(f"Tool handler registered: {toolName}")
    
    def unregister(self, toolName: str) -> bool:
        """Unregister a tool from the registry."""
        removed = toolName in self.tools
        if removed:
            del self.tools[toolName]
            self.handlers.pop(toolName, None)
            self.rateLimits.pop(toolName, None)
            self.logger.info(f"Tool unregistered: {toolName}")
        return removed
    
    def get(self, toolName: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(toolName)
    
    def getHandler(self, toolName: str) -> Optional[ToolHandler]:
        """Get a tool handler by name."""
        return self.handlers.get(toolName)
    
    def listTools(self) -> List[BaseTool]:
        """List all registered tools."""
        return list(self.tools.values())
    
    def hasTool(self, toolName: str) -> bool:
        """Check if a tool is registered."""
        return toolName in self.tools
    
    def clear(self) -> None:
        """Clear all tools from the registry."""
        self.tools.clear()
        self.handlers.clear()
        self.rateLimits.clear()
        self.logger.info("Tool registry cleared")
    
    async def execute(self, toolName: str, input: Dict[str, Any], context: ToolContext) -> ToolExecutionResult:
        """Execute a tool with input and context."""
        tool = self.get(toolName)
        if not tool:
            raise ValueError(f"Tool {toolName} not found")
        
        handler = self.getHandler(toolName)
        if not handler:
            raise ValueError(f"Handler for tool {toolName} not found")
        
        # Create execution record
        execution = ToolExecution(
            id=self._generateExecutionId(),
            toolName=toolName,
            input=input,
            context=context,
            startTime=datetime.now(timezone.utc).isoformat(),
            status='running'
        )
        
        try:
            # Check rate limiting
            if not self._checkRateLimit(toolName, context):
                raise ValueError('Rate limit exceeded')
            
            # Execute tool
            result = await handler(input, context)
            
            execution.status = 'completed'
            execution.endTime = datetime.now(timezone.utc).isoformat()
            execution.duration = int((datetime.fromisoformat(execution.endTime) -
                                   datetime.fromisoformat(execution.startTime)).total_seconds() * 1000)
            execution.result = result.result
            
            self.monitoring.recordExecution(execution)
            
            return ToolExecutionResult(
                execution=execution,
                success=result.success,
                result=result.result,
                error=result.error
            )
        
        except Exception as error:
            execution.status = 'failed'
            execution.endTime = datetime.now(timezone.utc).isoformat()
            execution.duration = int((datetime.fromisoformat(execution.endTime) -
                                   datetime.fromisoformat(execution.startTime)).total_seconds() * 1000)
            execution.error = ToolError(
                code=MCPErrorCode.TOOL_EXECUTION_ERROR,
                message=str(error)
            )
            
            self.monitoring.recordExecution(execution)
            
            return ToolExecutionResult(
                execution=execution,
                success=False,
                error=execution.error
            )
    
    def getCapabilities(self) -> ToolCapabilities:
        """Get tool capabilities."""
        tools = self.listTools()
        categories = set()
        permissions = set()
        
        for tool in tools:
            if hasattr(tool, 'metadata'):
                categories.add(tool.metadata.category.value)
                if tool.metadata.requiresAuth:
                    permissions.add('authenticated')
        
        return ToolCapabilities(
            tools=tools,
            count=len(tools),
            categories=list(categories),
            permissions=list(permissions)
        )
    
    def getToolSchemas(self) -> List[MCPTool]:
        """Get tool schemas for MCP protocol - returns proper MCP Tool objects."""
        return [
            MCPTool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.inputSchema
            )
            for tool in self.listTools()
        ]
    
    def setRateLimit(self, toolName: str, maxRequests: int, windowMs: int) -> None:
        """Set rate limit for a tool."""
        self.rateLimits[toolName] = ToolRateLimit(
            toolName=toolName,
            maxRequests=maxRequests,
            windowMs=windowMs,
            currentRequests=0,
            resetTime=(datetime.now(timezone.utc).timestamp() + windowMs / 1000)
        )
    
    def getMetrics(self, toolName: str) -> ToolMetrics:
        """Get metrics for a tool."""
        return self.monitoring.getMetrics(toolName)
    
    def getAllMetrics(self) -> Dict[str, ToolMetrics]:
        """Get all metrics."""
        return self.monitoring.getAllMetrics()
    
    def _generateExecutionId(self) -> str:
        """Generate unique execution ID."""
        return f"exec_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{id(self) % 10000}"
    
    def _generateCacheKey(self, toolName: str, input: Dict[str, Any], context: ToolContext) -> str:
        """Generate cache key for tool execution."""
        inputHash = hashlib.md5(str(sorted(input.items())).encode()).hexdigest()
        contextHash = hashlib.md5(f"{context.userId}_{context.accessLevel}".encode()).hexdigest()
        return f"{toolName}_{inputHash}_{contextHash}"
    
    def _checkRateLimit(self, toolName: str, context: ToolContext) -> bool:
        """Check rate limit for tool execution."""
        rateLimit = self.rateLimits.get(toolName)
        if not rateLimit:
            return True  # No rate limit set
        
        now = datetime.now(timezone.utc).timestamp()
        if now > rateLimit.resetTime:
            rateLimit.currentRequests = 0
            rateLimit.resetTime = now + (rateLimit.windowMs / 1000)
        
        if rateLimit.currentRequests >= rateLimit.maxRequests:
            return False
        
        rateLimit.currentRequests += 1
        return True

