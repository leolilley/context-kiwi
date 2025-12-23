"""
Get Tool

Download directives from registry to local space.
Uses lock file for efficient syncing.
"""

from pathlib import Path
from typing import Any

import httpx
from context_kiwi.config.lockfile import (
    compute_content_hash,
    get_locked_directive,
    needs_update,
    set_locked_directive,
)
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


class GetTool(BaseTool):
    """
    Download directives from registry to local space.
    
    Destinations:
    - "project" (default): .ai/directives/{category}/
    - "user": ~/.context-kiwi/directives/{category}/
    
    Category is determined from registry. Supports nested subcategories.
    """
    
    def __init__(self, logger: Logger, registry_url: str | None = None):
        super().__init__(logger, {
            'category': ToolCategory.CORE,
            'requiresAuth': False,
            'rateLimited': False
        })
        from context_kiwi.config import get_supabase_url, get_supabase_key
        self.supabase_url = get_supabase_url()
        self.supabase_key = get_supabase_key()
        from context_kiwi.config import get_user_home
        self.user_path = get_user_home() / "directives"
    
    def _get_project_path(self, project_path: str | None) -> Path:
        """Get project directives path."""
        root = Path(project_path) if project_path else Path.cwd()
        return root / ".ai" / "directives"
    
    @property
    def name(self) -> str:
        return "get"
    
    @property
    def description(self) -> str:
        return """Download a directive from registry to your local filesystem.

REQUIRED: directive (name), project_path (when to="project")
OPTIONAL: to ("project" or "user"), version

When to use:
- Downloading custom directives from registry
- Getting a specific version of a directive

When NOT to use:
- Core directives (init, create_directive, etc.) - already in ~/.context-kiwi/
- Just searching - use search() instead

Destinations:
- to="project": {project_path}/.ai/directives/{category}/ (committed to git, team-shared)
  REQUIRES project_path parameter
- to="user": ~/.context-kiwi/directives/{category}/ (personal, works across projects)
  DOES NOT require project_path parameter

Category is determined from the registry. Supports nested subcategories via the path parameter.

Examples:
- get("jwt_auth_zustand", project_path="/home/user/myproject") - Download to project
- get("my_helper", to="user") - Download for personal use
- get("jwt_auth", version="1.0.0", project_path="/home/user/myproject") - Specific version

CRITICAL: When to="project", you MUST provide project_path. Use the workspace root path.
Common mistake: Downloading core directives (they're already available)."""
    
    @property
    def inputSchema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directive": {
                    "type": "string",
                    "description": "Name of directive to download"
                },
                "version": {
                    "type": "string",
                    "description": "Specific version (default: latest)"
                },
                "to": {
                    "type": "string",
                    "enum": ["project", "user"],
                    "description": "Destination: project (.ai/) or user (~/.context-kiwi/)",
                    "default": "project"
                },
                "list_versions": {
                    "type": "boolean",
                    "description": "List available versions for the directive",
                    "default": False
                },
                "check": {
                    "type": "boolean",
                    "description": "Check for updates to local directives",
                    "default": False
                },
                "update": {
                    "type": "boolean",
                    "description": "Sync ALL core directives from registry (adds new + updates existing)",
                    "default": False
                },
                "project_path": {
                    "type": "string",
                    "description": "REQUIRED when to='project': Full absolute path to project root directory. Example: '/home/user/myproject'. Use workspace path. DO NOT use relative paths. This is CRITICAL - without it, files will be saved to wrong location!"
                },
                "path": {
                    "type": "string",
                    "description": "Optional subdirectory path within core/ (e.g., 'export-chat' for core/export-chat/). Supports nested folder structures."
                }
            }
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        """Execute get."""
        try:
            directive = input.get("directive")
            version = input.get("version")
            to = input.get("to", "project")
            list_versions = input.get("list_versions", False)
            check = input.get("check", False)
            update = input.get("update", False)
            project_path = input.get("project_path")
            sub_path = input.get("path")  # Optional subdirectory path (e.g., "export-chat")
            
            # Set project path for this request
            self.project_path = self._get_project_path(project_path)
            
            # Handle different operations
            if check:
                return await self._check_updates()
            
            if update:
                return await self._update_all(to or "project")
            
            if not directive:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message="Directive name is required (unless using check or update)"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            if list_versions:
                return await self._list_versions(directive)
            
            # Validate project_path when actually downloading to project
            # (not for list_versions, check, or update operations)
            if to == "project" and not project_path:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message="CRITICAL: project_path is REQUIRED when to='project'. Provide the full workspace path (e.g., '/home/user/myproject'). Without this, files will be saved to the wrong location!"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # Download directive
            return await self._download(directive, version, to or "project", sub_path)
            
        except Exception as e:
            self.logger.error(f"Get error: {e}")
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Get failed: {str(e)}"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error)
            )
    
    async def _download(
        self, 
        directive: str, 
        version: str | None = None, 
        to: str = "project",
        sub_path: str | None = None
    ) -> ToolHandlerResult:
        """Download a directive from Supabase registry."""
        try:
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get directive ID, category, and subcategory
                dir_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/directives",
                    params={"name": f"eq.{directive}", "select": "id,category,subcategory"},
                    headers=headers
                )
                
                directives = dir_resp.json() if dir_resp.status_code == 200 else []
                if not directives:
                    error = ToolError(
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"Directive '{directive}' not found in registry"
                    )
                    return ToolHandlerResult(success=False, error=error, result=self.createErrorResult(error))
                
                directive_id = directives[0]["id"]
                # Default to "actions" if category missing from registry (not "core" which is reserved for system directives)
                category = directives[0].get("category", "actions")
                subcategory = directives[0].get("subcategory") or sub_path  # Use registry subcategory or provided path
                
                # Get version (latest or specific) - include content_hash
                params = {
                    "directive_id": f"eq.{directive_id}",
                    "select": "version,content,content_hash"
                }
                if version:
                    params["version"] = f"eq.{version}"
                else:
                    params["is_latest"] = "eq.true"
                
                ver_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/directive_versions",
                    params=params,
                    headers=headers
                )
                
                versions = ver_resp.json() if ver_resp.status_code == 200 else []
                if not versions:
                    error = ToolError(
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"Version not found for '{directive}'"
                    )
                    return ToolHandlerResult(success=False, error=error, result=self.createErrorResult(error))
                
                # If no specific version requested and multiple versions returned, get the latest
                # (in case is_latest flag isn't set correctly, sort by version desc)
                if not version and len(versions) > 1:
                    # Sort by version (semantic versioning) to get true latest
                    from context_kiwi.utils.semver import parse
                    def version_key(v):
                        try:
                            major, minor, patch, _ = parse(v["version"])
                            return (major, minor, patch)
                        except ValueError:
                            return (0, 0, 0)
                    versions.sort(key=version_key, reverse=True)
                    # Use the first one (highest version)
                
                content = versions[0]["content"]
                actual_version = versions[0]["version"]
                registry_hash = versions[0].get("content_hash")
                
                # Verify we got the requested version
                if version and actual_version != version:
                    error = ToolError(
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"Requested version {version} but registry returned {actual_version} for directive {directive}"
                    )
                    return ToolHandlerResult(success=False, error=error, result=self.createErrorResult(error))
                
                # Determine destination using category and subcategory from registry
                dest_path = self.project_path if to == "project" else self.user_path
                
                # Use category from registry
                dest_path = dest_path / category
                
                # Support nested folder structures via subcategory or sub_path parameter
                # e.g., subcategory="export-chat" -> {category}/export-chat/{directive}.md
                if subcategory:
                    dest_path = dest_path / subcategory
                
                dest_path.mkdir(parents=True, exist_ok=True)
                
                # Write file (write_text always overwrites)
                file_path = dest_path / f"{directive}.md"
                file_path.write_text(content, encoding='utf-8')
                
                # Update lock file (for user space only - that's the cache)
                if to == "user":
                    content_hash = registry_hash or compute_content_hash(content)
                    set_locked_directive(directive, actual_version, content_hash, "registry")
                
                # Build display path
                if subcategory:
                    dest_display = f".ai/directives/{category}/{subcategory}/" if to == "project" else f"~/.context-kiwi/directives/{category}/{subcategory}/"
                else:
                    dest_display = f".ai/directives/{category}/" if to == "project" else f"~/.context-kiwi/directives/{category}/"
                
                return ToolHandlerResult(
                    success=True,
                    result=self.createSuccessResult({
                        "status": "downloaded",
                        "directive": directive,
                        "version": actual_version,
                        "destination": to,
                        "path": dest_display + f"{directive}.md",
                        "message": f"Downloaded {directive}@{actual_version} to {dest_display}"
                    })
                )
                
        except httpx.RequestError as e:
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Failed to connect to registry: {str(e)}"
            )
            return ToolHandlerResult(success=False, error=error, result=self.createErrorResult(error))
    
    async def _list_versions(self, directive: str) -> ToolHandlerResult:
        """List available versions for a directive."""
        try:
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get directive ID
                dir_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/directives",
                    params={"name": f"eq.{directive}", "select": "id"},
                    headers=headers
                )
                
                directives = dir_resp.json() if dir_resp.status_code == 200 else []
                if not directives:
                    error = ToolError(
                        code=MCPErrorCode.RESOURCE_NOT_FOUND,
                        message=f"Directive '{directive}' not found in registry"
                    )
                    return ToolHandlerResult(
                        success=False,
                        error=error,
                        result=self.createErrorResult(error)
                    )
                
                directive_id = directives[0]["id"]
                
                # Get all versions
                ver_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/directive_versions",
                    params={
                        "directive_id": f"eq.{directive_id}",
                        "select": "version,is_latest,created_at",
                        "order": "created_at.desc"
                    },
                    headers=headers
                )
                
                versions_data = ver_resp.json() if ver_resp.status_code == 200 else []
                versions = [v["version"] for v in versions_data]
                latest = next((v["version"] for v in versions_data if v.get("is_latest")), versions[0] if versions else None)
                
                # Check local version
                local_version = self._get_local_version(directive)
                
                return ToolHandlerResult(
                    success=True,
                    result=self.createSuccessResult({
                        "directive": directive,
                        "versions": versions,
                        "latest": latest,
                        "local": local_version
                    })
                )
                
        except httpx.RequestError as e:
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Failed to connect to registry: {str(e)}"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error)
            )
    
    async def _check_updates(self) -> ToolHandlerResult:
        """Check for updates to local directives."""
        updates_available = []
        up_to_date = []
        
        # Check both project and user directories
        for location, base_path in [("project", self.project_path), ("user", self.user_path)]:
            if not base_path.exists():
                continue
            
            # Search recursively in all category subdirectories
            for file in base_path.rglob("*.md"):
                directive_name = file.stem
                local_version = self._get_local_version(directive_name, base_path)
                
                # Check registry for latest
                try:
                    headers = {
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}"
                    }
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        # Get directive ID
                        dir_resp = await client.get(
                            f"{self.supabase_url}/rest/v1/directives",
                            params={"name": f"eq.{directive_name}", "select": "id"},
                            headers=headers
                        )
                        directives = dir_resp.json() if dir_resp.status_code == 200 else []
                        
                        if directives:
                            directive_id = directives[0]["id"]
                            # Get latest version
                            ver_resp = await client.get(
                                f"{self.supabase_url}/rest/v1/directive_versions",
                                params={
                                    "directive_id": f"eq.{directive_id}",
                                    "is_latest": "eq.true",
                                    "select": "version"
                                },
                                headers=headers
                            )
                            versions = ver_resp.json() if ver_resp.status_code == 200 else []
                            latest = versions[0]["version"] if versions else None
                            
                            if latest and local_version and latest != local_version:
                                updates_available.append({
                                    "name": directive_name,
                                    "local": local_version,
                                    "latest": latest,
                                    "location": location
                                })
                            elif latest and local_version:
                                up_to_date.append(f"{directive_name}@{local_version}")
                except Exception:
                    pass  # Skip if can't check
        
        return ToolHandlerResult(
            success=True,
            result=self.createSuccessResult({
                "updates_available": updates_available,
                "up_to_date": up_to_date
            })
        )
    
    async def _update_all(self, to: str = "project") -> ToolHandlerResult:
        """Sync ALL core directives from registry to local space.
        
        Uses lock file to skip unchanged directives (for user space).
        """
        import json
        
        updated = []
        added = []
        skipped = []
        errors = []
        
        path = self.project_path if to == "project" else self.user_path
        path.mkdir(parents=True, exist_ok=True)
        
        try:
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get ALL core directives with their latest version info
                dir_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/directives",
                    params={"category": "eq.core", "select": "id,name"},
                    headers=headers
                )
                
                if dir_resp.status_code != 200:
                    error = ToolError(
                        code=MCPErrorCode.INTERNAL_ERROR,
                        message=f"Failed to fetch directives: {dir_resp.status_code}"
                    )
                    return ToolHandlerResult(success=False, error=error, result=self.createErrorResult(error))
                
                all_directives = dir_resp.json()
                
                for directive in all_directives:
                    directive_name = directive["name"]
                    directive_id = directive["id"]
                    
                    # Get latest version info from registry
                    ver_resp = await client.get(
                        f"{self.supabase_url}/rest/v1/directive_versions",
                        params={
                            "directive_id": f"eq.{directive_id}",
                            "is_latest": "eq.true",
                            "select": "version,content_hash"
                        },
                        headers=headers
                    )
                    
                    versions = ver_resp.json() if ver_resp.status_code == 200 else []
                    if not versions:
                        errors.append(f"{directive_name} (no version)")
                        continue
                    
                    registry_version = versions[0]["version"]
                    registry_hash = versions[0].get("content_hash")
                    
                    # Check if file actually exists on disk
                    # Update function only handles "core" category
                    file_path = path / "core" / f"{directive_name}.md"
                    file_exists = file_path.exists()
                    file_was_missing = not file_exists
                    
                    # For user space, check lock file to see if update needed
                    if to == "user":
                        should_update, reason = needs_update(
                            directive_name, registry_version, registry_hash
                        )
                        
                        # If file is missing, we need to download it even if lock says up-to-date
                        if not should_update and file_exists:
                            skipped.append(f"{directive_name}@{registry_version}")
                            continue
                        elif not file_exists:
                            # File missing - need to download
                            should_update = True
                            reason = "file_missing"
                    
                    # Get current local version for reporting
                    locked = get_locked_directive(directive_name) if to == "user" else None
                    local_version = locked.get("version") if locked else None
                    
                    # Download
                    result = await self._download(directive_name, None, to)
                    
                    if result.success and result.result:
                        if local_version is None:
                            added.append(f"{directive_name}@{registry_version}")
                        elif file_was_missing:
                            # File was missing, restored it
                            updated.append(f"{directive_name}: {local_version} → {registry_version} (restored)")
                        else:
                            updated.append(f"{directive_name}: {local_version} → {registry_version}")
                    else:
                        errors.append(directive_name)
            
            return ToolHandlerResult(
                success=True,
                result=self.createSuccessResult({
                    "synced": len(added) + len(updated),
                    "added": added,
                    "updated": updated,
                    "skipped": skipped,
                    "errors": errors,
                    "destination": "~/.context-kiwi/directives/core/" if to == "user" else ".ai/directives/core/",
                    "note": "Updated core directives only. Other categories use their own subdirectories."
                })
            )
            
        except httpx.RequestError as e:
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Failed to connect to registry: {str(e)}"
            )
            return ToolHandlerResult(success=False, error=error, result=self.createErrorResult(error))
    
    def _get_local_version(self, directive: str, base_path: Path | None = None) -> str | None:
        """Get version of locally installed directive."""
        import re
        
        paths_to_check = []
        if base_path:
            # base_path is already the directives root, search recursively in all categories/subcategories
            for file_path in base_path.rglob(f"{directive}.md"):
                paths_to_check.append(file_path)
        else:
            # Search in both project and user space, all categories recursively
            for base in [self.project_path, self.user_path]:
                if base.exists():
                    for file_path in base.rglob(f"{directive}.md"):
                        paths_to_check.append(file_path)
        
        for path in paths_to_check:
            if path.exists():
                content = path.read_text()
                # Look for version in directive attributes
                match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        
        return None

