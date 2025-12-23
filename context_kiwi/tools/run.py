"""
Run Tool

Execute a directive from local space with preflight validation and context loading.
"""

import json
import time
from pathlib import Path
from typing import Any

from context_kiwi.directives import DirectiveLoader
from context_kiwi.execution.analytics import log_run
from context_kiwi.execution.context import load_context
from context_kiwi.execution.preflight import run_preflight
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


class RunTool(BaseTool):
    """
    Execute a directive with preflight validation and context loading.
    
    Only runs directives from LOCAL space (project > user).
    Use `get` to download from registry first.
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
        return "run"
    
    @property
    def description(self) -> str:
        return """Execute a directive that exists LOCALLY (not from registry).

REQUIRED: directive (name)
OPTIONAL: inputs (dict), project_path (use if workspace != current directory)

Search order: .ai/directives/custom/ → .ai/directives/core/ → ~/.context-kiwi/directives/core/

Examples:
- run("init") - Initialize project (first time setup)
- run("create_directive", {"name": "my_directive", "description": "..."})
- run("my_directive", {"param": "value"}, project_path="/path/to/project")

IMPORTANT:
- Only runs LOCAL directives. Use get() first to download from registry.
- Returns directive + project context. YOU execute the steps, not the tool.
- Core directives (init, create_directive, etc.) are pre-installed in ~/.context-kiwi/

Common mistake: Trying to run() a directive that only exists in registry (use get() first)."""
    
    @property
    def inputSchema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directive": {
                    "type": "string",
                    "description": "REQUIRED: Directive name (must exist locally, use get() first if from registry)"
                },
                "inputs": {
                    "type": "object",
                    "description": "Optional: Input parameters as dict (e.g., {'name': 'Button', 'type': 'component'})",
                    "default": {}
                },
                "project_path": {
                    "type": "string",
                    "description": "CRITICAL: Project root path if workspace != current directory. Example: '/home/user/myproject'. Defaults to current working directory."
                }
            },
            "required": ["directive"]
        }
    
    async def execute(self, input: ToolInput, context: ToolContext) -> ToolHandlerResult:
        """Execute run."""
        start_time = time.time()
        directive_name = ""
        proj_path: Path | None = None
        
        try:
            directive_name = input.get("directive", "")
            inputs = input.get("inputs", {})
            project_path = input.get("project_path")
            proj_path = Path(project_path) if project_path else None
            
            loader = self._get_loader(project_path)
            
            if not directive_name:
                error = ToolError(
                    code=MCPErrorCode.INVALID_INPUT,
                    message="Directive name is required"
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # 1. Load directive from LOCAL only
            directive = loader.load_local(directive_name)
            
            if not directive:
                error = ToolError(
                    code=MCPErrorCode.RESOURCE_NOT_FOUND,
                    message=f"Directive '{directive_name}' not found locally. "
                            f"Use search(source='registry') to find it, then get() to download."
                )
                return ToolHandlerResult(
                    success=False,
                    error=error,
                    result=self.createErrorResult(error)
                )
            
            # 2. Run preflight checks
            preflight_result = self._run_preflight(directive, inputs or {}, proj_path)
            
            # Include warnings in response even if pass
            warnings = preflight_result.get("warnings", [])
            
            if not preflight_result["pass"]:
                # Log validation failure
                log_run(
                    directive=directive_name,
                    status="validation_failed",
                    duration_sec=time.time() - start_time,
                    inputs=inputs or {},
                    project=str(proj_path) if proj_path else None,
                    error=str(preflight_result.get("blockers", []))
                )
                return ToolHandlerResult(
                    success=True,  # Not an error, just validation failure
                    result=self.createSuccessResult({
                        "status": "validation_failed",
                        "directive": directive_name,
                        "blockers": preflight_result["blockers"],
                        "checks": preflight_result["checks"]
                    })
                )
            
            # 3. Load project context
            project_context = load_context(proj_path)
            
            # Special handling for init directive - context won't exist yet (this is expected)
            if directive_name == "init" and project_context.get("setup_required"):
                project_context = {
                    "note": "No .ai/ directory yet - this directive will create it. This is expected and normal.",
                    "expected": True
                }
            
            # 4. Log directive loaded (LLM will execute it)
            log_run(
                directive=directive_name,
                status="loaded",
                duration_sec=time.time() - start_time,
                inputs=inputs or {},
                project=str(proj_path) if proj_path else None,
                metadata={"source": directive.source, "version": directive.version}
            )
            
            # 5. Build response
            response_data: dict[str, Any] = {
                "status": "ready",
                "directive": {
                    "name": directive.name,
                    "version": directive.version,
                    "description": directive.description,
                    "source": directive.source,
                    "content": directive.content,
                    "parsed": directive.parsed
                },
                "context": project_context,
                "inputs": inputs,
                "instructions": (
                    "IMPORTANT: Status 'ready' means the directive is loaded and ready for YOU to execute. "
                    "Read the directive's <process> section and follow each step. "
                    "The directive contains the instructions - you need to execute them now. "
                    "Use the project context (if available) to match coding patterns and conventions. "
                    "The directive's <inputs> section shows what parameters are available."
                )
            }
            
            # Add warnings if any (e.g., missing optional packages)
            if warnings:
                response_data["warnings"] = warnings
            
            # Add validation info if present
            validation = directive.parsed.get("validation") if directive.parsed else None
            if validation:
                response_data["validation"] = {
                    "note": "After generating code, run these checks:",
                    "checks": validation
                }
            
            # Add dependencies info if present
            dependencies = directive.parsed.get("dependencies") if directive.parsed else None
            if dependencies:
                response_data["dependencies"] = dependencies
            
            # 6. Return directive + context for LLM
            return ToolHandlerResult(
                success=True,
                result=self.createSuccessResult(response_data)
            )
            
        except Exception as e:
            self.logger.error(f"Run error: {e}")
            # Log the error
            if directive_name:
                log_run(
                    directive=directive_name,
                    status="error",
                    duration_sec=time.time() - start_time,
                    inputs={},
                    project=str(proj_path) if proj_path else None,
                    error=str(e)
                )
            error = ToolError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Run failed: {str(e)}"
            )
            return ToolHandlerResult(
                success=False,
                error=error,
                result=self.createErrorResult(error)
            )
    
    def _run_preflight(
        self, directive, inputs: dict[str, Any], project_path: Path | None = None
    ) -> dict[str, Any]:
        """Run preflight checks for a directive.
        
        Parses <preflight> section from directive XML:
        
        <preflight>
            <credentials>
                <env>OPENAI_API_KEY</env>
            </credentials>
            <packages>
                <package manager="npm">zustand</package>
                <package manager="pip">requests</package>
            </packages>
            <files>
                <file>tsconfig.json</file>
            </files>
            <commands>
                <command>docker</command>
            </commands>
        </preflight>
        """
        from pathlib import Path as PathLib
        
        parsed = directive.parsed or {}
        
        # Extract validation config from directive
        input_schema = None
        required_credentials: list[str] = []
        required_packages: list[dict[str, str]] = []
        required_files: list[str] = []
        required_commands: list[str] = []
        
        # Check for JSON Schema in inputs
        inputs_section = parsed.get("inputs", {})
        if isinstance(inputs_section, dict):
            schema = inputs_section.get("schema")
            if schema:
                if isinstance(schema, str):
                    try:
                        input_schema = json.loads(schema)
                    except json.JSONDecodeError:
                        pass
                elif isinstance(schema, dict):
                    input_schema = schema
        
        # Parse <preflight> section
        preflight_section = parsed.get("preflight", {})
        if isinstance(preflight_section, dict):
            # Credentials (env vars)
            creds = preflight_section.get("credentials", {})
            if isinstance(creds, dict):
                env_list = creds.get("env", [])
                if isinstance(env_list, str):
                    required_credentials = [env_list]
                elif isinstance(env_list, list):
                    required_credentials = [e for e in env_list if isinstance(e, str)]
            
            # Packages
            packages = preflight_section.get("packages", {})
            if isinstance(packages, dict):
                pkg_list = packages.get("package", [])
                if isinstance(pkg_list, dict):
                    pkg_list = [pkg_list]  # Single package
                if isinstance(pkg_list, list):
                    for pkg in pkg_list:
                        if isinstance(pkg, dict):
                            name = pkg.get("_text", "")
                            manager = pkg.get("_attrs", {}).get("manager", "npm")
                            if name:
                                required_packages.append({"name": name, "manager": manager})
                        elif isinstance(pkg, str):
                            required_packages.append({"name": pkg, "manager": "npm"})
            
            # Files
            files = preflight_section.get("files", {})
            if isinstance(files, dict):
                file_list = files.get("file", [])
                if isinstance(file_list, str):
                    required_files = [file_list]
                elif isinstance(file_list, list):
                    required_files = [f for f in file_list if isinstance(f, str)]
            
            # Commands
            commands = preflight_section.get("commands", {})
            if isinstance(commands, dict):
                cmd_list = commands.get("command", [])
                if isinstance(cmd_list, str):
                    required_commands = [cmd_list]
                elif isinstance(cmd_list, list):
                    required_commands = [c for c in cmd_list if isinstance(c, str)]
        
        # Also check legacy preflight_checks section
        legacy_preflight = parsed.get("preflight_checks", {})
        if isinstance(legacy_preflight, dict):
            creds = legacy_preflight.get("required_credentials", {})
            if isinstance(creds, dict):
                cred_list = creds.get("credential", [])
                if isinstance(cred_list, str):
                    required_credentials.append(cred_list)
                elif isinstance(cred_list, list):
                    required_credentials.extend(cred_list)
        
        return run_preflight(
            inputs=inputs,
            required_credentials=required_credentials or None,
            input_schema=input_schema,
            required_packages=required_packages or None,
            required_files=required_files or None,
            required_commands=required_commands or None,
            project_path=project_path
        )

