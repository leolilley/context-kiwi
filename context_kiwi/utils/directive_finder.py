"""
Directive File Finder

Shared utilities for finding directive files in local filesystem.
Supports nested folder structures like core/export-chat/opencode.md
"""

import re
from pathlib import Path
from typing import Optional


def find_directive_file(
    name: str,
    base_path: Path,
    verify_name: bool = True
) -> Optional[Path]:
    """
    Find a directive file by name, supporting nested folder structures.
    
    Args:
        name: Directive name (from XML name attribute)
        base_path: Base directory to search (e.g., .ai/directives or ~/.context-kiwi/directives)
        verify_name: If True, verify the directive name in XML matches (handles different filenames)
    
    Returns:
        Path to directive file, or None if not found
    
    Search order:
    1. Standard locations: core/{name}.md, custom/{name}.md, {name}.md
    2. Recursive search in all subdirectories
    """
    if not base_path.exists():
        return None
    
    # Check standard locations first (for backwards compatibility)
    locations = [
        base_path / "core" / f"{name}.md",
        base_path / "custom" / f"{name}.md",
        base_path / f"{name}.md",
    ]
    
    for path in locations:
        if path.exists():
            if verify_name:
                # Verify the directive name matches (in case filename differs)
                if _verify_directive_name(path, name):
                    return path
            else:
                return path
    
    # Recursively search subdirectories for nested folder structures
    # This supports paths like core/export-chat/opencode.md
    for md_file in base_path.glob("**/*.md"):
        if verify_name:
            if _verify_directive_name(md_file, name):
                return md_file
        else:
            # If not verifying, return first match (but this is less reliable)
            return md_file
    
    return None


def _verify_directive_name(file_path: Path, expected_name: str) -> bool:
    """
    Verify that a directive file contains the expected directive name.
    
    Args:
        file_path: Path to the directive file
        expected_name: Expected directive name from XML name attribute
    
    Returns:
        True if the directive name matches, False otherwise
    """
    try:
        content = file_path.read_text()
        # Extract directive name from XML
        name_match = re.search(r'<directive[^>]*name\s*=\s*["\']([^"\']+)["\']', content)
        if name_match:
            return name_match.group(1) == expected_name
        # If no name attribute found, assume filename matches (backwards compatibility)
        return file_path.stem == expected_name
    except Exception:
        # If we can't parse, assume it's correct if filename matches
        return file_path.stem == expected_name


def find_directive_files_by_name_pattern(
    base_path: Path,
    name_pattern: Optional[str] = None
) -> list[Path]:
    """
    Find all directive files matching a name pattern.
    
    Args:
        base_path: Base directory to search
        name_pattern: Optional pattern to match directive names (None = all)
    
    Returns:
        List of paths to matching directive files
    """
    if not base_path.exists():
        return []
    
    results = []
    
    for md_file in base_path.glob("**/*.md"):
        try:
            content = md_file.read_text()
            name_match = re.search(r'<directive[^>]*name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match:
                directive_name = name_match.group(1)
                if name_pattern is None or name_pattern.lower() in directive_name.lower():
                    results.append(md_file)
        except Exception:
            continue
    
    return results


