"""
delete_directive - Delete a directive from registry, user space, project space, or all tiers.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from context_kiwi.db.directives import DirectiveDB
from context_kiwi.mcp_types import ToolContext
from context_kiwi.utils.directive_finder import find_directive_file
from context_kiwi.config.lockfile import remove_locked_directive
from context_kiwi.config import get_user_home


def _get_project_path(project_path: Optional[str] = None) -> Path:
    """Get project directives path."""
    root = Path(project_path) if project_path else Path.cwd()
    return root / ".ai" / "directives"


def _get_user_path() -> Path:
    """Get user directives path."""
    return get_user_home() / "directives"


def _delete_from_project(
    name: str, 
    project_path: Path,
    cleanup_empty_dirs: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """
    Delete directive from project space.
    
    Returns:
        (success: bool, message: str, file_path: str | None)
    """
    file_path = find_directive_file(name, project_path)
    
    if not file_path:
        return (True, f"Directive not found in project space", None)
    
    try:
        file_path_str = str(file_path)
        file_path.unlink()
        
        # Clean up empty directories if requested
        if cleanup_empty_dirs:
            _cleanup_empty_dirs(file_path, project_path)
        
        return (True, f"Deleted from project space: {file_path_str}", file_path_str)
    except PermissionError:
        return (False, f"Permission denied: cannot delete {file_path}", str(file_path))
    except Exception as e:
        return (False, f"Failed to delete from project space: {str(e)}", str(file_path))


def _delete_from_user(
    name: str,
    user_path: Path,
    cleanup_empty_dirs: bool = False
) -> Tuple[bool, str, Optional[str]]:
    """
    Delete directive from user space and lockfile.
    
    Returns:
        (success: bool, message: str, file_path: str | None)
    """
    file_path = find_directive_file(name, user_path)
    
    if not file_path:
        # Still try to remove from lockfile (in case file was manually deleted)
        try:
            remove_locked_directive(name)
            return (True, f"Directive not found in user space (lockfile entry removed)", None)
        except Exception:
            return (True, f"Directive not found in user space", None)
    
    try:
        file_path_str = str(file_path)
        file_path.unlink()
        
        # Remove from lockfile
        try:
            remove_locked_directive(name)
        except Exception as e:
            # Log warning but don't fail - file is deleted
            pass
        
        # Clean up empty directories if requested
        if cleanup_empty_dirs:
            _cleanup_empty_dirs(file_path, user_path)
        
        return (True, f"Deleted from user space: {file_path_str}", file_path_str)
    except PermissionError:
        return (False, f"Permission denied: cannot delete {file_path}", str(file_path))
    except Exception as e:
        return (False, f"Failed to delete from user space: {str(e)}", str(file_path))


def _delete_from_registry(name: str, db: DirectiveDB) -> Tuple[bool, str]:
    """
    Delete directive from registry (database).
    
    Returns:
        (success: bool, message: str)
    """
    try:
        # Check it exists first
        existing = db.get(name)
        if not existing:
            return (True, f"Directive not found in registry")
        
        success = db.delete(name)
        
        if success:
            return (True, f"Deleted from registry: {name} and all versions")
        else:
            return (False, f"Failed to delete from registry")
    except Exception as e:
        return (False, f"Failed to delete from registry: {str(e)}")


def _cleanup_empty_dirs(file_path: Path, base_path: Path) -> None:
    """
    Remove empty parent directories after file deletion.
    Stops at base_path to preserve category structure.
    Preserves category-level directories (first level under base_path) when base_path is .ai/directives.
    
    Args:
        file_path: Path to the deleted file
        base_path: Base directory (stop cleanup here)
    """
    current = file_path.parent
    
    # Get category-level directory (first level under base_path)
    # Only preserve if base_path is the directives root (not a category folder)
    category_level = None
    try:
        relative = current.relative_to(base_path)
        # Only preserve category level if base_path ends with "directives"
        # (meaning we're at .ai/directives, not .ai/directives/patterns)
        if base_path.name == "directives" and relative.parts:
            category_level = base_path / relative.parts[0]
    except ValueError:
        pass
    
    while current != base_path and current.exists():
        try:
            # Don't remove category-level directories (preserve structure)
            # Only if we're preserving category structure
            if category_level and current == category_level:
                break
            
            # Check if directory is empty
            if not any(current.iterdir()):
                current.rmdir()
                current = current.parent
            else:
                break
        except (OSError, PermissionError):
            # Stop if we can't remove (permissions, not empty, etc.)
            break


async def delete_directive_handler(params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """
    Delete a directive from registry, user space, project space, or all tiers.
    
    Params:
        name: str - Directive name to delete (required)
        from: str - Where to delete from: "registry", "user", "project", or "all" (default: "registry")
        cleanup_empty_dirs: bool - Remove empty category/subcategory folders after deletion (default: false)
        project_path: str - Optional project path override
    """
    name = params.get("name")
    from_tier = params.get("from", "registry")
    cleanup_empty_dirs = params.get("cleanup_empty_dirs", False)
    project_path = params.get("project_path")
    
    if not name:
        return {"status": "error", "message": "Missing required parameter: name"}
    
    # Validate 'from' parameter
    valid_tiers = {"registry", "user", "project", "all"}
    if from_tier not in valid_tiers:
        return {
            "status": "error",
            "message": f"Invalid 'from' parameter: {from_tier}. Must be one of: {', '.join(valid_tiers)}"
        }
    
    # Determine which tiers to delete from
    delete_registry = from_tier in ("registry", "all")
    delete_user = from_tier in ("user", "all")
    delete_project = from_tier in ("project", "all")
    
    # Initialize paths
    proj_path = _get_project_path(project_path)
    user_path = _get_user_path()
    db = DirectiveDB()
    
    # Track deletion results for each tier
    results = {
        "registry": {"success": False, "message": ""},
        "user": {"success": False, "message": "", "file_path": None},
        "project": {"success": False, "message": "", "file_path": None}
    }
    
    # Delete from each tier
    if delete_registry:
        success, message = _delete_from_registry(name, db)
        results["registry"] = {"success": success, "message": message}
    
    if delete_user:
        success, message, file_path = _delete_from_user(name, user_path, cleanup_empty_dirs)
        results["user"] = {"success": success, "message": message, "file_path": file_path}
    
    if delete_project:
        success, message, file_path = _delete_from_project(name, proj_path, cleanup_empty_dirs)
        results["project"] = {"success": success, "message": message, "file_path": file_path}
    
    # Determine which results to check based on 'from' parameter
    relevant_results = []
    if delete_registry:
        relevant_results.append(results["registry"])
    if delete_user:
        relevant_results.append(results["user"])
    if delete_project:
        relevant_results.append(results["project"])
    
    # Check if directive was actually found and deleted (not just "not found")
    actually_deleted = []
    for r in relevant_results:
        # Success with a message indicating deletion (not "not found")
        if r["success"] and "not found" not in r["message"].lower():
            actually_deleted.append(True)
        elif r["success"]:
            actually_deleted.append(False)  # "not found" - idempotent but not actually deleted
        else:
            actually_deleted.append(False)  # Failed
    
    # Check if directive exists in at least one tier (for validation)
    directive_found = False
    if delete_registry:
        try:
            existing = db.get(name)
            if existing:
                directive_found = True
        except Exception:
            pass
    
    if not directive_found:
        # Check local files
        if delete_user and find_directive_file(name, user_path):
            directive_found = True
        if delete_project and find_directive_file(name, proj_path):
            directive_found = True
    
    # If deleting from all and not found anywhere, that's an error
    if from_tier == "all" and not directive_found and not any(actually_deleted):
        return {
            "status": "error",
            "name": name,
            "message": f"Directive '{name}' not found in any tier (registry, user, or project)",
            "deleted_from": results
        }
    
    # Determine status based on actual deletions (not just "not found" successes)
    all_success = all(r["success"] for r in relevant_results)
    any_actually_deleted = any(actually_deleted)
    any_failed = any(not r["success"] for r in relevant_results)
    
    if all_success and any_actually_deleted and not any_failed:
        status = "deleted"
        message = f"Successfully deleted {name}"
    elif any_actually_deleted and any_failed:
        status = "partial"
        message = f"Partially deleted {name} (some tiers failed)"
    elif all_success and not any_actually_deleted:
        # All succeeded but nothing was actually deleted (all "not found")
        # This is OK for single-tier deletions (idempotent) but should be noted
        if from_tier != "all":
            status = "deleted"  # Idempotent - not found is success
            message = f"Directive '{name}' not found in {from_tier} tier (already deleted or never existed)"
        else:
            # This shouldn't happen due to check above, but handle it
            status = "error"
            message = f"Directive '{name}' not found in any tier"
    else:
        status = "error"
        message = f"Failed to delete {name} from any tier"
    
    return {
        "status": status,
        "name": name,
        "deleted_from": results,
        "message": message
    }

