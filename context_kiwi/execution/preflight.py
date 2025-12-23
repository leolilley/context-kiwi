"""
Pre-flight validation utilities.

Run checks before executing directives to fail fast:
- Credential validation (env vars exist)
- Input validation (JSON Schema)
- Dependency checks (packages, files, commands)
"""

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)


def check_credentials(required_keys: List[str]) -> Dict[str, Any]:
    """
    Verify required environment variables exist.
    
    Args:
        required_keys: List of environment variable names to check
        
    Returns:
        {"status": "pass"} or {"status": "fail", "missing": [...]}
        
    Example:
        result = check_credentials(["OPENAI_API_KEY", "SUPABASE_URL"])
        if result["status"] == "fail":
            print(f"Missing: {result['missing']}")
    """
    missing = [k for k in required_keys if not os.getenv(k)]
    
    if missing:
        logger.warning(f"Missing credentials: {missing}")
        return {"status": "fail", "missing": missing}
    
    logger.debug(f"All credentials present: {required_keys}")
    return {"status": "pass"}


def check_packages(packages: List[Dict[str, str]], project_path: Path | None = None) -> Dict[str, Any]:
    """
    Check if required packages are installed.
    
    Args:
        packages: List of package specs like:
            {"name": "zustand", "manager": "npm"}
            {"name": "requests", "manager": "pip"}
        project_path: Project root for checking local packages
        
    Returns:
        {"status": "pass"} or {"status": "fail", "missing": [...]}
    """
    missing = []
    cwd = str(project_path) if project_path else None
    
    for pkg in packages:
        name = pkg.get("name", "")
        manager = pkg.get("manager", "npm")
        
        try:
            if manager == "npm":
                # Check package.json dependencies or node_modules
                result = subprocess.run(
                    ["npm", "list", name, "--depth=0"],
                    capture_output=True, text=True, cwd=cwd, timeout=10
                )
                if result.returncode != 0:
                    missing.append(f"{name} (npm)")
                    
            elif manager == "pip":
                result = subprocess.run(
                    ["pip", "show", name],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    missing.append(f"{name} (pip)")
                    
            elif manager == "cargo":
                # Check Cargo.toml
                cargo_toml = Path(cwd or ".") / "Cargo.toml"
                if cargo_toml.exists():
                    content = cargo_toml.read_text()
                    if name not in content:
                        missing.append(f"{name} (cargo)")
                else:
                    missing.append(f"{name} (cargo - no Cargo.toml)")
                    
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Package check failed for {name}: {e}")
            # Don't fail on check errors, just warn
            
    if missing:
        logger.warning(f"Missing packages: {missing}")
        return {"status": "fail", "missing": missing}
    
    return {"status": "pass"}


def check_files(files: List[str], project_path: Path | None = None) -> Dict[str, Any]:
    """
    Check if required files exist.
    
    Args:
        files: List of file paths (relative to project or absolute)
        project_path: Project root for relative paths
        
    Returns:
        {"status": "pass"} or {"status": "fail", "missing": [...]}
    """
    missing = []
    base = project_path or Path.cwd()
    
    for file_path in files:
        path = Path(file_path)
        if not path.is_absolute():
            path = base / path
        
        if not path.exists():
            missing.append(str(file_path))
    
    if missing:
        logger.warning(f"Missing files: {missing}")
        return {"status": "fail", "missing": missing}
    
    return {"status": "pass"}


def check_commands(commands: List[str]) -> Dict[str, Any]:
    """
    Check if required commands are available.
    
    Args:
        commands: List of command names (e.g., ["docker", "kubectl"])
        
    Returns:
        {"status": "pass"} or {"status": "fail", "missing": [...]}
    """
    missing = []
    
    for cmd in commands:
        if not shutil.which(cmd):
            missing.append(cmd)
    
    if missing:
        logger.warning(f"Missing commands: {missing}")
        return {"status": "fail", "missing": missing}
    
    return {"status": "pass"}


def validate_inputs(inputs: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate inputs against JSON Schema.
    
    Args:
        inputs: Dictionary of input values
        schema: JSON Schema for validation
        
    Returns:
        {"valid": True} or {"valid": False, "errors": [...]}
        
    Example:
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "count": {"type": "integer", "minimum": 1}
            }
        }
        result = validate_inputs({"name": "test", "count": 5}, schema)
    """
    try:
        validate(instance=inputs, schema=schema)
        logger.debug("Input validation passed")
        return {"valid": True}
    except ValidationError as e:
        logger.warning(f"Input validation failed: {e.message}")
        return {
            "valid": False,
            "errors": [e.message],
            "path": list(e.path) if e.path else []
        }


def validate_inputs_simple(inputs: Dict[str, Any], rules: List[Dict]) -> Dict[str, Any]:
    """
    Validate inputs against simple rules (fallback if no JSON Schema).
    
    Args:
        inputs: Dictionary of input values
        rules: List of validation rules
        
    Rules format:
        {"field": "name", "required": True}
        {"field": "count", "min": 1, "max": 10000}
        {"field": "email", "pattern": r"^[\\w.-]+@[\\w.-]+\\.\\w+$"}
        
    Returns:
        {"valid": True} or {"valid": False, "errors": [...]}
    """
    errors = []
    
    for rule in rules:
        field = rule.get("field", "")
        value = inputs.get(field) if field else None
        
        # Required check
        if rule.get("required") and value is None:
            errors.append(f"'{field}' is required but missing")
            continue
        
        # Skip other checks if value is None and not required
        if value is None:
            continue
        
        # Type check
        expected_type = rule.get("type")
        if expected_type:
            type_map = {
                "string": str, 
                "integer": int, 
                "float": (int, float), 
                "boolean": bool,
                "array": list,
                "object": dict
            }
            if expected_type in type_map and not isinstance(value, type_map[expected_type]):
                errors.append(f"'{field}' must be {expected_type}, got {type(value).__name__}")
        
        # Min/max check (for numbers)
        if "min" in rule and isinstance(value, (int, float)) and value < rule["min"]:
            errors.append(f"'{field}' must be >= {rule['min']}, got {value}")
        if "max" in rule and isinstance(value, (int, float)) and value > rule["max"]:
            errors.append(f"'{field}' must be <= {rule['max']}, got {value}")
        
        # Pattern check (for strings)
        if "pattern" in rule and isinstance(value, str):
            if not re.match(rule["pattern"], value):
                errors.append(f"'{field}' doesn't match required pattern")
        
        # Enum check
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"'{field}' must be one of {rule['enum']}, got '{value}'")
    
    if errors:
        logger.warning(f"Input validation failed: {errors}")
        return {"valid": False, "errors": errors}
    
    return {"valid": True}


def run_preflight(
    inputs: Dict[str, Any],
    required_credentials: List[str] | None = None,
    input_schema: Dict[str, Any] | None = None,
    validation_rules: List[Dict] | None = None,
    required_packages: List[Dict[str, str]] | None = None,
    required_files: List[str] | None = None,
    required_commands: List[str] | None = None,
    project_path: Path | None = None,
) -> Dict[str, Any]:
    """
    Run all preflight checks.
    
    Args:
        inputs: User-provided inputs
        required_credentials: List of required env vars
        input_schema: JSON Schema for input validation (preferred)
        validation_rules: Simple validation rules (fallback)
        required_packages: List of package specs [{"name": "x", "manager": "npm"}]
        required_files: List of required file paths
        required_commands: List of required CLI commands
        project_path: Project root for relative path resolution
        
    Returns:
        {
            "pass": bool,
            "checks": {
                "credentials": {...},
                "inputs": {...},
                "packages": {...},
                "files": {...},
                "commands": {...}
            },
            "blockers": [...],
            "warnings": [...]
        }
        
    Example:
        result = run_preflight(
            inputs={"name": "my-component"},
            required_credentials=["OPENAI_API_KEY"],
            required_packages=[{"name": "zustand", "manager": "npm"}],
            required_files=["tsconfig.json"],
            input_schema={
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string"}}
            }
        )
        
        if not result["pass"]:
            print(f"Blockers: {result['blockers']}")
    """
    checks = {}
    blockers = []
    warnings = []
    
    # Credential check
    if required_credentials:
        cred_result = check_credentials(required_credentials)
        checks["credentials"] = cred_result
        if cred_result["status"] == "fail":
            blockers.append(f"Missing credentials: {cred_result['missing']}")
    
    # Input validation (prefer JSON Schema, fallback to simple rules)
    if input_schema:
        input_result = validate_inputs(inputs, input_schema)
        checks["inputs"] = input_result
        if not input_result["valid"]:
            blockers.extend(input_result["errors"])
    elif validation_rules:
        input_result = validate_inputs_simple(inputs, validation_rules)
        checks["inputs"] = input_result
        if not input_result["valid"]:
            blockers.extend(input_result["errors"])
    
    # Package checks (warnings, not blockers - package might be global)
    if required_packages:
        pkg_result = check_packages(required_packages, project_path)
        checks["packages"] = pkg_result
        if pkg_result["status"] == "fail":
            warnings.append(f"Missing packages (install suggested): {pkg_result['missing']}")
    
    # File checks (blockers - required files must exist)
    if required_files:
        file_result = check_files(required_files, project_path)
        checks["files"] = file_result
        if file_result["status"] == "fail":
            blockers.append(f"Missing required files: {file_result['missing']}")
    
    # Command checks (blockers - required commands must be available)
    if required_commands:
        cmd_result = check_commands(required_commands)
        checks["commands"] = cmd_result
        if cmd_result["status"] == "fail":
            blockers.append(f"Missing required commands: {cmd_result['missing']}")
    
    # Summary
    all_pass = len(blockers) == 0
    
    result = {
        "pass": all_pass,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings
    }
    
    if all_pass:
        if warnings:
            logger.info(f"Preflight passed with warnings: {warnings}")
        else:
            logger.info("Preflight checks passed")
    else:
        logger.warning(f"Preflight checks failed: {blockers}")
    
    return result

