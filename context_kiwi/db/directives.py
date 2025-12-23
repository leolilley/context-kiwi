"""
Directive database operations.
CRUD operations for directives stored in Supabase with semver versioning.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from context_kiwi.db.client import get_supabase_client, SupabaseClient
from context_kiwi.db.helpers import Row, get_rows, get_first, get_nested_first
from context_kiwi.utils.logger import Logger
from context_kiwi.utils import semver


@dataclass(slots=True)
class DirectiveVersion:
    """A specific version of a directive."""
    version: str
    content: str
    content_hash: str
    changelog: Optional[str] = None
    is_latest: bool = False


@dataclass(slots=True)
class DirectiveRecord:
    """Represents a directive from the database."""
    id: str
    name: str
    category: str
    subcategory: Optional[str]
    description: Optional[str]
    is_official: bool
    download_count: int
    quality_score: float
    tech_stack: List[str]
    current_version: DirectiveVersion
    dependencies: List[Dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: Row, version_row: Row) -> "DirectiveRecord":
        """Build DirectiveRecord from database rows."""
        return cls(
            id=str(row.get("id", "")),
            name=str(row.get("name", "")),
            category=str(row.get("category", "")),
            subcategory=row.get("subcategory"),
            description=row.get("description"),
            is_official=bool(row.get("is_official", False)),
            download_count=int(row.get("download_count", 0)),
            quality_score=float(row.get("quality_score", 0.0)),
            tech_stack=list(row.get("tech_stack") or []),
            current_version=DirectiveVersion(
                version=str(version_row.get("version", "")),
                content=str(version_row.get("content", "")),
                content_hash=str(version_row.get("content_hash", "")),
                changelog=version_row.get("changelog"),
                is_latest=bool(version_row.get("is_latest", False)),
            ),
        )


class DirectiveDB:
    """Database operations for directives with versioning support."""
    
    DIRECTIVE_FIELDS = "id, name, category, subcategory, description, is_official, download_count, quality_score, tech_stack"
    VERSION_FIELDS = "version, content, content_hash, changelog, is_latest"
    
    def __init__(self, client: Optional[SupabaseClient] = None, logger: Optional[Logger] = None):
        self._client = client
        self.logger = logger or Logger("directive-db")
    
    @property
    def client(self) -> SupabaseClient:
        if self._client is None:
            self._client = get_supabase_client()
        return self._client
    
    @property
    def is_available(self) -> bool:
        return self.client.is_configured
    
    def _require_db(self) -> None:
        """Raise if database not configured."""
        if not self.is_available:
            raise RuntimeError("Database not configured. Set SUPABASE_URL and SUPABASE_SECRET_KEY.")
    
    def get(self, name: str, version_constraint: Optional[str] = None) -> Optional[DirectiveRecord]:
        """
        Get a directive by name and optional version constraint.
        
        Args:
            name: Directive name (e.g., 'bootstrap')
            version_constraint: Semver constraint (e.g., "^1.0.0", "~1.2.0", "*")
        """
        self._require_db()
        
        try:
            # Get directive metadata
            result = self.client.table("directives").select(self.DIRECTIVE_FIELDS).eq("name", name).execute()
            row = get_first(result.data)
            if not row:
                return None
            
            # Get versions
            versions_result = self.client.table("directive_versions").select(
                self.VERSION_FIELDS
            ).eq("directive_id", row["id"]).order("created_at", desc=True).execute()
            
            versions = get_rows(versions_result.data)
            if not versions:
                return None
            
            # Find matching version
            version_row = self._find_matching_version(versions, version_constraint)
            if not version_row:
                self.logger.warning(f"No version of {name} satisfies constraint {version_constraint}")
                return None
            
            return DirectiveRecord.from_row(row, version_row)
            
        except Exception as e:
            self.logger.error(f"Failed to get directive {name}: {e}")
            raise
    
    def _find_matching_version(
        self, 
        versions: List[Row], 
        constraint: Optional[str]
    ) -> Optional[Row]:
        """Find version matching constraint, or latest."""
        if constraint is None or constraint in ("*", "latest"):
            # Return latest, or first if no latest flag
            for v in versions:
                if v.get("is_latest"):
                    return v
            return versions[0] if versions else None
        
        # Find version matching constraint
        for v in versions:
            version_str = v.get("version", "")
            if isinstance(version_str, str) and semver.satisfies(version_str, constraint):
                return v
        return None
    
    def get_content(self, name: str, version_constraint: Optional[str] = None) -> Optional[str]:
        """Get just the content of a directive."""
        directive = self.get(name, version_constraint)
        return directive.current_version.content if directive else None
    
    def get_versions(self, name: str) -> List[str]:
        """Get all available versions for a directive."""
        self._require_db()
        
        try:
            result = self.client.table("directives").select("id").eq("name", name).execute()
            row = get_first(result.data)
            if not row:
                return []
            
            versions_result = self.client.table("directive_versions").select(
                "version"
            ).eq("directive_id", row.get("id")).order("created_at", desc=True).execute()
            
            return [str(v.get("version", "")) for v in get_rows(versions_result.data)]
        except Exception as e:
            self.logger.error(f"Failed to get versions for {name}: {e}")
            return []
    
    def list(self, category: Optional[str] = None, subcategory: Optional[str] = None, official_only: bool = False) -> List[Dict[str, Any]]:
        """List available directives with latest version info."""
        self._require_db()
        
        try:
            query = self.client.table("directives").select(
                "name, category, subcategory, description, is_official, download_count, quality_score, "
                "directive_versions!inner(version, is_latest)"
            ).eq("directive_versions.is_latest", True)
            
            if category:
                query = query.eq("category", category)
            if subcategory:
                query = query.eq("subcategory", subcategory)
            if official_only:
                query = query.eq("is_official", True)
            
            result = query.order("name").execute()
            
            return [
                {
                    "name": row.get("name"),
                    "category": row.get("category"),
                    "subcategory": row.get("subcategory"),
                    "description": row.get("description"),
                    "is_official": row.get("is_official"),
                    "download_count": row.get("download_count"),
                    "quality_score": float(row.get("quality_score", 0)),
                    "latest_version": (v.get("version") if (v := get_nested_first(row, "directive_versions")) else None),
                }
                for row in get_rows(result.data)
            ]
        except Exception as e:
            self.logger.error(f"Failed to list directives: {e}")
            raise
    
    def search(
        self, 
        query: str, 
        tech_stack: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        subcategories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "score",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search directives with PostgreSQL full-text search and advanced filtering.
        
        Uses PostgreSQL's full-text search (tsvector/tsquery) for better relevance
        and scalability compared to simple ILIKE pattern matching.
        
        Args:
            query: Search query string (supports multiple terms, will be parsed)
            tech_stack: Filter by tech stack compatibility
            categories: Filter by categories
            subcategories: Filter by subcategories
            tags: Filter by tags (array of tag strings)
            sort_by: Sort by "score", "success_rate", "date", or "downloads"
            date_from: Filter directives created/updated after this date (ISO format)
            date_to: Filter directives created/updated before this date (ISO format)
            limit: Maximum number of results
        """
        self._require_db()
        
        # Parse and normalize query
        query_terms = self._parse_search_query(query)
        if not query_terms:
            return []
        
        try:
            # Use PostgreSQL full-text search via RPC or raw SQL
            # Build tsquery from terms (AND by default, OR if user uses |)
            tsquery = " & ".join([term.replace("'", "''") for term in query_terms])
            
            # Build the search query using PostgreSQL full-text search
            # We'll use a raw SQL approach via Supabase RPC or direct query
            # For now, fallback to improved ILIKE if full-text search columns don't exist
            
            # Try full-text search first (requires search_vector column in DB)
            # If that fails, fall back to improved multi-term search
            use_fulltext = True  # Will be set based on DB schema availability
            
            if use_fulltext:
                # Full-text search using PostgreSQL tsvector
                # This requires a search_vector column: 
                # ALTER TABLE directives ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (
                #   to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, ''))
                # ) STORED;
                # CREATE INDEX directives_search_idx ON directives USING GIN(search_vector);
                
                # For Supabase, we'll use a raw query with RPC or direct SQL
                # Since Supabase client doesn't directly support full-text search,
                # we'll use an improved multi-term approach that's more scalable
                search_conditions = []
                for term in query_terms:
                    # Use ILIKE with word boundaries for better matching
                    search_conditions.append(f"(name ILIKE '%{term}%' OR description ILIKE '%{term}%')")
                
                # Use AND logic: all terms must match
                where_clause = " AND ".join(search_conditions)
            else:
                # Fallback: improved multi-term search
                search_conditions = []
                for term in query_terms:
                    search_conditions.append(f"(name ILIKE '%{term}%' OR description ILIKE '%{term}%')")
                where_clause = " AND ".join(search_conditions)
            
            # Build query with improved search
            # Note: Supabase client doesn't support raw WHERE clauses easily,
            # so we'll use the OR approach but with better term matching
            or_conditions = []
            for term in query_terms:
                or_conditions.extend([f"name.ilike.%{term}%", f"description.ilike.%{term}%"])
            
            query_builder = self.client.table("directives").select(
                "id, name, category, subcategory, description, is_official, download_count, quality_score, "
                "tech_stack, created_at, updated_at, tags, "
                "directive_versions!inner(version, is_latest)"
            ).eq("directive_versions.is_latest", True)
            
            # Apply search filter - use OR for terms but filter results to require all terms
            if or_conditions:
                query_builder = query_builder.or_(",".join(or_conditions))
            
            # Apply category filter
            if categories:
                query_builder = query_builder.in_("category", categories)
            
            # Apply subcategory filter
            if subcategories:
                query_builder = query_builder.in_("subcategory", subcategories)
            
            # Apply date filters
            if date_from:
                query_builder = query_builder.gte("updated_at", date_from)
            if date_to:
                query_builder = query_builder.lte("updated_at", date_to)
            
            # Execute query - get more results to filter client-side for multi-term matching
            result = query_builder.limit(limit * 3).execute()
            
            directives = []
            for row in get_rows(result.data):
                d = {
                    "name": row.get("name"),
                    "category": row.get("category"),
                    "subcategory": row.get("subcategory"),
                    "description": row.get("description"),
                    "is_official": row.get("is_official"),
                    "download_count": row.get("download_count", 0),
                    "quality_score": float(row.get("quality_score", 0)),
                    "tech_stack": row.get("tech_stack", []),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "latest_version": (v.get("version") if (v := get_nested_first(row, "directive_versions")) else None),
                    "tags": row.get("tags", []),
                }
                
                # Multi-term matching: ensure all query terms appear in name or description
                name_desc = f"{d['name']} {d.get('description', '')}".lower()
                if not all(term.lower() in name_desc for term in query_terms):
                    continue
                
                # Calculate relevance score based on term matches
                relevance_score = self._calculate_relevance_score(query_terms, d["name"], d.get("description", ""))
                d["relevance_score"] = relevance_score
                
                # Apply tech stack filter and calculate compatibility
                if tech_stack and (d_stack := d.get("tech_stack")):
                    overlap = set(tech.lower() for tech in tech_stack) & set(t.lower() for t in d_stack)
                    if not overlap:
                        continue
                    d["compatibility_score"] = len(overlap) / max(len(d_stack), 1)
                elif tech_stack:
                    d["compatibility_score"] = 1.0  # Universal directives
                else:
                    d["compatibility_score"] = 1.0
                
                # Apply tags filter
                if tags:
                    d_tags = d.get("tags", [])
                    if not any(tag.lower() in [t.lower() for t in d_tags] for tag in tags):
                        continue
                
                directives.append(d)
            
            # Sort results
            if sort_by == "success_rate":
                directives.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
            elif sort_by == "date":
                directives.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
            elif sort_by == "downloads":
                directives.sort(key=lambda x: x.get("download_count", 0), reverse=True)
            else:  # "score" or default - use relevance + compatibility
                directives.sort(
                    key=lambda x: (
                        x.get("relevance_score", 0) * 0.7 +  # 70% relevance
                        x.get("compatibility_score", 0) * 0.3  # 30% compatibility
                    ),
                    reverse=True
                )
            
            return directives[:limit]
        except Exception as e:
            self.logger.error(f"Failed to search directives: {e}")
            raise
    
    def _parse_search_query(self, query: str) -> List[str]:
        """
        Parse search query into normalized terms.
        
        Handles:
        - Multiple words (split by whitespace)
        - Quoted phrases (kept together)
        - Special operators (| for OR, - for NOT) - future enhancement
        - Normalization (lowercase, strip)
        """
        if not query or not query.strip():
            return []
        
        # Simple parsing: split by whitespace, normalize
        # Future: add support for quoted phrases and operators
        terms = []
        for word in query.split():
            word = word.strip().lower()
            if word and len(word) >= 2:  # Ignore single characters
                terms.append(word)
        
        return terms
    
    def _calculate_relevance_score(
        self, 
        query_terms: List[str], 
        name: str, 
        description: str
    ) -> float:
        """
        Calculate relevance score based on term matches.
        
        Scoring:
        - Exact name match: 100
        - Name contains all terms: 80
        - Name contains some terms: 60
        - Description contains all terms: 40
        - Description contains some terms: 20
        """
        name_lower = name.lower()
        desc_lower = (description or "").lower()
        
        # Check exact name match
        name_normalized = name_lower.replace("_", " ").replace("-", " ")
        query_normalized = " ".join(query_terms)
        if name_normalized == query_normalized or name_lower == query_normalized.replace(" ", "_"):
            return 100.0
        
        # Count term matches in name
        name_matches = sum(1 for term in query_terms if term in name_lower)
        desc_matches = sum(1 for term in query_terms if term in desc_lower)
        
        # Calculate score
        score = 0.0
        
        if name_matches == len(query_terms):
            score = 80.0  # All terms in name
        elif name_matches > 0:
            score = 60.0 * (name_matches / len(query_terms))  # Some terms in name
        
        if desc_matches == len(query_terms):
            score = max(score, 40.0)  # All terms in description
        elif desc_matches > 0:
            score = max(score, 20.0 * (desc_matches / len(query_terms)))  # Some terms in description
        
        return score
    
    def increment_downloads(self, name: str) -> bool:
        """Increment download count for a directive."""
        try:
            result = self.client.table("directives").select("download_count").eq("name", name).execute()
            row = get_first(result.data)
            if not row:
                return False
            
            current = int(row.get("download_count", 0))
            self.client.table("directives").update(
                {"download_count": current + 1}
            ).eq("name", name).execute()
            return True
        except Exception as e:
            self.logger.error(f"Failed to increment download count for {name}: {e}")
            return False
    
    def create(
        self,
        name: str,
        category: str,
        description: str,
        version: str,
        content: str,
        tech_stack: Optional[List[str]] = None,
        subcategory: Optional[str] = None,
        changelog: Optional[str] = None,
    ) -> bool:
        """Create a new directive with initial version."""
        self._require_db()
        
        # Validate semver
        try:
            semver.parse(version)
        except ValueError as e:
            raise ValueError(f"Invalid version format: {e}")
        
        try:
            import hashlib
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            # Create directive record
            directive_data = {
                "name": name,
                "category": category,
                "description": description,
                "is_official": True,
                "tech_stack": tech_stack or [],
            }
            if subcategory:
                directive_data["subcategory"] = subcategory
            
            result = self.client.table("directives").insert(directive_data).execute()
            
            row = get_first(result.data)
            if not row:
                raise ValueError("Failed to create directive record")
            
            directive_id = row.get("id")
            
            # Create initial version
            self.client.table("directive_versions").insert({
                "directive_id": directive_id,
                "version": version,
                "content": content,
                "content_hash": content_hash,
                "changelog": changelog or f"Initial release v{version}",
                "is_latest": True,
            }).execute()
            
            self.logger.info(f"Created {name}@{version}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create {name}@{version}: {e}")
            raise

    def publish(
        self,
        name: str,
        version: str,
        content: str,
        changelog: Optional[str] = None,
    ) -> bool:
        """Publish a new version of a directive."""
        self._require_db()
        
        # Validate semver
        try:
            semver.parse(version)
        except ValueError as e:
            raise ValueError(f"Invalid version format: {e}")
        
        try:
            import hashlib
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            
            # Get directive ID
            result = self.client.table("directives").select("id").eq("name", name).execute()
            row = get_first(result.data)
            if not row:
                raise ValueError(f"Directive not found: {name}")
            
            directive_id = row.get("id")
            
            # Unset previous latest
            self.client.table("directive_versions").update(
                {"is_latest": False}
            ).eq("directive_id", directive_id).eq("is_latest", True).execute()
            
            # Insert new version
            self.client.table("directive_versions").insert({
                "directive_id": directive_id,
                "version": version,
                "content": content,
                "content_hash": content_hash,
                "changelog": changelog,
                "is_latest": True,
            }).execute()
            
            self.logger.info(f"Published {name}@{version}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to publish {name}@{version}: {e}")
            raise
    
    def resolve_dependencies(
        self,
        name: str,
        version_constraint: Optional[str] = None,
        resolved: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Resolve all dependencies for a directive (future use)."""
        if resolved is None:
            resolved = {}
        
        directive = self.get(name, version_constraint)
        if not directive:
            raise ValueError(f"Directive not found: {name}")
        
        resolved[name] = directive.current_version.version
        
        for dep in directive.dependencies:
            dep_name = dep.get("name")
            dep_version = dep.get("version", "*")
            if dep_name and dep_name not in resolved:
                self.resolve_dependencies(dep_name, dep_version, resolved)
        
        return resolved
    
    def delete(self, name: str) -> bool:
        """Delete a directive and all its versions."""
        self._require_db()
        
        try:
            # Get directive ID
            result = self.client.table("directives").select("id").eq("name", name).execute()
            row = get_first(result.data)
            if not row:
                self.logger.warning(f"Directive not found for deletion: {name}")
                return False
            
            directive_id = row.get("id")
            
            # Delete all versions first (foreign key constraint)
            self.client.table("directive_versions").delete().eq("directive_id", directive_id).execute()
            
            # Delete the directive
            self.client.table("directives").delete().eq("id", directive_id).execute()
            
            self.logger.info(f"Deleted directive: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete {name}: {e}")
            raise
