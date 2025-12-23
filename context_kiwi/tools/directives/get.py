"""
get_directive - Fetch directive from registry.

For saveable directives: returns install command (curl)
For no-save directives: returns content directly (agent follows it)
"""

from typing import Dict, Any
from context_kiwi.db.directives import DirectiveDB
from context_kiwi.config.settings import get_base_url
from context_kiwi.mcp_types import ToolContext


async def get_directive_handler(params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """
    Fetch a directive from the registry.
    
    Params:
        name: str - Directive name (e.g. "create_directive")
        version: str - Optional version constraint
    
    Returns for saveable directives:
        {
            "status": "found",
            "name": "create_directive",
            "version": "1.2.0",
            "install_command": "curl -sL {base_url}/d/create_directive.md -o .ai/directives/core/create_directive.md"
        }
        
    Returns for no-save directives (like init):
        {
            "status": "found",
            "name": "init",
            "version": "1.1.0",
            "content": "# Init Directive\n\n...",
            "save": false
        }
        
    Agent: For install_command, run it. For content, follow the directive.
    """
    name = params.get("name")
    version_constraint = params.get("version")
    
    if not name:
        return {"status": "error", "message": "Missing required parameter: name"}
    
    db = DirectiveDB()
    
    try:
        directive = db.get(name, version_constraint)
        
        if not directive:
            return {
                "status": "not_found",
                "message": f"Directive not found: {name}"
            }
        
        version = directive.current_version.version
        content = directive.current_version.content
        description = directive.description or f"{name} directive"
        
        # Check if directive has <save>false</save> - return content directly
        no_save = "<save>false</save>" in content
        
        if no_save:
            # Agent needs to read and follow this directive
            return {
                "status": "found",
                "name": name,
                "version": version,
                "description": description,
                "content": content,
                "save": False,
                "hint": "Follow this directive directly, don't save it.",
            }
        else:
            # Agent downloads via curl - content doesn't pass through agent
            base_url = get_base_url()
            save_path = f".ai/directives/core/{name}.md"
            download_url = f"{base_url}/d/{name}.md"
            install_cmd = f"curl -sL {download_url} -o {save_path}"
            
            return {
                "status": "found",
                "name": name,
                "version": version,
                "description": description,
                "install_command": install_cmd,
                "path": save_path,
                "hint": f"Run the install_command, then read {save_path} and follow it.",
            }
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch directive: {str(e)}"}
