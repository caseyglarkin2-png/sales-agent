"""
Custom Fields Service - Dynamic Field Management
=================================================
Handles custom field definitions and values for flexible data modeling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class FieldType(str, Enum):
    """Types of custom fields."""
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DECIMAL = "decimal"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    USER = "user"
    LOOKUP = "lookup"
    FORMULA = "formula"
    ROLLUP = "rollup"
    JSON = "json"
    FILE = "file"
    IMAGE = "image"


class EntityType(str, Enum):
    """Entity types that can have custom fields."""
    CONTACT = "contact"
    ACCOUNT = "account"
    DEAL = "deal"
    LEAD = "lead"
    PRODUCT = "product"
    QUOTE = "quote"
    INVOICE = "invoice"
    CONTRACT = "contract"
    TASK = "task"
    MEETING = "meeting"
    CALL = "call"
    EMAIL = "email"
    CAMPAIGN = "campaign"
    SEQUENCE = "sequence"


@dataclass
class FieldOption:
    """Option for select/multi-select fields."""
    value: str
    label: str
    color: Optional[str] = None
    is_default: bool = False
    sort_order: int = 0
    is_active: bool = True


@dataclass
class FieldValidation:
    """Validation rules for a field."""
    required: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    pattern_message: Optional[str] = None
    unique: bool = False
    custom_validation: Optional[str] = None


@dataclass
class FieldPermissions:
    """Field-level permissions."""
    viewable_by: list[str] = field(default_factory=list)  # Role IDs
    editable_by: list[str] = field(default_factory=list)
    required_for: list[str] = field(default_factory=list)


@dataclass
class CustomField:
    """Custom field definition."""
    id: str
    name: str
    api_name: str
    entity_type: EntityType
    field_type: FieldType
    label: str
    description: Optional[str] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None
    options: list[FieldOption] = field(default_factory=list)
    validation: FieldValidation = field(default_factory=FieldValidation)
    permissions: FieldPermissions = field(default_factory=FieldPermissions)
    lookup_entity: Optional[EntityType] = None  # For lookup fields
    formula: Optional[str] = None  # For formula fields
    rollup_config: Optional[dict[str, Any]] = None  # For rollup fields
    currency_code: Optional[str] = None
    decimal_places: int = 2
    sort_order: int = 0
    group: Optional[str] = None
    is_system: bool = False
    is_active: bool = True
    show_in_list: bool = True
    show_in_detail: bool = True
    show_in_create: bool = True
    show_in_edit: bool = True
    searchable: bool = False
    filterable: bool = True
    sortable: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomFieldValue:
    """Custom field value for an entity."""
    id: str
    field_id: str
    entity_type: EntityType
    entity_id: str
    value: Any
    display_value: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None


@dataclass
class FieldGroup:
    """Group for organizing custom fields."""
    id: str
    name: str
    entity_type: EntityType
    description: Optional[str] = None
    sort_order: int = 0
    is_expanded: bool = True
    is_active: bool = True


class CustomFieldsService:
    """Service for managing custom fields."""
    
    def __init__(self):
        """Initialize custom fields service."""
        self.fields: dict[str, CustomField] = {}
        self.values: dict[str, CustomFieldValue] = {}
        self.groups: dict[str, FieldGroup] = {}
        self._entity_index: dict[str, dict[str, list[str]]] = {}  # entity_type -> entity_id -> value_ids
    
    async def create_field(
        self,
        name: str,
        entity_type: EntityType,
        field_type: FieldType,
        label: str,
        description: Optional[str] = None,
        options: Optional[list[dict[str, Any]]] = None,
        validation: Optional[dict[str, Any]] = None,
        default_value: Optional[Any] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> CustomField:
        """Create a new custom field."""
        field_id = str(uuid.uuid4())
        api_name = name.lower().replace(" ", "_").replace("-", "_")
        
        # Convert options
        field_options = []
        if options:
            for i, opt in enumerate(options):
                field_options.append(FieldOption(
                    value=opt.get("value", opt.get("label", f"opt_{i}")),
                    label=opt.get("label", opt.get("value", f"Option {i}")),
                    color=opt.get("color"),
                    is_default=opt.get("is_default", False),
                    sort_order=i,
                ))
        
        # Convert validation
        field_validation = FieldValidation()
        if validation:
            for key, value in validation.items():
                if hasattr(field_validation, key):
                    setattr(field_validation, key, value)
        
        custom_field = CustomField(
            id=field_id,
            name=name,
            api_name=api_name,
            entity_type=entity_type,
            field_type=field_type,
            label=label,
            description=description,
            options=field_options,
            validation=field_validation,
            default_value=default_value,
            created_by=created_by,
            **kwargs
        )
        
        self.fields[field_id] = custom_field
        return custom_field
    
    async def get_field(self, field_id: str) -> Optional[CustomField]:
        """Get custom field by ID."""
        return self.fields.get(field_id)
    
    async def get_field_by_name(
        self,
        name: str,
        entity_type: EntityType
    ) -> Optional[CustomField]:
        """Get field by name and entity type."""
        api_name = name.lower().replace(" ", "_").replace("-", "_")
        
        for field in self.fields.values():
            if field.entity_type == entity_type and field.api_name == api_name:
                return field
        
        return None
    
    async def update_field(
        self,
        field_id: str,
        updates: dict[str, Any]
    ) -> Optional[CustomField]:
        """Update custom field."""
        custom_field = self.fields.get(field_id)
        if not custom_field:
            return None
        
        if custom_field.is_system:
            # Only allow limited updates to system fields
            updates = {k: v for k, v in updates.items() 
                      if k in ['label', 'description', 'help_text', 'show_in_list', 'sort_order']}
        
        for key, value in updates.items():
            if hasattr(custom_field, key) and key not in ['id', 'api_name', 'entity_type', 'field_type', 'is_system', 'created_at']:
                setattr(custom_field, key, value)
        
        custom_field.updated_at = datetime.utcnow()
        return custom_field
    
    async def delete_field(self, field_id: str) -> bool:
        """Delete custom field (soft delete)."""
        custom_field = self.fields.get(field_id)
        if not custom_field or custom_field.is_system:
            return False
        
        custom_field.is_active = False
        custom_field.updated_at = datetime.utcnow()
        return True
    
    async def list_fields(
        self,
        entity_type: Optional[EntityType] = None,
        field_type: Optional[FieldType] = None,
        group: Optional[str] = None,
        active_only: bool = True,
        include_system: bool = True,
    ) -> list[CustomField]:
        """List custom fields with filters."""
        fields = list(self.fields.values())
        
        if active_only:
            fields = [f for f in fields if f.is_active]
        
        if entity_type:
            fields = [f for f in fields if f.entity_type == entity_type]
        
        if field_type:
            fields = [f for f in fields if f.field_type == field_type]
        
        if group:
            fields = [f for f in fields if f.group == group]
        
        if not include_system:
            fields = [f for f in fields if not f.is_system]
        
        return sorted(fields, key=lambda f: f.sort_order)
    
    # Field options management
    async def add_option(
        self,
        field_id: str,
        value: str,
        label: str,
        color: Optional[str] = None,
    ) -> Optional[FieldOption]:
        """Add option to a select field."""
        custom_field = self.fields.get(field_id)
        if not custom_field or custom_field.field_type not in [FieldType.SELECT, FieldType.MULTI_SELECT]:
            return None
        
        option = FieldOption(
            value=value,
            label=label,
            color=color,
            sort_order=len(custom_field.options),
        )
        
        custom_field.options.append(option)
        custom_field.updated_at = datetime.utcnow()
        
        return option
    
    async def remove_option(
        self,
        field_id: str,
        option_value: str
    ) -> bool:
        """Remove option from a select field."""
        custom_field = self.fields.get(field_id)
        if not custom_field:
            return False
        
        for option in custom_field.options:
            if option.value == option_value:
                option.is_active = False
                custom_field.updated_at = datetime.utcnow()
                return True
        
        return False
    
    async def reorder_options(
        self,
        field_id: str,
        option_order: list[str]
    ) -> bool:
        """Reorder field options."""
        custom_field = self.fields.get(field_id)
        if not custom_field:
            return False
        
        for i, value in enumerate(option_order):
            for option in custom_field.options:
                if option.value == value:
                    option.sort_order = i
                    break
        
        custom_field.options.sort(key=lambda o: o.sort_order)
        custom_field.updated_at = datetime.utcnow()
        
        return True
    
    # Field values management
    async def set_value(
        self,
        field_id: str,
        entity_id: str,
        value: Any,
        updated_by: Optional[str] = None,
    ) -> Optional[CustomFieldValue]:
        """Set a custom field value for an entity."""
        custom_field = self.fields.get(field_id)
        if not custom_field or not custom_field.is_active:
            return None
        
        # Validate value
        if not await self._validate_value(custom_field, value):
            return None
        
        # Check for existing value
        existing_value_id = await self._find_value_id(
            field_id, custom_field.entity_type, entity_id
        )
        
        if existing_value_id:
            # Update existing
            field_value = self.values[existing_value_id]
            field_value.value = value
            field_value.display_value = await self._get_display_value(custom_field, value)
            field_value.updated_at = datetime.utcnow()
            field_value.updated_by = updated_by
            return field_value
        
        # Create new
        value_id = str(uuid.uuid4())
        
        field_value = CustomFieldValue(
            id=value_id,
            field_id=field_id,
            entity_type=custom_field.entity_type,
            entity_id=entity_id,
            value=value,
            display_value=await self._get_display_value(custom_field, value),
            updated_by=updated_by,
        )
        
        self.values[value_id] = field_value
        
        # Update index
        entity_key = custom_field.entity_type.value
        if entity_key not in self._entity_index:
            self._entity_index[entity_key] = {}
        if entity_id not in self._entity_index[entity_key]:
            self._entity_index[entity_key][entity_id] = []
        self._entity_index[entity_key][entity_id].append(value_id)
        
        return field_value
    
    async def get_value(
        self,
        field_id: str,
        entity_id: str
    ) -> Optional[CustomFieldValue]:
        """Get a custom field value."""
        custom_field = self.fields.get(field_id)
        if not custom_field:
            return None
        
        value_id = await self._find_value_id(
            field_id, custom_field.entity_type, entity_id
        )
        
        if value_id:
            return self.values.get(value_id)
        
        return None
    
    async def get_entity_values(
        self,
        entity_type: EntityType,
        entity_id: str,
        include_empty: bool = False
    ) -> dict[str, Any]:
        """Get all custom field values for an entity."""
        result = {}
        
        entity_key = entity_type.value
        value_ids = self._entity_index.get(entity_key, {}).get(entity_id, [])
        
        for value_id in value_ids:
            field_value = self.values.get(value_id)
            if field_value:
                custom_field = self.fields.get(field_value.field_id)
                if custom_field:
                    result[custom_field.api_name] = {
                        "field_id": custom_field.id,
                        "label": custom_field.label,
                        "value": field_value.value,
                        "display_value": field_value.display_value,
                        "type": custom_field.field_type.value,
                    }
        
        # Include empty fields if requested
        if include_empty:
            for custom_field in self.fields.values():
                if custom_field.entity_type == entity_type and custom_field.api_name not in result:
                    result[custom_field.api_name] = {
                        "field_id": custom_field.id,
                        "label": custom_field.label,
                        "value": custom_field.default_value,
                        "display_value": None,
                        "type": custom_field.field_type.value,
                    }
        
        return result
    
    async def delete_value(
        self,
        field_id: str,
        entity_id: str
    ) -> bool:
        """Delete a custom field value."""
        custom_field = self.fields.get(field_id)
        if not custom_field:
            return False
        
        value_id = await self._find_value_id(
            field_id, custom_field.entity_type, entity_id
        )
        
        if value_id:
            del self.values[value_id]
            
            entity_key = custom_field.entity_type.value
            if entity_key in self._entity_index and entity_id in self._entity_index[entity_key]:
                self._entity_index[entity_key][entity_id].remove(value_id)
            
            return True
        
        return False
    
    async def bulk_set_values(
        self,
        entity_type: EntityType,
        entity_id: str,
        values: dict[str, Any],
        updated_by: Optional[str] = None,
    ) -> dict[str, bool]:
        """Bulk set custom field values for an entity."""
        results = {}
        
        for field_name, value in values.items():
            custom_field = await self.get_field_by_name(field_name, entity_type)
            if custom_field:
                result = await self.set_value(
                    custom_field.id, entity_id, value, updated_by
                )
                results[field_name] = result is not None
            else:
                results[field_name] = False
        
        return results
    
    # Field groups
    async def create_group(
        self,
        name: str,
        entity_type: EntityType,
        description: Optional[str] = None,
    ) -> FieldGroup:
        """Create a field group."""
        group_id = str(uuid.uuid4())
        
        group = FieldGroup(
            id=group_id,
            name=name,
            entity_type=entity_type,
            description=description,
            sort_order=len([g for g in self.groups.values() if g.entity_type == entity_type]),
        )
        
        self.groups[group_id] = group
        return group
    
    async def list_groups(
        self,
        entity_type: Optional[EntityType] = None,
        active_only: bool = True,
    ) -> list[FieldGroup]:
        """List field groups."""
        groups = list(self.groups.values())
        
        if active_only:
            groups = [g for g in groups if g.is_active]
        
        if entity_type:
            groups = [g for g in groups if g.entity_type == entity_type]
        
        return sorted(groups, key=lambda g: g.sort_order)
    
    # Helper methods
    async def _validate_value(
        self,
        field: CustomField,
        value: Any
    ) -> bool:
        """Validate a field value."""
        if value is None:
            return not field.validation.required
        
        # Type-specific validation
        if field.field_type in [FieldType.NUMBER, FieldType.DECIMAL, FieldType.CURRENCY, FieldType.PERCENTAGE]:
            try:
                num_value = float(value)
                if field.validation.min_value is not None and num_value < field.validation.min_value:
                    return False
                if field.validation.max_value is not None and num_value > field.validation.max_value:
                    return False
            except (ValueError, TypeError):
                return False
        
        elif field.field_type in [FieldType.TEXT, FieldType.TEXTAREA, FieldType.EMAIL, FieldType.PHONE, FieldType.URL]:
            str_value = str(value)
            if field.validation.min_length is not None and len(str_value) < field.validation.min_length:
                return False
            if field.validation.max_length is not None and len(str_value) > field.validation.max_length:
                return False
        
        elif field.field_type == FieldType.SELECT:
            valid_values = [o.value for o in field.options if o.is_active]
            if value not in valid_values:
                return False
        
        elif field.field_type == FieldType.MULTI_SELECT:
            valid_values = [o.value for o in field.options if o.is_active]
            if isinstance(value, list):
                for v in value:
                    if v not in valid_values:
                        return False
            else:
                return False
        
        return True
    
    async def _get_display_value(
        self,
        field: CustomField,
        value: Any
    ) -> Optional[str]:
        """Get display value for a field value."""
        if value is None:
            return None
        
        if field.field_type == FieldType.SELECT:
            for option in field.options:
                if option.value == value:
                    return option.label
            return str(value)
        
        elif field.field_type == FieldType.MULTI_SELECT:
            if isinstance(value, list):
                labels = []
                for v in value:
                    for option in field.options:
                        if option.value == v:
                            labels.append(option.label)
                            break
                return ", ".join(labels)
            return str(value)
        
        elif field.field_type == FieldType.CURRENCY:
            return f"{field.currency_code or '$'}{value:,.{field.decimal_places}f}"
        
        elif field.field_type == FieldType.PERCENTAGE:
            return f"{value:.{field.decimal_places}f}%"
        
        elif field.field_type == FieldType.BOOLEAN:
            return "Yes" if value else "No"
        
        return str(value)
    
    async def _find_value_id(
        self,
        field_id: str,
        entity_type: EntityType,
        entity_id: str
    ) -> Optional[str]:
        """Find value ID for a field/entity combination."""
        entity_key = entity_type.value
        value_ids = self._entity_index.get(entity_key, {}).get(entity_id, [])
        
        for value_id in value_ids:
            field_value = self.values.get(value_id)
            if field_value and field_value.field_id == field_id:
                return value_id
        
        return None
    
    async def get_field_usage(self, field_id: str) -> dict[str, Any]:
        """Get usage statistics for a field."""
        custom_field = self.fields.get(field_id)
        if not custom_field:
            return {}
        
        values_count = sum(
            1 for v in self.values.values()
            if v.field_id == field_id
        )
        
        # Value distribution for select fields
        distribution = {}
        if custom_field.field_type in [FieldType.SELECT, FieldType.MULTI_SELECT]:
            for v in self.values.values():
                if v.field_id == field_id and v.value:
                    if isinstance(v.value, list):
                        for val in v.value:
                            distribution[val] = distribution.get(val, 0) + 1
                    else:
                        distribution[v.value] = distribution.get(v.value, 0) + 1
        
        return {
            "field_id": field_id,
            "name": custom_field.name,
            "entity_type": custom_field.entity_type.value,
            "values_count": values_count,
            "distribution": distribution,
        }


# Singleton instance
_custom_fields_service: Optional[CustomFieldsService] = None


def get_custom_fields_service() -> CustomFieldsService:
    """Get custom fields service singleton."""
    global _custom_fields_service
    if _custom_fields_service is None:
        _custom_fields_service = CustomFieldsService()
    return _custom_fields_service
