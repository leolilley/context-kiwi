"""
check_updates - Compare local directive versions against the registry.

This tool runs on the MCP server and queries Supabase.
The LLM provides its local versions, and this tool returns what needs updating.
The LLM then writes the updated files locally.
"""

from typing import Dict, Any, List
from context_kiwi.db.directives import DirectiveDB
from context_kiwi.mcp_types import ToolContext


async def check_updates_handler(params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """
    Compare local versions against registry and return updates needed.
    
    Params:
        local_versions: Dict[str, str] - Map of directive_name -> local_version
                       e.g. {"bootstrap": "1.5.0", "create_component": "1.0.0"}
        categories: List[str] - Optional list of categories to check (default: all)
    
    Returns:
        {
            "updates_available": [
                {
                    "name": "bootstrap",
                    "category": "core",
                    "local_version": "1.5.0",
                    "latest_version": "1.7.0",
                    "content": "... full directive content ...",
                    "changelog": "Fixed rules file generation"
                }
            ],
            "up_to_date": ["create_component", "create_directive"],
            "new_directives": [
                {
                    "name": "create_api",
                    "category": "actions",
                    "version": "1.0.0",
                    "content": "...",
                    "description": "Create API endpoints"
                }
            ],
            "summary": {
                "total_in_registry": 15,
                "updates_available": 2,
                "new_available": 3,
                "up_to_date": 10
            }
        }
    """
    local_versions = params.get("local_versions", {})
    categories = params.get("categories", None)
    
    db = DirectiveDB()
    
    # Get all available directives from registry
    if categories:
        all_directives = []
        for cat in categories:
            all_directives.extend(db.list(category=cat))
    else:
        all_directives = db.list()
    
    updates_available: List[Dict[str, Any]] = []
    up_to_date: List[str] = []
    new_directives: List[Dict[str, Any]] = []
    
    for directive_info in all_directives:
        name = directive_info["name"]
        latest_version = directive_info.get("latest_version")
        
        if not latest_version:
            continue
        
        if name in local_versions:
            local_version = local_versions[name]
            
            # Compare versions
            if latest_version != local_version:
                # Fetch full content for update
                directive = db.get(name)
                if directive:
                    updates_available.append({
                        "name": name,
                        "category": directive.category,
                        "local_version": local_version,
                        "latest_version": latest_version,
                        "content": directive.current_version.content,
                        "changelog": directive.current_version.changelog,
                    })
            else:
                up_to_date.append(name)
        else:
            # New directive not in local cache
            directive = db.get(name)
            if directive:
                new_directives.append({
                    "name": name,
                    "category": directive.category,
                    "version": latest_version,
                    "content": directive.current_version.content,
                    "description": directive.description,
                })
    
    return {
        "updates_available": updates_available,
        "up_to_date": up_to_date,
        "new_directives": new_directives,
        "summary": {
            "total_in_registry": len(all_directives),
            "updates_available": len(updates_available),
            "new_available": len(new_directives),
            "up_to_date": len(up_to_date),
        }
    }
