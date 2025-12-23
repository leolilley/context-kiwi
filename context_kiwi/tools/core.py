"""
Core Meta-Tools
The 3 core meta-tools exposed to the LLM: search_tool, execute, help.

Architecture:
- The MCP server runs remotely (e.g., Fly.io) and can ONLY access Supabase
- Directive tools (get_directive, check_updates, publish_directive) query/write Supabase
- The LLM has local file access and follows directive instructions

Workflow:
1. search_tool("intent") → finds matching directives in registry
2. execute("get_directive", {name: "directive_name"}) → fetches directive content from registry
3. LLM follows the directive steps (creating files, running commands, etc.)
"""

from typing import Dict, Any

from context_kiwi.tools.base import BaseTool
from context_kiwi.mcp_types import (
    ToolInput, ToolContext, ToolHandlerResult,
    ToolCategory, ToolError, MCPErrorCode
)
from context_kiwi.db.directives import DirectiveDB


# Directive tools that can be called via execute()
DIRECTIVE_TOOLS = ["get_directive", "check_updates", "publish_directive"]


class SearchTool(BaseTool):
    """Search for directives by intent."""
    
    def __init__(self, logger):
        super().__init__(logger, {'category': ToolCategory.CORE})
        self._db: DirectiveDB | None = None
    
    @property
    def db(self) -> DirectiveDB:
        """Lazy-initialize database connection."""
        if self._db is None:
            self._db = DirectiveDB(logger=self.logger)
        return self._db
    
    @property
    def name(self) -> str:
        return "search_tool"
    
    @property
    def description(self) -> str:
        return """Search for directives by intent. Returns matching directives from the registry.

Use this to find directives for what you want to accomplish.
After finding a directive, use execute("get_directive", {name: "directive_name"}) to fetch it.
Then follow the directive's steps."""
    
    @property
    def inputSchema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What you want to do (e.g., 'setup project', 'create component')"
                },
                "tech_stack": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Project tech stack for compatibility filtering"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        query = str(input.get("query", "")).lower()
        tech_stack = input.get("tech_stack") or []
        
        if not query:
            error = ToolError(
                code=MCPErrorCode.INVALID_INPUT,
                message="Query parameter is required"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error.code.value, error.message)
            )
        
        try:
            # Search directives from registry
            results = self.db.search(query, tech_stack=tech_stack if tech_stack else None)
            
            # Transform to output format
            directives = [
                {
                    "name": r["name"],
                    "description": r.get("description"),
                    "category": r["category"],
                    "version": r.get("latest_version"),
                    "compatibility_score": r.get("compatibility_score", 1.0),
                    "download_count": r.get("download_count", 0),
                }
                for r in results[:10]
            ]
            
            self.logger.info(f"search_tool: query='{query}' results={len(directives)}")
            
            return ToolHandlerResult(
                success=True,
                result=self.createSuccessResult({
                    "status": "search_results",
                    "directives": directives,
                    "hint": "To fetch a directive, use: execute('get_directive', {name: 'directive_name'})"
                })
            )
        except Exception as e:
            self.logger.error(f"search_tool failed: {e}")
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Search failed: {str(e)}"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error.code.value, error.message)
            )


class ExecuteTool(BaseTool):
    """Execute a directive tool with parameters.
    
    Directive tools run on the MCP server and interact with the Supabase registry.
    They CANNOT access local files - that's the LLM's job.
    """
    
    def __init__(self, logger, tool_registry=None, directive_tools=None):
        super().__init__(logger, {'category': ToolCategory.CORE})
        self.tool_registry = tool_registry
        # Directive tools registry: maps tool_name -> callable
        self.directive_tools: Dict[str, Any] = directive_tools or {}
    
    def register_directive_tool(self, name: str, handler):
        """Register a directive tool that can be called via execute()."""
        self.directive_tools[name] = handler
    
    @property
    def name(self) -> str:
        return "execute"
    
    @property
    def description(self) -> str:
        return """Execute a directive tool with parameters.

Available directive tools:
- get_directive: Fetch directive content from registry
  Example: execute("get_directive", {name: "init"})

- get_bundle: Fetch multiple directives at once
  Example: execute("get_bundle", {bundle: "core"})
  Example: execute("get_bundle", {names: ["init", "create_directive"]})
  
- check_updates: Compare local versions against registry
  Example: execute("check_updates", {local_versions: {"init": "1.0.0"}})
  
- publish_directive: Publish a new directive version to registry

After fetching a directive, follow its instructions to complete the task."""
    
    @property
    def inputSchema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the directive tool (get_directive, check_updates, publish_directive)"
                },
                "params": {
                    "type": "object",
                    "description": "Parameters for the tool (e.g., {name: 'bootstrap'} for get_directive)"
                }
            },
            "required": ["tool_name"]
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        tool_name = input.get("tool_name", "")
        params = input.get("params", {})
        
        if not tool_name:
            error = ToolError(
                code=MCPErrorCode.INVALID_INPUT,
                message="tool_name parameter is required"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error.code.value, error.message)
            )
        
        # Check if this is a registered directive tool
        if tool_name in self.directive_tools:
            handler = self.directive_tools[tool_name]
            self.logger.info(f"execute: running '{tool_name}' with params={params}")
            
            try:
                result = await handler(params, context)
                
                return ToolHandlerResult(
                    success=True,
                    result=self.createSuccessResult({
                        "status": "executed",
                        "tool_name": tool_name,
                        "result": result
                    })
                )
            except FileNotFoundError as e:
                error = ToolError(
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=str(e)
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error.code.value, error.message)
                )
            except ValueError as e:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message=str(e)
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error.code.value, error.message)
                )
            except Exception as e:
                error = ToolError(
                    code=MCPErrorCode.TOOL_EXECUTION_ERROR,
                    message=f"Directive tool '{tool_name}' failed: {str(e)}"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error.code.value, error.message)
                )
        
        # Not a directive tool - provide helpful error
        available = list(self.directive_tools.keys())
        error = ToolError(
            code=MCPErrorCode.TOOL_NOT_FOUND,
            message=f"Directive tool '{tool_name}' not found. Available: {available}"
        )
        return ToolHandlerResult(
            success=False,
            error=error,
            result=self.createSuccessResult({
                "status": "error",
                "error": error.message,
                "available_directive_tools": available,
            })
        )


class HelpTool(BaseTool):
    """Get workflow guidance for using Context Kiwi."""
    
    def __init__(self, logger):
        super().__init__(logger, {'category': ToolCategory.CORE})
    
    @property
    def name(self) -> str:
        return "help"
    
    @property
    def description(self) -> str:
        return """Get workflow guidance for using Context Kiwi.

**New project?** Start with: execute("get_directive", {name: "init"})

Topics:
- workflow: How to use the meta-tools (search_tool, execute, help)
- tools: Available directive tools and their parameters

Key concept: The MCP server runs remotely and can only access Supabase.
YOU (the LLM) have local file access - follow directive instructions to create/modify files."""
    
    @property
    def inputSchema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Help topic: workflow, tools"
                }
            }
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        topic = str(input.get("topic", "workflow"))
        
        self.logger.info(f"help: topic='{topic}'")
        
        if topic == "tools":
            return ToolHandlerResult(
                success=True,
                result=self.createSuccessResult({
                    "topic": "tools",
                    "getting_started": 'New project? execute("get_directive", {name: "init"})',
                    "directive_tools": {
                        "get_directive": {
                            "description": "Fetch directive content from registry",
                            "params": {
                                "name": "Directive name (required)",
                                "version": "Version constraint (optional, e.g., '^1.0.0')"
                            },
                            "example": 'execute("get_directive", {name: "init"})'
                        },
                        "check_updates": {
                            "description": "Compare local versions against registry",
                            "params": {
                                "local_versions": "Dict of name -> version you have locally",
                                "categories": "Optional list of categories to check"
                            },
                            "example": 'execute("check_updates", {local_versions: {"init": "1.0.0"}})'
                        },
                        "publish_directive": {
                            "description": "Publish new directive version to registry",
                            "params": {
                                "name": "Directive name (required)",
                                "version": "Semver version (required)",
                                "content": "Full directive content (required)",
                                "changelog": "What changed (optional)"
                            }
                        }
                    }
                })
            )
        
        # Default: workflow help
        return ToolHandlerResult(
            success=True,
            result=self.createSuccessResult({
                "topic": "workflow",
                "getting_started": 'New project? execute("get_directive", {name: "init"})',
                "meta_tools": {
                    "search_tool": "Search for directives by intent",
                    "execute": "Run directive tools (get_directive, check_updates, publish_directive)",
                    "help": "Get this guidance"
                },
                "typical_workflow": [
                    "0. New project? execute('get_directive', {name: 'init'}) → initialize Context Kiwi",
                    "1. search_tool('create react component') → find relevant directives",
                    "2. execute('get_directive', {name: 'create_component'}) → fetch directive content",
                    "3. Follow the directive's instructions to complete the task",
                    "4. The directive tells you what files to create, commands to run, etc."
                ],
                "key_concept": "The MCP server runs remotely and queries Supabase. "
                              "YOU have local file access - directives are instructions for YOU to follow."
            })
        )
