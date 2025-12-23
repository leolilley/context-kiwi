"""
Directive lock file management.

Tracks installed directive versions and content hashes for efficient syncing.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from context_kiwi.config.registry import get_user_home


LOCKFILE_VERSION = 1


def get_lockfile_path() -> Path:
    """Get path to the directives lock file."""
    return get_user_home() / "directives.lock.json"


def load_lockfile() -> dict[str, Any]:
    """Load the lock file, creating empty one if doesn't exist."""
    path = get_lockfile_path()
    
    if not path.exists():
        return {
            "lockfile_version": LOCKFILE_VERSION,
            "directives": {}
        }
    
    try:
        content = path.read_text()
        data = json.loads(content)
        
        # Validate version
        if data.get("lockfile_version", 0) != LOCKFILE_VERSION:
            # Future: handle migrations
            return {
                "lockfile_version": LOCKFILE_VERSION,
                "directives": {}
            }
        
        return data
    except (json.JSONDecodeError, OSError):
        return {
            "lockfile_version": LOCKFILE_VERSION,
            "directives": {}
        }


def save_lockfile(data: dict[str, Any]) -> None:
    """Save the lock file."""
    path = get_lockfile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Ensure version is set
    data["lockfile_version"] = LOCKFILE_VERSION
    
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def get_locked_directive(name: str) -> dict[str, Any] | None:
    """Get lock info for a specific directive."""
    lockfile = load_lockfile()
    return lockfile.get("directives", {}).get(name)


def set_locked_directive(
    name: str,
    version: str,
    content_hash: str,
    source: str = "registry"
) -> None:
    """Update lock info for a directive after download."""
    lockfile = load_lockfile()
    
    if "directives" not in lockfile:
        lockfile["directives"] = {}
    
    lockfile["directives"][name] = {
        "version": version,
        "hash": content_hash,
        "source": source,
        "downloaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    save_lockfile(lockfile)


def remove_locked_directive(name: str) -> None:
    """Remove a directive from the lock file."""
    lockfile = load_lockfile()
    
    if "directives" in lockfile and name in lockfile["directives"]:
        del lockfile["directives"][name]
        save_lockfile(lockfile)


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return "sha256:" + hashlib.sha256(content.encode()).hexdigest()[:16]


def needs_update(
    name: str,
    registry_version: str,
    registry_hash: str | None = None
) -> tuple[bool, str]:
    """
    Check if a directive needs to be updated.
    
    Returns:
        (needs_update: bool, reason: str)
    """
    locked = get_locked_directive(name)
    
    if not locked:
        return True, "not_installed"
    
    local_version = locked.get("version")
    local_hash = locked.get("hash")
    
    # Version mismatch
    if local_version != registry_version:
        return True, f"version_changed:{local_version}→{registry_version}"
    
    # Hash mismatch (same version but content changed - re-publish)
    if registry_hash and local_hash and local_hash != registry_hash:
        return True, "content_changed"
    
    return False, "up_to_date"


def verify_local_file(name: str, file_path: Path) -> tuple[bool, str]:
    """
    Verify local file matches lock file.
    
    Returns:
        (valid: bool, reason: str)
    """
    locked = get_locked_directive(name)
    
    if not locked:
        return False, "not_in_lockfile"
    
    if not file_path.exists():
        return False, "file_missing"
    
    content = file_path.read_text()
    actual_hash = compute_content_hash(content)
    expected_hash = locked.get("hash")
    
    if expected_hash and actual_hash != expected_hash:
        return False, "hash_mismatch"
    
    return True, "valid"

