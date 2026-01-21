"""
Tags Service - Entity Tagging System
=====================================
Handles tag creation, assignment, and search across entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class EntityType(str, Enum):
    """Entity types that can be tagged."""
    CONTACT = "contact"
    ACCOUNT = "account"
    DEAL = "deal"
    LEAD = "lead"
    TASK = "task"
    MEETING = "meeting"
    CALL = "call"
    EMAIL = "email"
    DOCUMENT = "document"
    CAMPAIGN = "campaign"
    SEQUENCE = "sequence"
    TEMPLATE = "template"
    PRODUCT = "product"
    QUOTE = "quote"
    INVOICE = "invoice"
    CONTRACT = "contract"


@dataclass
class TagCategory:
    """Category for organizing tags."""
    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Tag:
    """Tag model."""
    id: str
    name: str
    slug: str
    color: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    allowed_entity_types: list[EntityType] = field(default_factory=list)  # Empty = all types
    usage_count: int = 0
    is_system: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityTag:
    """Association between a tag and an entity."""
    id: str
    tag_id: str
    entity_type: EntityType
    entity_id: str
    tagged_at: datetime = field(default_factory=datetime.utcnow)
    tagged_by: Optional[str] = None


class TagsService:
    """Service for managing tags."""
    
    def __init__(self):
        """Initialize tags service."""
        self.tags: dict[str, Tag] = {}
        self.entity_tags: dict[str, EntityTag] = {}
        self.categories: dict[str, TagCategory] = {}
        self._slug_index: dict[str, str] = {}  # slug -> tag_id
        self._entity_index: dict[str, list[str]] = {}  # entity_key -> entity_tag_ids
        self._tag_entities: dict[str, list[str]] = {}  # tag_id -> entity_tag_ids
        
        # Initialize common tags
        self._init_common_tags()
    
    def _init_common_tags(self):
        """Initialize common/system tags."""
        common_tags = [
            ("Hot Lead", "#ef4444", "High priority lead"),
            ("VIP", "#8b5cf6", "VIP customer"),
            ("Competitor", "#f97316", "Competitor account"),
            ("Partner", "#22c55e", "Partner organization"),
            ("Enterprise", "#3b82f6", "Enterprise account"),
            ("SMB", "#06b6d4", "Small/medium business"),
            ("At Risk", "#dc2626", "At risk of churning"),
            ("Expansion", "#84cc16", "Expansion opportunity"),
            ("Follow Up", "#eab308", "Needs follow up"),
            ("Decision Maker", "#a855f7", "Key decision maker"),
        ]
        
        for name, color, description in common_tags:
            slug = name.lower().replace(" ", "-")
            tag_id = str(uuid.uuid4())
            
            self.tags[tag_id] = Tag(
                id=tag_id,
                name=name,
                slug=slug,
                color=color,
                description=description,
                is_system=True,
            )
            self._slug_index[slug] = tag_id
            self._tag_entities[tag_id] = []
    
    async def create_tag(
        self,
        name: str,
        color: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[str] = None,
        allowed_entity_types: Optional[list[EntityType]] = None,
        created_by: Optional[str] = None,
    ) -> Tag:
        """Create a new tag."""
        tag_id = str(uuid.uuid4())
        slug = name.lower().replace(" ", "-").replace("_", "-")
        
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while slug in self._slug_index:
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        tag = Tag(
            id=tag_id,
            name=name,
            slug=slug,
            color=color or "#6b7280",
            description=description,
            category_id=category_id,
            allowed_entity_types=allowed_entity_types or [],
            created_by=created_by,
        )
        
        self.tags[tag_id] = tag
        self._slug_index[slug] = tag_id
        self._tag_entities[tag_id] = []
        
        return tag
    
    async def get_tag(self, tag_id: str) -> Optional[Tag]:
        """Get tag by ID."""
        return self.tags.get(tag_id)
    
    async def get_tag_by_slug(self, slug: str) -> Optional[Tag]:
        """Get tag by slug."""
        tag_id = self._slug_index.get(slug)
        if tag_id:
            return self.tags.get(tag_id)
        return None
    
    async def update_tag(
        self,
        tag_id: str,
        updates: dict[str, Any]
    ) -> Optional[Tag]:
        """Update tag."""
        tag = self.tags.get(tag_id)
        if not tag:
            return None
        
        if tag.is_system:
            # Only allow limited updates to system tags
            updates = {k: v for k, v in updates.items() 
                      if k in ['color', 'description']}
        
        for key, value in updates.items():
            if hasattr(tag, key) and key not in ['id', 'slug', 'is_system', 'created_at', 'usage_count']:
                setattr(tag, key, value)
        
        tag.updated_at = datetime.utcnow()
        return tag
    
    async def delete_tag(self, tag_id: str) -> bool:
        """Delete tag (soft delete)."""
        tag = self.tags.get(tag_id)
        if not tag or tag.is_system:
            return False
        
        tag.is_active = False
        tag.updated_at = datetime.utcnow()
        return True
    
    async def list_tags(
        self,
        category_id: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
        search: Optional[str] = None,
        active_only: bool = True,
        include_system: bool = True,
    ) -> list[Tag]:
        """List tags with filters."""
        tags = list(self.tags.values())
        
        if active_only:
            tags = [t for t in tags if t.is_active]
        
        if not include_system:
            tags = [t for t in tags if not t.is_system]
        
        if category_id:
            tags = [t for t in tags if t.category_id == category_id]
        
        if entity_type:
            tags = [
                t for t in tags
                if not t.allowed_entity_types or entity_type in t.allowed_entity_types
            ]
        
        if search:
            search_lower = search.lower()
            tags = [t for t in tags if search_lower in t.name.lower()]
        
        return sorted(tags, key=lambda t: (-t.usage_count, t.name))
    
    async def search_tags(
        self,
        query: str,
        limit: int = 10
    ) -> list[Tag]:
        """Search tags by name."""
        query_lower = query.lower()
        
        matches = []
        for tag in self.tags.values():
            if tag.is_active and query_lower in tag.name.lower():
                matches.append(tag)
        
        # Sort by relevance (exact match first, then by usage)
        def sort_key(t: Tag):
            exact = t.name.lower() == query_lower
            starts_with = t.name.lower().startswith(query_lower)
            return (not exact, not starts_with, -t.usage_count)
        
        return sorted(matches, key=sort_key)[:limit]
    
    # Tag assignment
    async def tag_entity(
        self,
        tag_id: str,
        entity_type: EntityType,
        entity_id: str,
        tagged_by: Optional[str] = None,
    ) -> Optional[EntityTag]:
        """Tag an entity."""
        tag = self.tags.get(tag_id)
        if not tag or not tag.is_active:
            return None
        
        # Check if allowed for this entity type
        if tag.allowed_entity_types and entity_type not in tag.allowed_entity_types:
            return None
        
        # Check if already tagged
        entity_key = f"{entity_type.value}:{entity_id}"
        existing_ids = self._entity_index.get(entity_key, [])
        for et_id in existing_ids:
            et = self.entity_tags.get(et_id)
            if et and et.tag_id == tag_id:
                return et  # Already tagged
        
        # Create association
        et_id = str(uuid.uuid4())
        entity_tag = EntityTag(
            id=et_id,
            tag_id=tag_id,
            entity_type=entity_type,
            entity_id=entity_id,
            tagged_by=tagged_by,
        )
        
        self.entity_tags[et_id] = entity_tag
        
        # Update indexes
        if entity_key not in self._entity_index:
            self._entity_index[entity_key] = []
        self._entity_index[entity_key].append(et_id)
        self._tag_entities[tag_id].append(et_id)
        
        # Update usage count
        tag.usage_count += 1
        
        return entity_tag
    
    async def untag_entity(
        self,
        tag_id: str,
        entity_type: EntityType,
        entity_id: str
    ) -> bool:
        """Remove a tag from an entity."""
        entity_key = f"{entity_type.value}:{entity_id}"
        existing_ids = self._entity_index.get(entity_key, [])
        
        for et_id in existing_ids:
            et = self.entity_tags.get(et_id)
            if et and et.tag_id == tag_id:
                del self.entity_tags[et_id]
                self._entity_index[entity_key].remove(et_id)
                self._tag_entities[tag_id].remove(et_id)
                
                # Update usage count
                tag = self.tags.get(tag_id)
                if tag:
                    tag.usage_count = max(0, tag.usage_count - 1)
                
                return True
        
        return False
    
    async def get_entity_tags(
        self,
        entity_type: EntityType,
        entity_id: str
    ) -> list[Tag]:
        """Get all tags for an entity."""
        entity_key = f"{entity_type.value}:{entity_id}"
        et_ids = self._entity_index.get(entity_key, [])
        
        tags = []
        for et_id in et_ids:
            et = self.entity_tags.get(et_id)
            if et:
                tag = self.tags.get(et.tag_id)
                if tag and tag.is_active:
                    tags.append(tag)
        
        return tags
    
    async def get_tagged_entities(
        self,
        tag_id: str,
        entity_type: Optional[EntityType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get all entities with a specific tag."""
        et_ids = self._tag_entities.get(tag_id, [])
        
        entities = []
        for et_id in et_ids:
            et = self.entity_tags.get(et_id)
            if et:
                if entity_type and et.entity_type != entity_type:
                    continue
                entities.append({
                    "entity_type": et.entity_type.value,
                    "entity_id": et.entity_id,
                    "tagged_at": et.tagged_at.isoformat(),
                    "tagged_by": et.tagged_by,
                })
        
        return entities[offset:offset + limit]
    
    async def bulk_tag(
        self,
        tag_ids: list[str],
        entity_type: EntityType,
        entity_id: str,
        tagged_by: Optional[str] = None,
    ) -> dict[str, bool]:
        """Apply multiple tags to an entity."""
        results = {}
        for tag_id in tag_ids:
            result = await self.tag_entity(tag_id, entity_type, entity_id, tagged_by)
            results[tag_id] = result is not None
        return results
    
    async def replace_tags(
        self,
        entity_type: EntityType,
        entity_id: str,
        tag_ids: list[str],
        tagged_by: Optional[str] = None,
    ) -> list[Tag]:
        """Replace all tags on an entity."""
        # Remove existing tags
        current_tags = await self.get_entity_tags(entity_type, entity_id)
        for tag in current_tags:
            await self.untag_entity(tag.id, entity_type, entity_id)
        
        # Add new tags
        for tag_id in tag_ids:
            await self.tag_entity(tag_id, entity_type, entity_id, tagged_by)
        
        return await self.get_entity_tags(entity_type, entity_id)
    
    # Categories
    async def create_category(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
    ) -> TagCategory:
        """Create a tag category."""
        cat_id = str(uuid.uuid4())
        
        category = TagCategory(
            id=cat_id,
            name=name,
            description=description,
            color=color,
            sort_order=len(self.categories),
        )
        
        self.categories[cat_id] = category
        return category
    
    async def list_categories(
        self,
        active_only: bool = True
    ) -> list[TagCategory]:
        """List tag categories."""
        categories = list(self.categories.values())
        
        if active_only:
            categories = [c for c in categories if c.is_active]
        
        return sorted(categories, key=lambda c: c.sort_order)
    
    async def get_tags_by_category(
        self,
        category_id: str,
        active_only: bool = True
    ) -> list[Tag]:
        """Get all tags in a category."""
        tags = [t for t in self.tags.values() if t.category_id == category_id]
        
        if active_only:
            tags = [t for t in tags if t.is_active]
        
        return sorted(tags, key=lambda t: t.name)
    
    # Analytics
    async def get_popular_tags(
        self,
        entity_type: Optional[EntityType] = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get most used tags."""
        tags = list(self.tags.values())
        
        if entity_type:
            tags = [
                t for t in tags
                if not t.allowed_entity_types or entity_type in t.allowed_entity_types
            ]
        
        tags = [t for t in tags if t.is_active]
        tags = sorted(tags, key=lambda t: -t.usage_count)[:limit]
        
        return [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "color": t.color,
                "usage_count": t.usage_count,
            }
            for t in tags
        ]
    
    async def get_tag_stats(self) -> dict[str, Any]:
        """Get tag statistics."""
        active_tags = [t for t in self.tags.values() if t.is_active]
        total_associations = len(self.entity_tags)
        
        # Usage by entity type
        usage_by_type: dict[str, int] = {}
        for et in self.entity_tags.values():
            type_name = et.entity_type.value
            usage_by_type[type_name] = usage_by_type.get(type_name, 0) + 1
        
        return {
            "total_tags": len(active_tags),
            "system_tags": len([t for t in active_tags if t.is_system]),
            "custom_tags": len([t for t in active_tags if not t.is_system]),
            "total_associations": total_associations,
            "categories_count": len([c for c in self.categories.values() if c.is_active]),
            "usage_by_entity_type": usage_by_type,
        }


# Singleton instance
_tags_service: Optional[TagsService] = None


def get_tags_service() -> TagsService:
    """Get tags service singleton."""
    global _tags_service
    if _tags_service is None:
        _tags_service = TagsService()
    return _tags_service
