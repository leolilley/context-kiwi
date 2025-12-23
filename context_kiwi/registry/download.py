"""
Directive Download/Serving
Serves directive files over HTTP from Supabase.
"""

from typing import List, Optional, Dict, Any

from context_kiwi.utils.logger import Logger
from context_kiwi.db.directives import DirectiveDB

logger = Logger("registry-download")


async def serve_directive(name: str, version: Optional[str] = None) -> str:
    """Serve a directive file by name and version."""
    if name.endswith(".md"):
        name = name[:-3]
    
    db = DirectiveDB(logger=logger)
    db._require_db()
    
    content = db.get_content(name, version)
    if not content:
        raise FileNotFoundError(f"Directive not found: {name}")
    
    db.increment_downloads(name)
    logger.info(f"Served {name}@{version or 'latest'}")
    return content


async def get_directive_info(name: str) -> Optional[Dict[str, Any]]:
    """Get directive metadata including all versions."""
    db = DirectiveDB(logger=logger)
    db._require_db()
    
    directive = db.get(name)
    if not directive:
        return None
    
    return {
        "name": directive.name,
        "category": directive.category,
        "description": directive.description,
        "is_official": directive.is_official,
        "download_count": directive.download_count,
        "quality_score": directive.quality_score,
        "tech_stack": directive.tech_stack,
        "latest_version": directive.current_version.version,
        "available_versions": db.get_versions(name),
    }


async def list_available_directives(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all available directives with version info."""
    db = DirectiveDB(logger=logger)
    db._require_db()
    return db.list(category=category)


async def search_directives(query: str, tech_stack: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Search directives by query with tech stack compatibility."""
    db = DirectiveDB(logger=logger)
    db._require_db()
    return db.search(query, tech_stack=tech_stack)


async def publish_directive(
    name: str,
    version: str,
    content: str,
    changelog: Optional[str] = None,
) -> bool:
    """Publish a new version of a directive."""
    db = DirectiveDB(logger=logger)
    db._require_db()
    return db.publish(name, version, content, changelog)
