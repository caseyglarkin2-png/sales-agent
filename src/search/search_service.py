"""
Search Service
==============
Advanced search functionality with full-text search, filters, facets, and suggestions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import re
import uuid


class SearchableEntity(str, Enum):
    """Searchable entity types."""
    LEAD = "lead"
    CONTACT = "contact"
    ACCOUNT = "account"
    COMPANY = "company"
    DEAL = "deal"
    OPPORTUNITY = "opportunity"
    TASK = "task"
    MEETING = "meeting"
    CALL = "call"
    EMAIL = "email"
    NOTE = "note"
    DOCUMENT = "document"
    CONTRACT = "contract"
    QUOTE = "quote"
    PRODUCT = "product"
    CAMPAIGN = "campaign"
    SEQUENCE = "sequence"
    TEMPLATE = "template"
    WORKFLOW = "workflow"
    ALL = "all"


class SearchOperator(str, Enum):
    """Search filter operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    MATCHES = "matches"  # Regex match


class SortOrder(str, Enum):
    """Sort order."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class SearchFilter:
    """Search filter definition."""
    field: str
    operator: SearchOperator
    value: Any
    boost: float = 1.0  # Relevance boost factor


@dataclass
class SearchFacet:
    """Search facet for filtering."""
    field: str
    value: Any
    count: int
    selected: bool = False


@dataclass
class SearchSuggestion:
    """Search suggestion."""
    text: str
    highlighted: str
    entity_type: SearchableEntity
    entity_id: Optional[str] = None
    score: float = 0.0


@dataclass
class SearchResultItem:
    """Individual search result."""
    id: str
    entity_type: SearchableEntity
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    score: float = 0.0
    highlights: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    url: Optional[str] = None


@dataclass
class SearchResult:
    """Search result set."""
    query: str
    total: int
    items: list[SearchResultItem] = field(default_factory=list)
    facets: dict[str, list[SearchFacet]] = field(default_factory=dict)
    suggestions: list[SearchSuggestion] = field(default_factory=list)
    page: int = 1
    page_size: int = 20
    took_ms: float = 0.0
    spell_corrected: Optional[str] = None


@dataclass
class SearchIndex:
    """Search index configuration."""
    id: str
    entity_type: SearchableEntity
    fields: list[str]
    boost_fields: dict[str, float] = field(default_factory=dict)
    enabled: bool = True
    last_indexed: Optional[datetime] = None
    document_count: int = 0


@dataclass
class SavedSearch:
    """Saved search query."""
    id: str
    name: str
    query: str
    entity_types: list[SearchableEntity]
    filters: list[SearchFilter]
    user_id: str
    is_public: bool = False
    notification_enabled: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    use_count: int = 0


@dataclass 
class RecentSearch:
    """Recent search tracking."""
    id: str
    query: str
    user_id: str
    entity_types: list[SearchableEntity]
    result_count: int
    searched_at: datetime = field(default_factory=datetime.utcnow)


class SearchService:
    """
    Advanced search service.
    
    Provides full-text search, filtering, faceting, and suggestions
    across all searchable entities.
    """
    
    def __init__(self):
        """Initialize search service."""
        # In-memory storage (would use Elasticsearch/Meilisearch in production)
        self.documents: dict[str, dict[str, Any]] = {}
        self.indexes: dict[str, SearchIndex] = {}
        self.saved_searches: dict[str, SavedSearch] = {}
        self.recent_searches: list[RecentSearch] = []
        
        # Initialize default indexes
        self._init_indexes()
    
    def _init_indexes(self):
        """Initialize default search indexes."""
        default_indexes = [
            SearchIndex(
                id="leads",
                entity_type=SearchableEntity.LEAD,
                fields=["name", "email", "company", "title", "notes"],
                boost_fields={"name": 2.0, "email": 1.5, "company": 1.5},
            ),
            SearchIndex(
                id="contacts",
                entity_type=SearchableEntity.CONTACT,
                fields=["first_name", "last_name", "email", "company", "phone"],
                boost_fields={"first_name": 2.0, "last_name": 2.0, "email": 1.5},
            ),
            SearchIndex(
                id="companies",
                entity_type=SearchableEntity.COMPANY,
                fields=["name", "domain", "industry", "description"],
                boost_fields={"name": 3.0, "domain": 2.0},
            ),
            SearchIndex(
                id="deals",
                entity_type=SearchableEntity.DEAL,
                fields=["name", "description", "company_name", "contact_name"],
                boost_fields={"name": 2.5, "company_name": 1.5},
            ),
            SearchIndex(
                id="documents",
                entity_type=SearchableEntity.DOCUMENT,
                fields=["name", "content", "tags", "description"],
                boost_fields={"name": 2.0, "content": 1.0},
            ),
            SearchIndex(
                id="emails",
                entity_type=SearchableEntity.EMAIL,
                fields=["subject", "body", "from", "to"],
                boost_fields={"subject": 2.0, "body": 1.0},
            ),
        ]
        
        for idx in default_indexes:
            self.indexes[idx.id] = idx
    
    async def search(
        self,
        query: str,
        entity_types: Optional[list[SearchableEntity]] = None,
        filters: Optional[list[SearchFilter]] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: Optional[str] = None,
        sort_order: SortOrder = SortOrder.DESC,
        include_facets: bool = True,
        include_suggestions: bool = True,
        user_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Execute a search query.
        
        Args:
            query: Search query string
            entity_types: Entity types to search (default: all)
            filters: Additional filters to apply
            page: Page number
            page_size: Results per page
            sort_by: Field to sort by
            sort_order: Sort order
            include_facets: Whether to include facets
            include_suggestions: Whether to include suggestions
            user_id: User ID for tracking
            
        Returns:
            SearchResult with matching items
        """
        import time
        start_time = time.time()
        
        if entity_types is None:
            entity_types = [SearchableEntity.ALL]
        
        # Normalize query
        normalized_query = self._normalize_query(query)
        
        # Find matching documents
        matches = []
        for doc_id, doc in self.documents.items():
            # Check entity type
            doc_type = SearchableEntity(doc.get("_type", "all"))
            if SearchableEntity.ALL not in entity_types and doc_type not in entity_types:
                continue
            
            # Calculate relevance score
            score = self._calculate_score(normalized_query, doc)
            if score > 0:
                # Apply filters
                if filters and not self._apply_filters(doc, filters):
                    continue
                
                # Create result item
                item = SearchResultItem(
                    id=doc_id,
                    entity_type=doc_type,
                    title=doc.get("_title", ""),
                    subtitle=doc.get("_subtitle"),
                    description=doc.get("_description"),
                    score=score,
                    highlights=self._get_highlights(normalized_query, doc),
                    metadata=doc.get("_metadata", {}),
                    created_at=doc.get("_created_at"),
                    updated_at=doc.get("_updated_at"),
                    url=doc.get("_url"),
                )
                matches.append(item)
        
        # Sort results
        if sort_by:
            matches.sort(
                key=lambda x: x.metadata.get(sort_by, ""),
                reverse=sort_order == SortOrder.DESC
            )
        else:
            # Sort by score by default
            matches.sort(key=lambda x: x.score, reverse=True)
        
        # Paginate
        total = len(matches)
        start = (page - 1) * page_size
        end = start + page_size
        items = matches[start:end]
        
        # Generate facets
        facets = {}
        if include_facets:
            facets = self._generate_facets(matches, entity_types)
        
        # Generate suggestions
        suggestions = []
        if include_suggestions and query:
            suggestions = await self.get_suggestions(query, entity_types, limit=5)
        
        # Track recent search
        if user_id:
            await self._track_recent_search(query, user_id, entity_types, total)
        
        took_ms = (time.time() - start_time) * 1000
        
        return SearchResult(
            query=query,
            total=total,
            items=items,
            facets=facets,
            suggestions=suggestions,
            page=page,
            page_size=page_size,
            took_ms=took_ms,
        )
    
    def _normalize_query(self, query: str) -> str:
        """Normalize search query."""
        return query.lower().strip()
    
    def _calculate_score(self, query: str, doc: dict) -> float:
        """Calculate relevance score for a document."""
        if not query:
            return 1.0
        
        score = 0.0
        query_terms = query.split()
        
        # Get index for this document type
        doc_type = doc.get("_type", "all")
        index = None
        for idx in self.indexes.values():
            if idx.entity_type.value == doc_type:
                index = idx
                break
        
        # Search through fields
        for key, value in doc.items():
            if key.startswith("_"):
                continue
            
            if isinstance(value, str):
                value_lower = value.lower()
                
                # Get boost factor
                boost = 1.0
                if index and key in index.boost_fields:
                    boost = index.boost_fields[key]
                
                # Exact match
                if query == value_lower:
                    score += 10.0 * boost
                
                # Contains full query
                elif query in value_lower:
                    score += 5.0 * boost
                
                # Term matches
                for term in query_terms:
                    if term in value_lower:
                        score += 1.0 * boost
        
        return score
    
    def _apply_filters(self, doc: dict, filters: list[SearchFilter]) -> bool:
        """Apply filters to a document."""
        for flt in filters:
            value = doc.get(flt.field)
            
            if flt.operator == SearchOperator.EQUALS:
                if value != flt.value:
                    return False
            elif flt.operator == SearchOperator.NOT_EQUALS:
                if value == flt.value:
                    return False
            elif flt.operator == SearchOperator.CONTAINS:
                if flt.value not in str(value):
                    return False
            elif flt.operator == SearchOperator.IN:
                if value not in flt.value:
                    return False
            elif flt.operator == SearchOperator.GREATER_THAN:
                if value is None or value <= flt.value:
                    return False
            elif flt.operator == SearchOperator.LESS_THAN:
                if value is None or value >= flt.value:
                    return False
            elif flt.operator == SearchOperator.IS_NULL:
                if value is not None:
                    return False
            elif flt.operator == SearchOperator.IS_NOT_NULL:
                if value is None:
                    return False
        
        return True
    
    def _get_highlights(self, query: str, doc: dict) -> dict[str, list[str]]:
        """Get highlighted snippets."""
        highlights = {}
        query_terms = query.split()
        
        for key, value in doc.items():
            if key.startswith("_"):
                continue
            
            if isinstance(value, str):
                for term in query_terms:
                    if term in value.lower():
                        # Create highlighted snippet
                        pattern = re.compile(f"({re.escape(term)})", re.IGNORECASE)
                        highlighted = pattern.sub(r"<em>\1</em>", value)
                        if key not in highlights:
                            highlights[key] = []
                        highlights[key].append(highlighted[:200])
                        break
        
        return highlights
    
    def _generate_facets(
        self,
        results: list[SearchResultItem],
        entity_types: list[SearchableEntity],
    ) -> dict[str, list[SearchFacet]]:
        """Generate facets from results."""
        facets = {}
        
        # Entity type facet
        type_counts: dict[str, int] = {}
        for item in results:
            type_name = item.entity_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        facets["entity_type"] = [
            SearchFacet(
                field="entity_type",
                value=type_name,
                count=count,
                selected=SearchableEntity(type_name) in entity_types,
            )
            for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1])
        ]
        
        return facets
    
    async def _track_recent_search(
        self,
        query: str,
        user_id: str,
        entity_types: list[SearchableEntity],
        result_count: int,
    ):
        """Track a recent search."""
        recent = RecentSearch(
            id=str(uuid.uuid4()),
            query=query,
            user_id=user_id,
            entity_types=entity_types,
            result_count=result_count,
        )
        self.recent_searches.insert(0, recent)
        
        # Keep only last 100 searches
        self.recent_searches = self.recent_searches[:100]
    
    async def get_suggestions(
        self,
        query: str,
        entity_types: Optional[list[SearchableEntity]] = None,
        limit: int = 10,
    ) -> list[SearchSuggestion]:
        """Get search suggestions."""
        suggestions = []
        query_lower = query.lower()
        
        for doc_id, doc in self.documents.items():
            # Check entity type
            doc_type = SearchableEntity(doc.get("_type", "all"))
            if entity_types and SearchableEntity.ALL not in entity_types:
                if doc_type not in entity_types:
                    continue
            
            title = doc.get("_title", "")
            if query_lower in title.lower():
                # Highlight match
                pattern = re.compile(f"({re.escape(query)})", re.IGNORECASE)
                highlighted = pattern.sub(r"<em>\1</em>", title)
                
                suggestion = SearchSuggestion(
                    text=title,
                    highlighted=highlighted,
                    entity_type=doc_type,
                    entity_id=doc_id,
                    score=1.0 if title.lower().startswith(query_lower) else 0.5,
                )
                suggestions.append(suggestion)
        
        # Sort by score and limit
        suggestions.sort(key=lambda x: x.score, reverse=True)
        return suggestions[:limit]
    
    async def index_document(
        self,
        doc_id: str,
        entity_type: SearchableEntity,
        title: str,
        data: dict[str, Any],
        subtitle: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """Index a document for search."""
        doc = {
            "_type": entity_type.value,
            "_title": title,
            "_subtitle": subtitle,
            "_description": description,
            "_url": url,
            "_created_at": datetime.utcnow(),
            "_updated_at": datetime.utcnow(),
            "_metadata": {},
            **data,
        }
        self.documents[doc_id] = doc
        
        # Update index stats
        for idx in self.indexes.values():
            if idx.entity_type == entity_type:
                idx.document_count += 1
                idx.last_indexed = datetime.utcnow()
                break
    
    async def update_document(self, doc_id: str, data: dict[str, Any]):
        """Update an indexed document."""
        if doc_id in self.documents:
            self.documents[doc_id].update(data)
            self.documents[doc_id]["_updated_at"] = datetime.utcnow()
    
    async def delete_document(self, doc_id: str):
        """Delete a document from the index."""
        if doc_id in self.documents:
            doc = self.documents.pop(doc_id)
            
            # Update index stats
            doc_type = SearchableEntity(doc.get("_type", "all"))
            for idx in self.indexes.values():
                if idx.entity_type == doc_type:
                    idx.document_count = max(0, idx.document_count - 1)
                    break
    
    async def bulk_index(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Bulk index documents."""
        indexed = 0
        failed = 0
        
        for doc in documents:
            try:
                await self.index_document(
                    doc_id=doc["id"],
                    entity_type=SearchableEntity(doc["type"]),
                    title=doc["title"],
                    data=doc.get("data", {}),
                    subtitle=doc.get("subtitle"),
                    description=doc.get("description"),
                    url=doc.get("url"),
                )
                indexed += 1
            except Exception:
                failed += 1
        
        return {
            "indexed": indexed,
            "failed": failed,
            "total": len(documents),
        }
    
    async def save_search(
        self,
        name: str,
        query: str,
        entity_types: list[SearchableEntity],
        filters: list[SearchFilter],
        user_id: str,
        is_public: bool = False,
        notification_enabled: bool = False,
    ) -> SavedSearch:
        """Save a search query."""
        saved = SavedSearch(
            id=str(uuid.uuid4()),
            name=name,
            query=query,
            entity_types=entity_types,
            filters=filters,
            user_id=user_id,
            is_public=is_public,
            notification_enabled=notification_enabled,
        )
        self.saved_searches[saved.id] = saved
        return saved
    
    async def get_saved_searches(
        self,
        user_id: str,
        include_public: bool = True,
    ) -> list[SavedSearch]:
        """Get saved searches for a user."""
        searches = []
        for search in self.saved_searches.values():
            if search.user_id == user_id:
                searches.append(search)
            elif include_public and search.is_public:
                searches.append(search)
        return searches
    
    async def execute_saved_search(
        self,
        search_id: str,
        page: int = 1,
        page_size: int = 20,
        user_id: Optional[str] = None,
    ) -> Optional[SearchResult]:
        """Execute a saved search."""
        saved = self.saved_searches.get(search_id)
        if not saved:
            return None
        
        # Update usage stats
        saved.last_used = datetime.utcnow()
        saved.use_count += 1
        
        return await self.search(
            query=saved.query,
            entity_types=saved.entity_types,
            filters=saved.filters,
            page=page,
            page_size=page_size,
            user_id=user_id,
        )
    
    async def delete_saved_search(self, search_id: str, user_id: str) -> bool:
        """Delete a saved search."""
        saved = self.saved_searches.get(search_id)
        if saved and saved.user_id == user_id:
            del self.saved_searches[search_id]
            return True
        return False
    
    async def get_recent_searches(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[RecentSearch]:
        """Get recent searches for a user."""
        user_searches = [s for s in self.recent_searches if s.user_id == user_id]
        return user_searches[:limit]
    
    async def clear_recent_searches(self, user_id: str):
        """Clear recent searches for a user."""
        self.recent_searches = [
            s for s in self.recent_searches if s.user_id != user_id
        ]
    
    async def get_index_stats(self) -> dict[str, Any]:
        """Get search index statistics."""
        return {
            "total_documents": len(self.documents),
            "indexes": [
                {
                    "id": idx.id,
                    "entity_type": idx.entity_type.value,
                    "document_count": idx.document_count,
                    "enabled": idx.enabled,
                    "last_indexed": idx.last_indexed.isoformat() if idx.last_indexed else None,
                }
                for idx in self.indexes.values()
            ],
            "saved_searches_count": len(self.saved_searches),
            "recent_searches_count": len(self.recent_searches),
        }
    
    async def reindex_all(self) -> dict[str, Any]:
        """Trigger reindexing of all documents."""
        # In production, this would trigger a background reindexing job
        for idx in self.indexes.values():
            idx.last_indexed = datetime.utcnow()
        
        return {
            "status": "triggered",
            "document_count": len(self.documents),
            "indexes_count": len(self.indexes),
        }


# Singleton instance
_search_service: Optional[SearchService] = None


def get_search_service() -> SearchService:
    """Get or create search service singleton."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
