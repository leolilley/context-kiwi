"""
publish_directive directive tool.
Publishes a new version of a directive to the Supabase registry.
Auto-creates directive if it doesn't exist.
"""

import re
from typing import Dict, Any, Optional, Tuple
from context_kiwi.db.directives import DirectiveDB
from context_kiwi.utils import semver
from context_kiwi.mcp_types import ToolContext

# Max directive size: 100KB
MAX_DIRECTIVE_SIZE_BYTES = 100 * 1024


def extract_metadata_from_content(content: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract category, subcategory, and description from directive XML content."""
    category = None
    subcategory = None
    description = None
    
    # Try to extract category
    cat_match = re.search(r'<category>([^<]+)</category>', content)
    if cat_match:
        category = cat_match.group(1).strip()
    
    # Try to extract subcategory
    subcat_match = re.search(r'<subcategory>([^<]+)</subcategory>', content)
    if subcat_match:
        subcategory = subcat_match.group(1).strip()
    
    # Try to extract description
    desc_match = re.search(r'<description>([^<]+)</description>', content)
    if desc_match:
        description = desc_match.group(1).strip()
    
    return category, subcategory, description


async def publish_directive_handler(params: Dict[str, Any], context: ToolContext) -> Dict[str, Any]:
    """
    Publish a directive to the registry. Creates if new, updates if exists.
    
    Params:
        name: str - Directive name (e.g. "create_component")
        version: str - Semver version (e.g. "1.2.0")
        content: str - Full directive content (markdown with embedded XML)
        changelog: str - Optional changelog entry
        category: str - Optional, extracted from content if not provided
        subcategory: str - Optional, extracted from content if not provided
        description: str - Optional, extracted from content if not provided
    """
    name = params.get("name")
    version = params.get("version")
    content = params.get("content")
    changelog = params.get("changelog")
    category = params.get("category")
    subcategory = params.get("subcategory")
    description = params.get("description")
    
    # Validate required params
    if not name:
        return {"status": "error", "message": "Missing required parameter: name"}
    if not version:
        return {"status": "error", "message": "Missing required parameter: version"}
    if not content:
        return {"status": "error", "message": "Missing required parameter: content"}
    
    # Validate content size
    content_size = len(content.encode('utf-8'))
    if content_size > MAX_DIRECTIVE_SIZE_BYTES:
        return {
            "status": "error",
            "message": f"Directive too large: {content_size:,} bytes (max {MAX_DIRECTIVE_SIZE_BYTES:,} bytes)."
        }
    
    # Validate semver format
    try:
        semver.parse(version)
    except ValueError as e:
        return {"status": "error", "message": f"Invalid version format: {e}"}
    
    # Extract metadata from content if not provided
    if not category or not description or subcategory is None:
        extracted_cat, extracted_subcat, extracted_desc = extract_metadata_from_content(content)
        # Default to "actions" for user-published directives (not "core" which is reserved for system directives)
        category = category or extracted_cat or "actions"
        subcategory = subcategory if subcategory is not None else extracted_subcat
        description = description or extracted_desc or f"{name} directive"
    
    db = DirectiveDB()
    
    # Check if directive exists
    existing = db.get(name)
    is_new = existing is None
    
    if not is_new:
        # Check if version already exists
        existing_versions = db.get_versions(name)
        if version in existing_versions:
            return {
                "status": "error",
                "message": f"Version {version} already exists for {name}. Available: {existing_versions}"
            }
    
    try:
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        if is_new:
            # Create new directive
            success = db.create(
                name=name,
                category=category,
                description=description,
                version=version,
                content=content,
                subcategory=subcategory,
                changelog=changelog,
            )
            action = "created"
        else:
            # Publish new version
            success = db.publish(
                name=name,
                version=version,
                content=content,
                changelog=changelog,
            )
            action = "published"
        
        if success:
            return {
                "status": "published",
                "name": name,
                "version": version,
                "category": category,
                "subcategory": subcategory,
                "content_hash": content_hash,
                "content_size_bytes": content_size,
                "is_new": is_new,
                "message": f"Successfully {action} {name}@{version}"
            }
        else:
            return {"status": "error", "message": f"{action.title()} failed for unknown reason"}
            
    except Exception as e:
        return {"status": "error", "message": f"Publish failed: {str(e)}"}
