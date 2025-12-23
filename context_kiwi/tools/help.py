"""
Help Tool

Workflow guidance and documentation.
"""

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
from context_kiwi.utils import Logger


class HelpTool(BaseTool):
    """
    Get workflow guidance and documentation.
    """
    
    def __init__(self, logger: Logger):
        super().__init__(logger, {
            'category': ToolCategory.CORE,
            'requiresAuth': False,
            'rateLimited': False
        })
    
    @property
    def name(self) -> str:
        return "help"
    
    @property
    def description(self) -> str:
        return """Get help and workflow guidance.

OPTIONAL: topic ("overview"|"search"|"run"|"get"|"publish"|"context"|"directives")

Examples:
- help() - Get overview
- help("search") - Help for search tool
- help("run") - Help for run tool

Quick start: run("init") to initialize project. Core directives are pre-installed."""
    
    @property
    def inputSchema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": ["overview", "search", "run", "get", "publish", "context", "directives"],
                    "description": "Help topic",
                    "default": "overview"
                }
            }
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        """Execute help."""
        try:
            topic = input.get("topic") or "overview"
            content = self._get_help_content(topic)
            
            return ToolHandlerResult(
                success=True,
                result=self.createSuccessResult({
                    "topic": topic,
                    "content": content
                })
            )
            
        except Exception as e:
            self.logger.error(f"Help error: {e}")
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Help failed: {str(e)}"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error)
            )
    
    def _get_help_content(self, topic: str) -> dict[str, Any]:
        """Get help content for a topic."""
        
        if topic == "overview":
            return {
                "title": "Context Kiwi - Solve once, solve everywhere",
                "description": "Directive-based code generation MCP server",
                "FIRST_TIME_SETUP": {
                    "step_1": "run('init') - Creates .ai/ structure, detects tech stack",
                    "note": "Core directives are already in ~/.context-kiwi/ - no download needed",
                    "what_init_creates": [
                        ".ai/patterns/ - Code patterns (initially empty)",
                        ".ai/directives/custom/ - Your project-specific directives"
                    ],
                    "after_init": "Run 'run(\"context\")' to generate comprehensive project context"
                },
                "tools": {
                    "search": "Find directives (local or registry)",
                    "run": "Execute directive with context",
                    "get": "Download from registry (only for custom directives)",
                    "publish": "Share to registry",
                    "help": "This help"
                },
                "directive_locations": {
                    "~/.context-kiwi/directives/core/": "Core directives (shared across all projects)",
                    ".ai/directives/custom/": "Project-specific directives",
                    ".ai/directives/core/": "Only for overriding/editing core (use edit_core_directive)"
                },
                "quick_workflow": [
                    "1. run('init') - Initialize project (first time only)",
                    "2. search('auth') - Find relevant directives",
                    "3. run('directive_name', {inputs}) - Execute directive"
                ],
                "key_concept": (
                    "Directives are reusable instructions that combine with your "
                    "project context (.ai/) to generate code that fits YOUR codebase."
                )
            }
        
        elif topic == "search":
            return {
                "title": "search - Find Directives",
                "usage": "search(query, source='local')",
                "sources": {
                    "local": "Search project (.ai/directives/) and user (~/.context-kiwi/directives/)",
                    "registry": "Search community registry with tech stack context",
                    "all": "Search everywhere"
                },
                "examples": [
                    "search('auth') - Find local auth directives",
                    "search('JWT auth', source='registry') - Find in registry",
                    "search('form validation', source='all') - Search everywhere"
                ],
                "note": "Registry search automatically includes your tech stack for better matching"
            }
        
        elif topic == "run":
            return {
                "title": "run - Execute Directive",
                "usage": "run(directive, inputs={})",
                "flow": [
                    "1. Load directive from LOCAL only (project > user)",
                    "2. Validate inputs against schema",
                    "3. Check required credentials",
                    "4. Load project context (.ai/)",
                    "5. Return directive + context for you to follow"
                ],
                "examples": [
                    "run('init') - Initialize project",
                    "run('create_component', {name: 'Button'})",
                    "run('jwt_auth', {refresh_endpoint: '/auth/refresh'})"
                ],
                "note": "Only runs LOCAL directives. Use get() to download from registry first."
            }
        
        elif topic == "get":
            return {
                "title": "get - Download from Registry",
                "usage": "get(directive, to='project')",
                "destinations": {
                    "project": ".ai/directives/core/ - for team (committed to git)",
                    "user": "~/.context-kiwi/directives/core/ - personal (works across projects)"
                },
                "options": {
                    "version": "Download specific version",
                    "list_versions": "Show available versions",
                    "check": "Check for updates to local directives",
                    "update": "Update all local directives"
                },
                "examples": [
                    "get('jwt_auth_zustand') - Download to project",
                    "get('my_helper', to='user') - Download for personal use",
                    "get('jwt_auth', version='1.0.0') - Specific version",
                    "get(check=True) - Check for updates"
                ]
            }
        
        elif topic == "publish":
            return {
                "title": "publish - Share to Registry",
                "usage": "publish(directive, version, source='project')",
                "requirements": [
                    "CONTEXT_KIWI_API_KEY environment variable",
                    "Valid directive structure (name, version, process)"
                ],
                "sources": {
                    "project": ".ai/directives/custom/",
                    "user": "~/.context-kiwi/directives/custom/"
                },
                "examples": [
                    "publish('our_api_pattern', version='1.0.0')",
                    "publish('my_helper', version='2.0.0', source='user')"
                ],
                "tip": "Add tech_stack to your directive for better discoverability"
            }
        
        elif topic == "context":
            return {
                "title": "Project Context (.ai/ folder)",
                "description": "The .ai/ folder contains your project's context for code generation",
                "structure": {
                    ".ai/project_context.md": "Auto-generated comprehensive project context (run 'context' directive)",
                    ".ai/patterns/": "Code patterns (api.md, components.md, etc.)",
                    ".ai/directives/custom/": "Project-specific directives"
                },
                "NOT_in_project": {
                    "~/.context-kiwi/directives/core/": "Core directives (shared, auto-synced)",
                    "~/.context-kiwi/.runs/": "Execution history (user space)"
                },
                "setup": "run('init') - Creates structure, then run('context') - Generates project context",
                "tip": "The more context you provide, the better the generated code fits your codebase",
                "important": (
                    "Do NOT download core directives to .ai/directives/core/. "
                    "They're already available from ~/.context-kiwi/. "
                    "Only create core/ if you need to override/edit a directive."
                )
            }
        
        elif topic == "directives":
            return {
                "title": "Writing Good Directives",
                "key_principle": "Specificity beats generality",
                "structure": {
                    "metadata": "name, version, description, category",
                    "context": "tech_stack, assumptions, dependencies",
                    "inputs": "JSON Schema for validation",
                    "process": "Step-by-step instructions with code patterns",
                    "outputs": "What files get created"
                },
                "bad_example": "<step>Set up auth state</step> - Too vague",
                "good_example": (
                    "<step><pattern><![CDATA[\n"
                    "// stores/authStore.ts\n"
                    "export const useAuthStore = create<AuthState>(...)\n"
                    "]]></pattern></step>"
                ),
                "tips": [
                    "Include actual code in <pattern> blocks",
                    "Declare your tech stack for better matching",
                    "Be specific about versions (React 18+, not just React)",
                    "Document assumptions clearly"
                ]
            }
        
        else:
            return {
                "error": f"Unknown topic: {topic}",
                "available_topics": ["overview", "search", "run", "get", "publish", "context", "directives"]
            }

