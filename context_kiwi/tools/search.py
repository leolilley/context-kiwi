"""
Search Tool

Find directives in local space or registry.
"""

from typing import Any
from context_kiwi.directives import DirectiveLoader
from context_kiwi.execution.context import get_tech_stack_list
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


class SearchTool(BaseTool):
    """
    Search for directives.
    
    Sources:
    - "local": Project + User space
    - "registry": Remote registry with context-aware ranking
    - "all": Everything
    """
    
    def __init__(self, logger: Logger):
        super().__init__(logger, {
            'category': ToolCategory.CORE,
            'requiresAuth': False,
            'rateLimited': False
        })
    
    def _get_loader(self, project_path: str | None = None) -> DirectiveLoader:
        """Get loader for the given project path."""
        from pathlib import Path
        path = Path(project_path) if project_path else None
        return DirectiveLoader(project_path=path)
    
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return """Find directives using natural language search.

REQUIRED: query, source, project_path (when source is "local" or "all")
OPTIONAL: sort_by (defaults to "score")

Search Features:
- Multi-term matching: "JWT auth" matches directives with both "JWT" and "auth"
- Smart scoring: Name matches ranked higher than description matches
- Context-aware: Registry search auto-includes your tech stack for better ranking

Sources:
- "local": Search .ai/directives/ (project) and ~/.context-kiwi/directives/ (user)
  → REQUIRES project_path to search project space
- "registry": Search community registry (no project_path needed)
- "all": Search both local and registry
  → REQUIRES project_path to include project space in results

Examples:
- search("auth", "registry") - Search registry only (no project_path needed)
- search("auth", "local", project_path="/path/to/project") - Search project + user space
- search("JWT authentication", "all", project_path="/path/to/project", sort_by="date") - Search everywhere
- search("React component", "registry", tech_stack=["React", "TypeScript"]) - Tech stack filtered

CRITICAL: Always provide project_path when searching "local" or "all" - without it, the search will fail with an error."""
    
    @property
    def inputSchema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - natural language search supporting multiple terms. Examples: 'JWT auth', 'form validation', 'React component'. All terms must match for best results."
                },
                "source": {
                    "type": "string",
                    "enum": ["local", "registry", "all"],
                    "description": "REQUIRED: 'local' (project+user), 'registry' (community), or 'all' (both)"
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by categories (e.g., ['patterns', 'workflows', 'actions'])"
                },
                "subcategories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by subcategories (e.g., ['api-endpoints', 'react-components'])"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags (array of tag strings)"
                },
                "tech_stack": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tech stack compatibility (e.g., ['React', 'TypeScript'])"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["score", "success_rate", "date", "downloads"],
                    "description": "OPTIONAL: 'score' (relevance, default), 'success_rate', 'date', or 'downloads'",
                    "default": "score"
                },
                "date_from": {
                    "type": "string",
                    "description": "Filter directives created/updated after this date (ISO 8601 format, e.g., '2024-01-01T00:00:00Z')"
                },
                "date_to": {
                    "type": "string",
                    "description": "Filter directives created/updated before this date (ISO 8601 format, e.g., '2024-12-31T23:59:59Z')"
                },
                "project_path": {
                    "type": "string",
                    "description": "REQUIRED for source='local' or 'all': Absolute path to project root (where .ai/ folder lives). Example: '/home/user/myproject'. Not needed for source='registry'."
                }
            },
            "required": ["query", "source"]
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        """Execute search."""
        try:
            query = input.get("query")
            source = input.get("source")
            project_path = input.get("project_path")
            
            # Extract filters
            categories = input.get("categories")
            subcategories = input.get("subcategories")
            tags = input.get("tags")
            tech_stack_filter = input.get("tech_stack")
            sort_by: str = input.get("sort_by") or "score"
            date_from = input.get("date_from")
            date_to = input.get("date_to")
            
            # Validate required fields
            if not query:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message="Query parameter is required"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            if not source:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message="Source parameter is required"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # Validate project_path requirement
            if source in ("local", "all") and not project_path:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message=f"project_path is required when source='{source}'. Without it, only user space (~/.context-kiwi/) can be searched. Please provide the absolute path to your project root (where .ai/ folder lives)."
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            loader = self._get_loader(project_path)
            
            # Get project tech stack for context-aware search (if not explicitly provided)
            tech_stack = tech_stack_filter or (get_tech_stack_list() if source in ("registry", "all") else [])
            
            # Search with filters
            results = loader.search(
                query=query,
                source=source,
                sort_by=sort_by,
                project_tech_stack=tech_stack if tech_stack else None,
                categories=categories,
                subcategories=subcategories,
                tags=tags,
                tech_stack_filter=tech_stack_filter,
                date_from=date_from,
                date_to=date_to
            )
            
            # Format results
            formatted = []
            for match in results[:20]:  # Limit to 20 results
                result_item = {
                    "name": match.name,
                    "description": match.description,
                    "version": match.version,
                    "source": match.source,
                    "score": match.score,
                    "tech_stack": match.tech_stack,
                    "category": match.category
                }
                if match.subcategory:
                    result_item["subcategory"] = match.subcategory
                # Add optional fields if available
                if hasattr(match, 'quality_score') and match.quality_score is not None:
                    result_item["quality_score"] = match.quality_score
                if hasattr(match, 'download_count') and match.download_count is not None:
                    result_item["download_count"] = match.download_count
                if hasattr(match, 'created_at') and match.created_at:
                    result_item["created_at"] = match.created_at
                if hasattr(match, 'updated_at') and match.updated_at:
                    result_item["updated_at"] = match.updated_at
                formatted.append(result_item)
            
            return ToolHandlerResult(
                success=True,
                result=self.createSuccessResult({
                    "query": query,
                    "source": source,
                    "filters": {
                        "categories": categories,
                        "subcategories": subcategories,
                        "tags": tags,
                        "tech_stack": tech_stack_filter,
                        "sort_by": sort_by,
                        "date_from": date_from,
                        "date_to": date_to
                    },
                    "results": formatted,
                    "total": len(results),
                    "tech_stack_context": tech_stack if not tech_stack_filter else None
                })
            )
            
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Search failed: {str(e)}"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error)
            )

