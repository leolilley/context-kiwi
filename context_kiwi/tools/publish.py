"""
Publish Tool

Upload local directives to the registry.
"""

import hashlib
import os
from pathlib import Path
from typing import Any
import httpx
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


class PublishTool(BaseTool):
    """
    Upload local directive to the registry.
    
    Sources:
    - "project" (default): .ai/directives/custom/
    - "user": ~/.context-kiwi/directives/custom/
    """
    
    def __init__(self, logger: Logger, registry_url: str | None = None):
        super().__init__(logger, {
            'category': ToolCategory.CORE,
            'requiresAuth': True,  # Needs API key
            'rateLimited': True
        })
        from context_kiwi.config import get_supabase_url
        self.supabase_url = get_supabase_url()
        from context_kiwi.config import get_user_home
        self.user_path = get_user_home() / "directives"
    
    def _get_project_path(self, project_path: str | None) -> Path:
        """Get project directives path."""
        root = Path(project_path) if project_path else Path.cwd()
        return root / ".ai" / "directives"
    
    @property
    def name(self) -> str:
        return "publish"
    
    @property
    def description(self) -> str:
        return """Upload a local directive to the public registry.

REQUIRED: directive (name), version (semver like "1.0.0"), project_path (when source="project")
OPTIONAL: source ("project" or "user")

Requires: CONTEXT_KIWI_API_KEY environment variable

Sources:
- source="project": .ai/directives/{category}/{name}.md (default)
  ⚠️  REQUIRES project_path parameter!
- source="user": ~/.context-kiwi/directives/{category}/{name}.md
  ✓ project_path not needed

Examples:
- publish("my_directive", "1.0.0", project_path="/home/user/myproject")
- publish("my_directive", "1.0.0", source="user")

CRITICAL: When source="project", you MUST provide project_path. Use the workspace root path.
Common mistake: Forgetting project_path or CONTEXT_KIWI_API_KEY."""
    
    @property
    def inputSchema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directive": {
                    "type": "string",
                    "description": "Name of the directive to publish"
                },
                "version": {
                    "type": "string",
                    "description": "Version to publish (semver)"
                },
                "source": {
                    "type": "string",
                    "enum": ["project", "user"],
                    "description": "Where to find the directive",
                    "default": "project"
                },
                "project_path": {
                    "type": "string",
                    "description": "⚠️  REQUIRED when source='project': Full absolute path to project root directory. Example: '/home/user/myproject'. Use workspace path. DO NOT use relative paths. This is CRITICAL - without it, files won't be found correctly!"
                }
            },
            "required": ["directive", "version"]
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        """Execute publish."""
        try:
            directive = input.get("directive")
            version = input.get("version")
            source = input.get("source", "project")
            project_path = input.get("project_path")
            
            # Validate project_path when publishing from project
            if source == "project" and not project_path:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message="CRITICAL: project_path is REQUIRED when source='project'. Provide the full workspace path (e.g., '/home/user/myproject'). Without this, files won't be found correctly!"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # Set project path for this request
            self.project_path = self._get_project_path(project_path)
            
            if not directive or not version:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message="Both directive and version are required"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # Check for API key (CONTEXT_KIWI_API_KEY or SUPABASE_SECRET_KEY)
            api_key = os.getenv("CONTEXT_KIWI_API_KEY") or os.getenv("SUPABASE_SECRET_KEY")
            if not api_key:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message="CONTEXT_KIWI_API_KEY or SUPABASE_SECRET_KEY environment variable is required for publishing"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # Find the directive file
            base_path = self.project_path if source == "project" else self.user_path
            
            # If project source and no explicit project_path, try to auto-detect
            if source == "project" and not project_path:
                # Try to find .ai/ directory in current working directory or parent
                cwd = Path.cwd()
                potential_paths = [
                    cwd / ".ai" / "directives",
                    cwd.parent / ".ai" / "directives",
                ]
                for potential in potential_paths:
                    if potential.exists():
                        base_path = potential.parent.parent  # Go back to project root
                        self.project_path = base_path / ".ai" / "directives"
                        break
            
            file_path = self._find_directive_file(directive, base_path)
            
            if not file_path:
                # Provide helpful error message with search suggestions
                searched_path = base_path
                if source == "project":
                    searched_path = base_path / ".ai" / "directives" if base_path.name != "directives" else base_path
                
                error_msg = (
                    f"Directive '{directive}' not found in {source} space.\n"
                    f"Searched in: {searched_path}/ (including subdirectories)\n\n"
                )
                
                if source == "project":
                    error_msg += (
                        "Common locations:\n"
                        f"  - {searched_path}/core/{directive}.md\n"
                        f"  - {searched_path}/custom/{directive}.md\n\n"
                        "Tip: If your workspace is not the project root, provide 'project_path' parameter."
                    )
                else:
                    error_msg += (
                        f"Tip: User space directives should be in: {self.user_path}/"
                    )
                
                error = ToolError(
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=error_msg
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # Read content
            content = file_path.read_text()
            
            # Validate directive
            validation = self._validate_directive(content)
            if not validation["valid"]:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message=f"Directive validation failed: {validation['errors']}"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # CRITICAL: Validate that user-provided version matches content version
            content_version = validation.get("metadata", {}).get("version")
            if content_version and content_version != version:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message=(
                        f"Version mismatch: you're publishing as '{version}' but the directive content "
                        f"has version='{content_version}'. Please update the version attribute in "
                        f"your directive file to match, or use version='{content_version}'."
                    )
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # Publish to registry
            return await self._publish_to_registry(
                name=directive,
                version=version,
                content=content,
                api_key=api_key,
                metadata=validation.get("metadata", {})
            )
            
        except Exception as e:
            self.logger.error(f"Publish error: {e}")
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Publish failed: {str(e)}"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error)
            )
    
    def _find_directive_file(self, name: str, base_path: Path) -> Path | None:
        """Find directive file in the given path. Supports nested folder structures."""
        from context_kiwi.utils.directive_finder import find_directive_file
        return find_directive_file(name, base_path, verify_name=True)
    
    def _escape_nested_cdata(self, xml_content: str) -> str:
        """
        Escape nested CDATA blocks for XML validation.
        
        XML doesn't support nested CDATA - when you have:
            <template><![CDATA[
                <action><![CDATA[content]]></action>
            ]]></template>
        
        The inner ]]> terminates the outer CDATA prematurely, causing parse errors.
        
        For validation purposes, we process CDATA sections character by character,
        tracking nesting depth, and escape any nested CDATA markers.
        """
        result = []
        i = 0
        cdata_start = '<![CDATA['
        cdata_end = ']]>'
        
        while i < len(xml_content):
            # Check for CDATA start
            if xml_content[i:i+len(cdata_start)] == cdata_start:
                # Found CDATA start, now find the matching end
                # accounting for any nested CDATA markers
                result.append(cdata_start)
                i += len(cdata_start)
                depth = 1
                
                while i < len(xml_content) and depth > 0:
                    if xml_content[i:i+len(cdata_start)] == cdata_start:
                        # Nested CDATA start - escape it
                        result.append('&lt;![CDATA[')
                        i += len(cdata_start)
                        depth += 1
                    elif xml_content[i:i+len(cdata_end)] == cdata_end:
                        depth -= 1
                        if depth == 0:
                            # This is the closing of our outermost CDATA
                            result.append(cdata_end)
                        else:
                            # Nested CDATA end - escape it
                            result.append(']]&gt;')
                        i += len(cdata_end)
                    else:
                        result.append(xml_content[i])
                        i += 1
            else:
                result.append(xml_content[i])
                i += 1
        
        return ''.join(result)
    
    def _validate_directive(self, content: str) -> dict[str, Any]:
        """Validate directive content before publishing."""
        import re
        import xml.etree.ElementTree as ET
        
        errors = []
        metadata = {}
        
        # Extract XML from markdown - find <directive>...</directive> directly
        start_pattern = r'<directive[^>]*>'
        start_match = re.search(start_pattern, content)
        if not start_match:
            return {"valid": False, "errors": ["No <directive> tag found"]}
        
        end_tag = '</directive>'
        end_idx = content.rfind(end_tag)
        if end_idx == -1:
            return {"valid": False, "errors": ["No closing </directive> tag found"]}
        
        xml_content = content[start_match.start():end_idx + len(end_tag)]
        
        # Handle nested CDATA blocks: XML doesn't support nested CDATA, so when a directive
        # contains a template with example CDATA blocks inside, the inner ]]> terminates
        # the outer CDATA prematurely. For validation purposes, we escape nested CDATA
        # by replacing inner CDATA sections with placeholders.
        xml_content = self._escape_nested_cdata(xml_content)
        
        # Parse XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            return {"valid": False, "errors": [f"Invalid XML: {e}"]}
        
        # Check required elements
        if root.tag != "directive":
            errors.append("Root element must be <directive>")
        
        # Check name attribute
        name = root.get("name")
        if not name:
            errors.append("Directive must have a name attribute")
        else:
            metadata["name"] = name
        
        # Check version attribute
        version = root.get("version")
        if not version:
            errors.append("Directive must have a version attribute")
        else:
            metadata["version"] = version
        
        # Check for metadata/description
        metadata_elem = root.find("metadata")
        if metadata_elem is not None:
            desc_elem = metadata_elem.find("description")
            if desc_elem is not None and desc_elem.text:
                metadata["description"] = desc_elem.text.strip()
            else:
                errors.append("Directive should have metadata/description")
        else:
            errors.append("Directive should have metadata section")
        
        # Check for process OR content section (content for info/help directives)
        process = root.find("process")
        has_content = root.find("content") is not None
        if process is None and not has_content:
            errors.append("Directive must have a process or content section")
        elif process is not None:
            steps = process.findall("step")
            if len(steps) == 0:
                errors.append("Process must have at least one step")
        
        # Check for context/tech_stack
        context_elem = root.find("context")
        if context_elem is not None:
            tech_stack_elem = context_elem.find("tech_stack")
            if tech_stack_elem is not None and tech_stack_elem.text:
                # Parse tech stack (comma-separated or single value)
                ts_text = tech_stack_elem.text.strip()
                if "," in ts_text:
                    metadata["tech_stack"] = [t.strip() for t in ts_text.split(",")]
                else:
                    metadata["tech_stack"] = [ts_text] if ts_text != "any" else []
        
        # Get category from metadata
        if metadata_elem is not None:
            cat_elem = metadata_elem.find("category")
            if cat_elem is not None and cat_elem.text:
                metadata["category"] = cat_elem.text.strip()
        
        if errors:
            return {"valid": False, "errors": errors}
        
        return {"valid": True, "metadata": metadata}
    
    async def _publish_to_registry(
        self,
        name: str,
        version: str,
        content: str,
        api_key: str,
        metadata: dict[str, Any]
    ) -> ToolHandlerResult:
        """Publish directive to Supabase registry."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "apikey": api_key,
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                }
                
                # Check if directive exists
                check_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/directives",
                    params={"name": f"eq.{name}", "select": "id"},
                    headers=headers
                )
                
                existing = check_resp.json() if check_resp.status_code == 200 else []
                
                if existing:
                    # Update existing directive
                    directive_id = existing[0]["id"]
                    
                    # Insert new version
                    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                    version_resp = await client.post(
                        f"{self.supabase_url}/rest/v1/directive_versions",
                        json={
                            "directive_id": directive_id,
                            "version": version,
                            "content": content,
                            "content_hash": content_hash,
                            "changelog": metadata.get("changelog", ""),
                            "is_latest": True
                        },
                        headers=headers
                    )
                    
                    if version_resp.status_code not in (200, 201):
                        error = ToolError(
                            code=MCPErrorCode.INTERNAL_ERROR,
                            message=f"Failed to create version: {version_resp.text}"
                        )
                        return ToolHandlerResult(success=False, error=error, result=self.createErrorResult(error))
                    
                    # Unset previous latest
                    await client.patch(
                        f"{self.supabase_url}/rest/v1/directive_versions",
                        params={
                            "directive_id": f"eq.{directive_id}",
                            "version": f"neq.{version}",
                            "is_latest": "eq.true"
                        },
                        json={"is_latest": False},
                        headers=headers
                    )
                else:
                    # Create new directive
                    create_resp = await client.post(
                        f"{self.supabase_url}/rest/v1/directives",
                        json={
                            "name": name,
                            "category": metadata.get("category", "actions"),  # Default to "actions" for user directives (not "core" which is reserved)
                            "description": metadata.get("description", ""),
                            "is_official": True,
                            "tech_stack": metadata.get("tech_stack", [])
                        },
                        headers=headers
                    )
                    
                    if create_resp.status_code not in (200, 201):
                        error = ToolError(
                            code=MCPErrorCode.INTERNAL_ERROR,
                            message=f"Failed to create directive: {create_resp.text}"
                        )
                        return ToolHandlerResult(success=False, error=error, result=self.createErrorResult(error))
                    
                    directive_id = create_resp.json()[0]["id"]
                    
                    # Create initial version
                    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                    await client.post(
                        f"{self.supabase_url}/rest/v1/directive_versions",
                        json={
                            "directive_id": directive_id,
                            "version": version,
                            "content": content,
                            "content_hash": content_hash,
                            "is_latest": True
                        },
                        headers=headers
                    )
                
                return ToolHandlerResult(
                    success=True,
                    result=self.createSuccessResult({
                        "status": "published",
                        "name": name,
                        "version": version,
                        "message": f"Published {name}@{version} to registry"
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

