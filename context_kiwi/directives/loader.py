"""
Directive Loader

Loads, parses, and searches directives from multiple sources:
1. Project (.ai/directives/) - highest priority
2. User (~/.context-kiwi/directives/)  
3. Registry (Supabase) - lowest priority
"""

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DirectiveMatch:
    """Search result for a directive."""
    name: str
    description: str
    version: str
    source: str  # "project", "user", "registry"
    score: float
    tech_stack: list[str] = field(default_factory=list)
    category: str = ""
    subcategory: str | None = None
    path: Path | None = None  # For local directives
    quality_score: float | None = None  # Success rate / quality score
    download_count: int | None = None  # Download count (registry only)
    created_at: str | None = None  # ISO date string
    updated_at: str | None = None  # ISO date string
    tags: list[str] = field(default_factory=list)  # Tags for filtering


@dataclass 
class Directive:
    """Loaded directive with content and parsed structure."""
    name: str
    version: str
    description: str
    content: str  # Raw markdown content
    parsed: dict[str, Any]  # Parsed XML structure
    source: str  # "project", "user", "registry"
    path: Path | None = None
    tech_stack: list[str] = field(default_factory=list)


class DirectiveLoader:
    """
    Loads directives from local filesystem and remote registry.
    
    Sources (priority order):
    1. Project: .ai/directives/ (current working directory)
    2. User: ~/.context-kiwi/directives/
    3. Registry: Remote Supabase database
    """
    
    def __init__(self, project_path: Path | None = None, registry_url: str | None = None):
        """
        Initialize directive loader.
        
        Args:
            project_path: Override project path (default: auto-detect)
            registry_url: Override registry URL
        """
        self.project_path = (project_path or Path.cwd()) / ".ai" / "directives"
        
        from context_kiwi.config import get_user_home
        self.user_path = get_user_home() / "directives"
        from context_kiwi.config import get_supabase_url, get_supabase_key
        self.supabase_url = get_supabase_url()
        self.supabase_key = get_supabase_key()
        
        # Cache: name -> (Directive, file_hash)
        self._cache: dict[str, tuple] = {}
    
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def search(
        self, 
        query: str, 
        source: str,
        sort_by: str,
        project_tech_stack: list[str] | None = None,
        categories: list[str] | None = None,
        subcategories: list[str] | None = None,
        tags: list[str] | None = None,
        tech_stack_filter: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None
    ) -> list[DirectiveMatch]:
        """
        Search for directives with advanced filtering.
        
        Args:
            query: Search query
            source: Where to search
                - "local": Project + User space (default)
                - "registry": Remote registry with context
                - "all": Everything
            project_tech_stack: Project's tech stack for context-aware registry search
            categories: Filter by categories (e.g., ["patterns", "workflows"])
            tags: Filter by tags (array of strings)
            tech_stack_filter: Filter by tech stack compatibility
            sort_by: Sort by "score", "success_rate", "date", or "downloads"
            date_from: Filter directives created/updated after this date (ISO format)
            date_to: Filter directives created/updated before this date (ISO format)
            
        Returns:
            List of matches sorted according to sort_by
            Priority: Project > User > Registry
        """
        results = []
        
        # Search local sources
        if source in ("local", "all"):
            results.extend(self._search_local(
                query, self.project_path, "project",
                categories=categories, subcategories=subcategories, tags=tags, tech_stack_filter=tech_stack_filter
            ))
            results.extend(self._search_local(
                query, self.user_path, "user",
                categories=categories, subcategories=subcategories, tags=tags, tech_stack_filter=tech_stack_filter
            ))
        
        # Search registry (with context - server handles ranking)
        if source in ("registry", "all"):
            results.extend(self._search_registry(
                query, project_tech_stack,
                categories=categories, subcategories=subcategories, tags=tags, tech_stack_filter=tech_stack_filter,
                sort_by=sort_by, date_from=date_from, date_to=date_to
            ))
        
        # Apply tech stack bonus for LOCAL results only
        # (Registry search already handles this server-side)
        tech_stack_to_use = tech_stack_filter or project_tech_stack
        if tech_stack_to_use and source in ("local", "all"):
            for match in results:
                if match.source != "registry" and match.tech_stack:
                    overlap = set(match.tech_stack) & set(tech_stack_to_use)
                    if overlap:
                        match.score += 20
        
        # Apply filters to local results
        if categories:
            results = [r for r in results if r.category in categories]
        if subcategories:
            results = [r for r in results if r.subcategory and r.subcategory in subcategories]
        if tags:
            results = [r for r in results if any(tag.lower() in [t.lower() for t in r.tags] for tag in tags)]
        if tech_stack_filter:
            results = [r for r in results if any(
                tech.lower() in [t.lower() for t in r.tech_stack] 
                for tech in tech_stack_filter
            )]
        
        # Apply date filtering
        if date_from or date_to:
            from datetime import datetime
            results = [r for r in results if self._matches_date_filter(r, date_from, date_to)]
        
        # Sort results
        results = self._sort_results(results, sort_by)
        
        return results
    
    def load(self, name: str, version: str | None = None) -> Directive | None:
        """
        Load a directive by name.
        
        Priority: project > user > registry
        
        Args:
            name: Directive name
            version: Specific version (only for registry)
            
        Returns:
            Directive or None if not found
        """
        # Check cache first
        cached = self._get_cached(name)
        if cached:
            return cached
        
        # 1. Check project
        directive = self._load_from_path(name, self.project_path, "project")
        if directive:
            self._cache_directive(directive)
            return directive
        
        # 2. Check user
        directive = self._load_from_path(name, self.user_path, "user")
        if directive:
            self._cache_directive(directive)
            return directive
        
        # 3. Fetch from registry
        directive = self._fetch_from_registry(name, version)
        if directive:
            # Don't cache registry directives (they should be downloaded first)
            return directive
        
        return None
    
    def load_local(self, name: str) -> Directive | None:
        """Load directive from local sources only (no registry)."""
        cached = self._get_cached(name)
        if cached:
            return cached
        
        directive = self._load_from_path(name, self.project_path, "project")
        if directive:
            self._cache_directive(directive)
            return directive
        
        directive = self._load_from_path(name, self.user_path, "user")
        if directive:
            self._cache_directive(directive)
            return directive
        
        return None
    
    # =========================================================================
    # Local Search
    # =========================================================================
    
    def _search_local(
        self, 
        query: str, 
        base_path: Path, 
        source: str,
        categories: list[str] | None = None,
        subcategories: list[str] | None = None,
        tags: list[str] | None = None,
        tech_stack_filter: list[str] | None = None
    ) -> list[DirectiveMatch]:
        """Search directives in a local directory."""
        results = []
        query_lower = query.lower()
        
        if not base_path.exists():
            return results
        
        # Search all subdirectories recursively
        for md_file in base_path.glob("**/*.md"):
                try:
                    content = md_file.read_text()
                    parsed = self._parse_directive(content)
                    
                    if not parsed:
                        continue
                    
                    name = parsed.get("_attrs", {}).get("name", md_file.stem)
                    description = self._get_description(parsed)
                    tech_stack = self._get_tech_stack(parsed)
                    category = self._get_category(parsed)
                    subcategory = self._get_subcategory(parsed) or self._extract_subcategory_from_path(md_file, base_path)
                    version = parsed.get("_attrs", {}).get("version", "0.0.0")
                    tags_list = self._get_tags(parsed)
                    
                    # Apply category filter
                    if categories and category not in categories:
                        continue
                    
                    # Apply subcategory filter
                    if subcategories and (not subcategory or subcategory not in subcategories):
                        continue
                    
                    # Apply tags filter
                    if tags and not any(tag.lower() in [t.lower() for t in tags_list] for tag in tags):
                        continue
                    
                    # Apply tech stack filter
                    if tech_stack_filter and not any(
                        tech.lower() in [t.lower() for t in tech_stack] 
                        for tech in tech_stack_filter
                    ):
                        continue
                    
                    # Calculate score
                    score = self._calculate_score(
                        query_lower, name, description, category, tech_stack
                    )
                    
                    if score > 0:
                        # Get file modification time for date filtering
                        file_stat = md_file.stat()
                        from datetime import datetime
                        created_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                        
                        results.append(DirectiveMatch(
                            name=name,
                            description=description,
                            version=version,
                            source=source,
                            score=score,
                            tech_stack=tech_stack,
                            category=category,
                            subcategory=subcategory,
                            path=md_file,
                            tags=tags_list,
                            created_at=created_at,
                            updated_at=created_at
                        ))
                        
                except Exception as e:
                    logger.warning(f"Error parsing {md_file}: {e}")
        
        return results
    
    def _calculate_score(
        self, 
        query: str, 
        name: str, 
        description: str,
        category: str,
        tech_stack: list[str]
    ) -> float:
        """
        Calculate match score for a directive with improved multi-term support.
        
        Scoring:
        - Exact name match: 100 (instant win)
        - Name contains all query terms: 80
        - Name contains some query terms: 60
        - Description contains all terms: 40
        - Description contains some terms: 20
        - Category match: 15
        - Tech stack match: 10
        """
        query_lower = query.lower()
        name_lower = name.lower()
        desc_lower = (description or "").lower()
        category_lower = (category or "").lower()
        
        # Parse query into terms
        query_terms = [t.strip() for t in query_lower.split() if t.strip() and len(t.strip()) >= 2]
        
        if not query_terms:
            # Fallback to simple matching if no valid terms
            if name_lower == query_lower:
                return 100
            if query_lower in name_lower:
                return 70
            if description and query_lower in desc_lower:
                return 40
            return 0
        
        # Exact name match
        name_normalized = name_lower.replace("_", " ").replace("-", " ")
        query_normalized = " ".join(query_terms)
        if name_lower == query_normalized or name_normalized == query_normalized:
            return 100
        
        score = 0.0
        
        # Count term matches in name
        name_matches = sum(1 for term in query_terms if term in name_lower)
        if name_matches == len(query_terms):
            score = 80.0  # All terms in name
        elif name_matches > 0:
            score = 60.0 * (name_matches / len(query_terms))  # Partial match in name
        
        # Count term matches in description
        desc_matches = sum(1 for term in query_terms if term in desc_lower)
        if desc_matches == len(query_terms):
            score = max(score, 40.0)  # All terms in description
        elif desc_matches > 0:
            score = max(score, 20.0 * (desc_matches / len(query_terms)))  # Partial match in description
        
        # Category match (bonus)
        if category_lower:
            category_matches = sum(1 for term in query_terms if term in category_lower)
            if category_matches > 0:
                score += 15.0 * (category_matches / len(query_terms))
        
        # Tech stack match (bonus)
        if tech_stack:
            tech_matches = 0
            for tech in tech_stack:
                tech_lower = tech.lower()
                tech_matches += sum(1 for term in query_terms if term in tech_lower)
            if tech_matches > 0:
                score += 10.0 * min(tech_matches / len(query_terms), 1.0)
        
        return min(score, 100.0)  # Cap at 100
    
    # =========================================================================
    # Registry Search
    # =========================================================================
    
    def _search_registry(
        self, 
        query: str, 
        tech_stack: list[str] | None = None,
        categories: list[str] | None = None,
        subcategories: list[str] | None = None,
        tags: list[str] | None = None,
        tech_stack_filter: list[str] | None = None,
        sort_by: str = "score",
        date_from: str | None = None,
        date_to: str | None = None
    ) -> list[DirectiveMatch]:
        """
        Search directives in Supabase registry.
        
        Args:
            query: Search query
            tech_stack: Project's tech stack for context-aware ranking
            categories: Filter by categories
            subcategories: Filter by subcategories
            tags: Filter by tags
            tech_stack_filter: Filter by tech stack
            sort_by: Sort order
            date_from: Filter by date from
            date_to: Filter by date to
        """
        results = []
        query_lower = query.lower()
        
        try:
            # Use DirectiveDB for better filtering support
            from context_kiwi.db.directives import DirectiveDB
            db = DirectiveDB()
            
            if not db.is_available:
                raise RuntimeError("Database not available for registry search")
            
            # Use database search with filters
            tech_stack_to_use = tech_stack_filter or tech_stack
            db_results = db.search(
                query=query,
                tech_stack=tech_stack_to_use,
                categories=categories,
                subcategories=subcategories,
                tags=tags,
                sort_by=sort_by,
                date_from=date_from,
                date_to=date_to,
                limit=50
            )
            
            # Convert DB results to DirectiveMatch
            for item in db_results:
                results.append(DirectiveMatch(
                    name=item.get("name", ""),
                    description=item.get("description", ""),
                    version=item.get("latest_version", "0.0.0"),
                    source="registry",
                    score=item.get("compatibility_score", 1.0) * 100,  # Convert to score scale
                    tech_stack=item.get("tech_stack", []),
                    category=item.get("category", ""),
                    subcategory=item.get("subcategory"),
                    quality_score=item.get("quality_score"),
                    download_count=item.get("download_count"),
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at"),
                    tags=item.get("tags", [])
                ))
                        
        except Exception as e:
            logger.error(f"Registry search failed: {e}")
            raise
        
        return results
    
    
    # =========================================================================
    # Loading
    # =========================================================================
    
    def _load_from_path(
        self, 
        name: str, 
        base_path: Path, 
        source: str
    ) -> Directive | None:
        """Load directive from a local path. Supports nested folder structures."""
        from context_kiwi.utils.directive_finder import find_directive_file
        
        # Use shared utility to find the file
        file_path = find_directive_file(name, base_path, verify_name=True)
        
        if not file_path:
            return None
        
        try:
            content = file_path.read_text()
            parsed = self._parse_directive(content)
            
            if parsed:
                directive_name = parsed.get("_attrs", {}).get("name", name)
                # Verify name matches (should already be verified by find_directive_file, but double-check)
                if directive_name == name:
                    return Directive(
                        name=directive_name,
                        version=parsed.get("_attrs", {}).get("version", "0.0.0"),
                        description=self._get_description(parsed),
                        content=content,
                        parsed=parsed,
                        source=source,
                        path=file_path,
                        tech_stack=self._get_tech_stack(parsed)
                    )
        except Exception as e:
            logger.warning(f"Error loading {file_path}: {e}")
        
        return None
    
    def _fetch_from_registry(
        self, 
        name: str, 
        version: str | None = None
    ) -> Directive | None:
        """Fetch directive from Supabase registry."""
        try:
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}"
            }
            
            with httpx.Client(timeout=10.0) as client:
                # Get directive ID and metadata
                dir_resp = client.get(
                    f"{self.supabase_url}/rest/v1/directives",
                    params={"name": f"eq.{name}", "select": "id,name,description,tech_stack"},
                    headers=headers
                )
                
                directives = dir_resp.json() if dir_resp.status_code == 200 else []
                if not directives:
                    return None
                
                directive = directives[0]
                directive_id = directive["id"]
                
                # Get version (latest or specific)
                params = {"directive_id": f"eq.{directive_id}", "select": "version,content"}
                if version:
                    params["version"] = f"eq.{version}"
                else:
                    params["is_latest"] = "eq.true"
                
                ver_resp = client.get(
                    f"{self.supabase_url}/rest/v1/directive_versions",
                    params=params,
                    headers=headers
                )
                
                versions = ver_resp.json() if ver_resp.status_code == 200 else []
                if not versions:
                    return None
                
                content = versions[0]["content"]
                actual_version = versions[0]["version"]
                parsed = self._parse_directive(content)
                
                return Directive(
                    name=directive.get("name", name),
                    version=actual_version,
                    description=directive.get("description", ""),
                    content=content,
                    parsed=parsed or {},
                    source="registry",
                    tech_stack=directive.get("tech_stack", []) or []
                )
                
        except Exception as e:
            logger.warning(f"Registry fetch failed for {name}: {e}")
        
        return None
    
    # =========================================================================
    # Parsing
    # =========================================================================
    
    def _parse_directive(self, content: str) -> dict[str, Any] | None:
        """
        Parse directive from markdown content.
        
        Extracts XML from ```xml ... ``` code block and parses to dict.
        """
        xml_content = self._extract_xml_from_markdown(content)
        if not xml_content:
            return None
        
        return self._parse_xml_to_dict(xml_content)
    
    def _extract_xml_from_markdown(self, content: str) -> str | None:
        """Extract XML directive from markdown."""
        # Strategy: Find <directive...>...</directive> directly
        # This handles nested code blocks inside CDATA sections
        
        # Find the directive tag (may have attributes)
        start_pattern = r'<directive[^>]*>'
        start_match = re.search(start_pattern, content)
        if not start_match:
            return None
        
        start_idx = start_match.start()
        
        # Find closing </directive> - must find the LAST one to handle nested content
        end_tag = '</directive>'
        end_idx = content.rfind(end_tag)
        if end_idx == -1 or end_idx < start_idx:
            return None
        
        return content[start_idx:end_idx + len(end_tag)].strip()
    
    def _parse_xml_to_dict(self, xml_content: str) -> dict[str, Any] | None:
        """Parse XML string to dictionary."""
        try:
            root = ET.fromstring(xml_content)
            result = self._element_to_dict(root)
            # Root element is always a dict, not a simplified string
            return result if isinstance(result, dict) else {"_text": result}
        except ET.ParseError as e:
            logger.warning(f"XML parse error: {e}")
            return None
    
    def _element_to_dict(self, element: ET.Element) -> dict[str, Any] | str:
        """Convert XML element to dict (or str for text-only elements)."""
        result: dict[str, Any] = {}
        
        # Text content
        if element.text and element.text.strip():
            result['_text'] = element.text.strip()
        
        # Attributes
        if element.attrib:
            result['_attrs'] = dict(element.attrib)
        
        # Children
        for child in element:
            tag = child.tag
            child_dict = self._element_to_dict(child)
            
            # Handle multiple children with same tag
            if tag in result:
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_dict)
            else:
                result[tag] = child_dict
        
        # Simplify text-only elements
        if len(result) == 1 and '_text' in result:
            return result['_text']
        
        return result
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def _get_description(self, parsed: dict[str, Any]) -> str:
        """Extract description from parsed directive."""
        metadata = parsed.get("metadata", {})
        if isinstance(metadata, dict):
            desc = metadata.get("description", "")
            if isinstance(desc, dict):
                return desc.get("_text", "")
            return desc
        return ""
    
    def _get_tech_stack(self, parsed: dict[str, Any]) -> list[str]:
        """Extract tech stack from parsed directive."""
        context = parsed.get("context", {})
        if not isinstance(context, dict):
            return []
        
        tech_stack = context.get("tech_stack", {})
        if isinstance(tech_stack, str):
            # Simple string like "React 18+, Zustand, Axios"
            return [t.strip() for t in tech_stack.split(",")]
        elif isinstance(tech_stack, dict):
            # Structured like {framework: "React", language: "TypeScript"}
            values = []
            for key, value in tech_stack.items():
                if key.startswith("_"):
                    continue
                if isinstance(value, str):
                    values.append(value)
                elif isinstance(value, dict) and "_text" in value:
                    values.append(value["_text"])
            return values
        
        return []
    
    def _get_category(self, parsed: dict[str, Any]) -> str:
        """Extract category from parsed directive."""
        metadata = parsed.get("metadata", {})
        if isinstance(metadata, dict):
            cat = metadata.get("category", "")
            if isinstance(cat, dict):
                return cat.get("_text", "")
            return cat
        return ""
    
    def _get_subcategory(self, parsed: dict[str, Any]) -> str | None:
        """Extract subcategory from parsed directive."""
        metadata = parsed.get("metadata", {})
        if isinstance(metadata, dict):
            subcat = metadata.get("subcategory")
            if isinstance(subcat, dict):
                return subcat.get("_text")
            if isinstance(subcat, str) and subcat.strip():
                return subcat.strip()
        return None
    
    def _extract_subcategory_from_path(self, file_path: Path, base_path: Path) -> str | None:
        """
        Extract subcategory from directory structure.
        
        Examples:
            .ai/directives/patterns/api-endpoints/file.md → "api-endpoints"
            .ai/directives/core/export-chat/file.md → "export-chat"
            .ai/directives/core/file.md → None (no subcategory)
        """
        try:
            # Get relative path from base
            relative = file_path.relative_to(base_path)
            parts = relative.parts
            
            # If we have more than 2 parts (category/subcategory/file.md), extract subcategory
            # parts[0] is category, parts[1] would be subcategory (if exists)
            if len(parts) > 2:
                return parts[1]  # Subcategory is the second directory level
            return None
        except (ValueError, IndexError):
            return None
    
    def _get_tags(self, parsed: dict[str, Any]) -> list[str]:
        """Extract tags from parsed directive."""
        metadata = parsed.get("metadata", {})
        if not isinstance(metadata, dict):
            return []
        
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            return [t.strip() for t in tags.split(",")]
        elif isinstance(tags, list):
            result = []
            for tag in tags:
                if isinstance(tag, str):
                    result.append(tag)
                elif isinstance(tag, dict):
                    result.append(tag.get("_text", ""))
            return [t for t in result if t]
        elif isinstance(tags, dict):
            # Single tag as dict
            return [tags.get("_text", "")]
        return []
    
    def _sort_results(self, results: list[DirectiveMatch], sort_by: str) -> list[DirectiveMatch]:
        """Sort results according to sort_by parameter."""
        source_priority = {"project": 0, "user": 1, "registry": 2}
        
        if sort_by == "success_rate":
            # Sort by quality_score (descending), then by source priority
            results.sort(key=lambda x: (
                -(x.quality_score or 0),
                source_priority.get(x.source, 3)
            ))
        elif sort_by == "date":
            # Sort by updated_at or created_at (newest first), then by source priority
            from datetime import datetime
            def get_date(match: DirectiveMatch) -> datetime:
                date_str = match.updated_at or match.created_at
                if date_str:
                    try:
                        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        return datetime.min
                return datetime.min
            
            results.sort(key=lambda x: (
                -get_date(x).timestamp(),
                source_priority.get(x.source, 3)
            ))
        elif sort_by == "downloads":
            # Sort by download_count (descending), then by source priority
            results.sort(key=lambda x: (
                -(x.download_count or 0),
                source_priority.get(x.source, 3)
            ))
        elif sort_by == "score":
            # Sort by score (descending), then by source priority
            results.sort(key=lambda x: (
                -x.score,
                source_priority.get(x.source, 3)
            ))
        else:
            # Unknown sort_by, default to score
            results.sort(key=lambda x: (
                -x.score,
                source_priority.get(x.source, 3)
            ))
        
        return results
    
    def _matches_date_filter(self, match: DirectiveMatch, date_from: str | None, date_to: str | None) -> bool:
        """Check if match falls within date range."""
        if not date_from and not date_to:
            return True
        
        from datetime import datetime
        
        date_str = match.updated_at or match.created_at
        if not date_str:
            return False
        
        try:
            match_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            if date_from:
                from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                if match_date < from_date:
                    return False
            
            if date_to:
                to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                if match_date > to_date:
                    return False
            
            return True
        except Exception:
            return True  # If date parsing fails, include the result
    
    
    # =========================================================================
    # Caching
    # =========================================================================
    
    def _get_cached(self, name: str) -> Directive | None:
        """Get directive from cache if still valid."""
        if name not in self._cache:
            return None
        
        directive, file_hash = self._cache[name]
        
        # Validate cache for local directives
        if directive.path and directive.path.exists():
            current_hash = self._hash_file(directive.path)
            if current_hash != file_hash:
                del self._cache[name]
                return None
        
        return directive
    
    def _cache_directive(self, directive: Directive):
        """Cache a directive."""
        file_hash = None
        if directive.path and directive.path.exists():
            file_hash = self._hash_file(directive.path)
        
        self._cache[directive.name] = (directive, file_hash)
    
    def _hash_file(self, path: Path) -> str:
        """Calculate file hash for cache invalidation."""
        return hashlib.md5(path.read_bytes()).hexdigest()
    
    def clear_cache(self, name: str | None = None):
        """Clear cache for specific directive or all."""
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()

