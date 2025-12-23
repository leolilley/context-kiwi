"""
get_bundle - Fetch multiple directives at once.

Returns curl commands for deterministic file downloads.
Agent runs the commands - content never passes through agent.
"""

from typing import Dict, Any, List
from context_kiwi.db.directives import DirectiveDB
from context_kiwi.config.settings import get_base_url
from context_kiwi.mcp_types import ToolContext

# Predefined bundles
BUNDLES = {
    "core": [
        "create_directive",
        "publish_directive",
        "anneal_directive",
        "log_directive",
    ],
}


async def get_bundle_handler(params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """
    Fetch multiple directives at once.
    
    Params:
        bundle: str - Predefined bundle name ("core")
        names: List[str] - Or explicit list of directive names
    
    Returns:
        {
            "status": "ready",
            "count": 4,
            "install_commands": [
                "curl -sL {base_url}/d/create_directive.md -o .ai/directives/core/create_directive.md",
                ...
            ],
            "combined_command": "mkdir -p .ai/directives/core && curl -sL ... && curl -sL ..."
        }
    """
    bundle_name = params.get("bundle")
    names = params.get("names")
    
    if bundle_name:
        if bundle_name not in BUNDLES:
            return {
                "status": "error",
                "message": f"Unknown bundle: {bundle_name}. Available: {list(BUNDLES.keys())}"
            }
        names = BUNDLES[bundle_name]
    
    if not names:
        return {
            "status": "error",
            "message": "Provide either 'bundle' or 'names' parameter"
        }
    
    db = DirectiveDB()
    
    base_url = get_base_url()
    commands: List[str] = []
    errors: List[str] = []
    
    for name in names:
        try:
            directive = db.get(name)
            if not directive:
                errors.append(f"{name}: not found")
                continue
            
            save_path = f".ai/directives/core/{name}.md"
            download_url = f"{base_url}/d/{name}.md"
            
            # curl command for this directive - content downloads directly, never passes through agent
            cmd = f"curl -sL {download_url} -o {save_path}"
            commands.append(cmd)
            
        except Exception as e:
            errors.append(f"{name}: {str(e)}")
    
    # Combined command: create dir + all curls
    combined = "mkdir -p .ai/directives/core && " + " && ".join(commands) if commands else ""
    
    return {
        "status": "ready",
        "count": len(commands),
        "install_commands": commands,
        "combined_command": combined,
        "errors": errors if errors else None,
    }
