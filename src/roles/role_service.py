"""
Role Service - Role-Based Access Control
=========================================
Handles roles, permissions, and access control.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class ResourceType(str, Enum):
    """Resource types for permissions."""
    CONTACTS = "contacts"
    ACCOUNTS = "accounts"
    DEALS = "deals"
    ACTIVITIES = "activities"
    TASKS = "tasks"
    NOTES = "notes"
    EMAILS = "emails"
    CALLS = "calls"
    MEETINGS = "meetings"
    DOCUMENTS = "documents"
    QUOTES = "quotes"
    INVOICES = "invoices"
    CONTRACTS = "contracts"
    PRODUCTS = "products"
    REPORTS = "reports"
    ANALYTICS = "analytics"
    CAMPAIGNS = "campaigns"
    SEQUENCES = "sequences"
    TEMPLATES = "templates"
    INTEGRATIONS = "integrations"
    SETTINGS = "settings"
    USERS = "users"
    ROLES = "roles"
    TEAMS = "teams"
    TERRITORIES = "territories"
    WORKFLOWS = "workflows"
    API_KEYS = "api_keys"
    WEBHOOKS = "webhooks"
    EXPORTS = "exports"
    IMPORTS = "imports"
    AUDIT = "audit"
    ALL = "*"


class Action(str, Enum):
    """Actions for permissions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    SHARE = "share"
    ASSIGN = "assign"
    APPROVE = "approve"
    EXECUTE = "execute"
    MANAGE = "manage"
    ALL = "*"


class AccessScope(str, Enum):
    """Access scope for data visibility."""
    OWN = "own"  # Only records they own
    TEAM = "team"  # Records owned by their team
    TERRITORY = "territory"  # Records in their territory
    ALL = "all"  # All records


@dataclass
class Permission:
    """A permission definition."""
    id: str
    resource: ResourceType
    action: Action
    scope: AccessScope = AccessScope.ALL
    
    # Conditions (for field-level or conditional access)
    conditions: dict[str, Any] = field(default_factory=dict)
    
    def matches(self, resource: ResourceType, action: Action) -> bool:
        """Check if permission matches request."""
        resource_match = self.resource == ResourceType.ALL or self.resource == resource
        action_match = self.action == Action.ALL or self.action == action
        return resource_match and action_match


@dataclass
class Role:
    """A role with permissions."""
    id: str
    name: str
    description: Optional[str] = None
    
    # Permissions
    permissions: list[Permission] = field(default_factory=list)
    
    # Hierarchy
    parent_role_id: Optional[str] = None
    level: int = 0  # 0 = lowest, higher = more access
    
    # System role
    is_system: bool = False  # Cannot be deleted
    is_default: bool = False  # Assigned to new users
    
    # Status
    is_active: bool = True
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RoleAssignment:
    """A role assignment to a user."""
    id: str
    user_id: str
    role_id: str
    
    # Optional scoping
    team_id: Optional[str] = None
    territory_id: Optional[str] = None
    
    # Temporary assignment
    expires_at: Optional[datetime] = None
    
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    assigned_by: Optional[str] = None


class RoleService:
    """Service for role-based access control."""
    
    def __init__(self):
        self.roles: dict[str, Role] = {}
        self.assignments: dict[str, list[RoleAssignment]] = {}  # user_id -> assignments
        self._init_system_roles()
    
    def _init_system_roles(self) -> None:
        """Initialize system roles."""
        # Admin role - full access
        admin = Role(
            id="admin",
            name="Administrator",
            description="Full system access",
            level=100,
            is_system=True,
            permissions=[
                Permission(
                    id="admin-all",
                    resource=ResourceType.ALL,
                    action=Action.ALL,
                    scope=AccessScope.ALL
                )
            ]
        )
        self.roles["admin"] = admin
        
        # Manager role
        manager = Role(
            id="manager",
            name="Sales Manager",
            description="Manage team and view all data",
            level=50,
            is_system=True,
            permissions=[
                Permission(id="mgr-contacts", resource=ResourceType.CONTACTS, action=Action.ALL, scope=AccessScope.TEAM),
                Permission(id="mgr-accounts", resource=ResourceType.ACCOUNTS, action=Action.ALL, scope=AccessScope.TEAM),
                Permission(id="mgr-deals", resource=ResourceType.DEALS, action=Action.ALL, scope=AccessScope.TEAM),
                Permission(id="mgr-reports", resource=ResourceType.REPORTS, action=Action.READ, scope=AccessScope.TEAM),
                Permission(id="mgr-analytics", resource=ResourceType.ANALYTICS, action=Action.READ, scope=AccessScope.TEAM),
                Permission(id="mgr-users", resource=ResourceType.USERS, action=Action.READ, scope=AccessScope.TEAM),
                Permission(id="mgr-approve", resource=ResourceType.DEALS, action=Action.APPROVE, scope=AccessScope.TEAM),
            ]
        )
        self.roles["manager"] = manager
        
        # Sales rep role
        sales_rep = Role(
            id="sales_rep",
            name="Sales Representative",
            description="Standard sales user",
            level=10,
            is_system=True,
            is_default=True,
            permissions=[
                Permission(id="rep-contacts", resource=ResourceType.CONTACTS, action=Action.ALL, scope=AccessScope.OWN),
                Permission(id="rep-accounts", resource=ResourceType.ACCOUNTS, action=Action.ALL, scope=AccessScope.OWN),
                Permission(id="rep-deals", resource=ResourceType.DEALS, action=Action.ALL, scope=AccessScope.OWN),
                Permission(id="rep-activities", resource=ResourceType.ACTIVITIES, action=Action.ALL, scope=AccessScope.OWN),
                Permission(id="rep-tasks", resource=ResourceType.TASKS, action=Action.ALL, scope=AccessScope.OWN),
                Permission(id="rep-emails", resource=ResourceType.EMAILS, action=Action.ALL, scope=AccessScope.OWN),
                Permission(id="rep-calls", resource=ResourceType.CALLS, action=Action.ALL, scope=AccessScope.OWN),
                Permission(id="rep-meetings", resource=ResourceType.MEETINGS, action=Action.ALL, scope=AccessScope.OWN),
                Permission(id="rep-documents-read", resource=ResourceType.DOCUMENTS, action=Action.READ, scope=AccessScope.ALL),
                Permission(id="rep-templates-read", resource=ResourceType.TEMPLATES, action=Action.READ, scope=AccessScope.ALL),
                Permission(id="rep-products-read", resource=ResourceType.PRODUCTS, action=Action.READ, scope=AccessScope.ALL),
            ]
        )
        self.roles["sales_rep"] = sales_rep
        
        # Read-only role
        viewer = Role(
            id="viewer",
            name="Viewer",
            description="Read-only access",
            level=1,
            is_system=True,
            permissions=[
                Permission(id="view-contacts", resource=ResourceType.CONTACTS, action=Action.READ, scope=AccessScope.ALL),
                Permission(id="view-accounts", resource=ResourceType.ACCOUNTS, action=Action.READ, scope=AccessScope.ALL),
                Permission(id="view-deals", resource=ResourceType.DEALS, action=Action.READ, scope=AccessScope.ALL),
                Permission(id="view-reports", resource=ResourceType.REPORTS, action=Action.READ, scope=AccessScope.ALL),
            ]
        )
        self.roles["viewer"] = viewer
    
    # Role CRUD
    async def create_role(
        self,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[list[dict[str, Any]]] = None,
        parent_role_id: Optional[str] = None,
        level: int = 0
    ) -> Role:
        """Create a new role."""
        role = Role(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            parent_role_id=parent_role_id,
            level=level,
        )
        
        if permissions:
            for perm in permissions:
                permission = Permission(
                    id=str(uuid.uuid4()),
                    resource=ResourceType(perm.get("resource", "contacts")),
                    action=Action(perm.get("action", "read")),
                    scope=AccessScope(perm.get("scope", "own")),
                    conditions=perm.get("conditions", {}),
                )
                role.permissions.append(permission)
        
        self.roles[role.id] = role
        return role
    
    async def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        return self.roles.get(role_id)
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get a role by name."""
        for role in self.roles.values():
            if role.name.lower() == name.lower():
                return role
        return None
    
    async def update_role(
        self,
        role_id: str,
        updates: dict[str, Any]
    ) -> Optional[Role]:
        """Update a role."""
        role = self.roles.get(role_id)
        if not role or role.is_system:
            return None
        
        for key, value in updates.items():
            if hasattr(role, key) and key not in ["id", "is_system"]:
                setattr(role, key, value)
        
        role.updated_at = datetime.utcnow()
        return role
    
    async def delete_role(self, role_id: str) -> bool:
        """Delete a role."""
        role = self.roles.get(role_id)
        if not role or role.is_system:
            return False
        
        del self.roles[role_id]
        return True
    
    async def list_roles(
        self,
        active_only: bool = True,
        include_system: bool = True
    ) -> list[Role]:
        """List roles."""
        roles = list(self.roles.values())
        
        if active_only:
            roles = [r for r in roles if r.is_active]
        if not include_system:
            roles = [r for r in roles if not r.is_system]
        
        roles.sort(key=lambda r: r.level, reverse=True)
        return roles
    
    # Permission management
    async def add_permission(
        self,
        role_id: str,
        resource: ResourceType,
        action: Action,
        scope: AccessScope = AccessScope.OWN,
        conditions: Optional[dict[str, Any]] = None
    ) -> Optional[Permission]:
        """Add permission to a role."""
        role = self.roles.get(role_id)
        if not role:
            return None
        
        permission = Permission(
            id=str(uuid.uuid4()),
            resource=resource,
            action=action,
            scope=scope,
            conditions=conditions or {},
        )
        
        role.permissions.append(permission)
        role.updated_at = datetime.utcnow()
        
        return permission
    
    async def remove_permission(
        self,
        role_id: str,
        permission_id: str
    ) -> bool:
        """Remove permission from a role."""
        role = self.roles.get(role_id)
        if not role:
            return False
        
        original = len(role.permissions)
        role.permissions = [p for p in role.permissions if p.id != permission_id]
        
        if len(role.permissions) < original:
            role.updated_at = datetime.utcnow()
            return True
        
        return False
    
    # Role assignment
    async def assign_role(
        self,
        user_id: str,
        role_id: str,
        team_id: Optional[str] = None,
        territory_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        assigned_by: Optional[str] = None
    ) -> Optional[RoleAssignment]:
        """Assign a role to a user."""
        role = self.roles.get(role_id)
        if not role:
            return None
        
        assignment = RoleAssignment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            role_id=role_id,
            team_id=team_id,
            territory_id=territory_id,
            expires_at=expires_at,
            assigned_by=assigned_by,
        )
        
        if user_id not in self.assignments:
            self.assignments[user_id] = []
        
        self.assignments[user_id].append(assignment)
        return assignment
    
    async def revoke_role(
        self,
        user_id: str,
        role_id: str
    ) -> bool:
        """Revoke a role from a user."""
        if user_id not in self.assignments:
            return False
        
        original = len(self.assignments[user_id])
        self.assignments[user_id] = [
            a for a in self.assignments[user_id] if a.role_id != role_id
        ]
        
        return len(self.assignments[user_id]) < original
    
    async def get_user_roles(self, user_id: str) -> list[Role]:
        """Get all roles for a user."""
        assignments = self.assignments.get(user_id, [])
        
        # Filter expired assignments
        now = datetime.utcnow()
        valid = [a for a in assignments if not a.expires_at or a.expires_at > now]
        
        roles = []
        for assignment in valid:
            role = self.roles.get(assignment.role_id)
            if role and role.is_active:
                roles.append(role)
        
        return roles
    
    async def get_user_permissions(self, user_id: str) -> list[Permission]:
        """Get all permissions for a user (from all roles)."""
        roles = await self.get_user_roles(user_id)
        
        permissions = []
        seen = set()
        
        for role in roles:
            for perm in role.permissions:
                key = f"{perm.resource}:{perm.action}"
                if key not in seen:
                    permissions.append(perm)
                    seen.add(key)
        
        return permissions
    
    # Access checking
    async def check_access(
        self,
        user_id: str,
        resource: ResourceType,
        action: Action,
        owner_id: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> bool:
        """Check if user has access to perform action on resource."""
        permissions = await self.get_user_permissions(user_id)
        
        for perm in permissions:
            if perm.matches(resource, action):
                # Check scope
                if perm.scope == AccessScope.ALL:
                    return True
                elif perm.scope == AccessScope.OWN and owner_id == user_id:
                    return True
                elif perm.scope == AccessScope.TEAM:
                    # Would check team membership here
                    user_roles = await self.get_user_roles(user_id)
                    user_assignments = self.assignments.get(user_id, [])
                    for a in user_assignments:
                        if a.team_id == team_id:
                            return True
        
        return False
    
    async def get_accessible_scope(
        self,
        user_id: str,
        resource: ResourceType,
        action: Action
    ) -> Optional[AccessScope]:
        """Get the highest access scope for a user on a resource."""
        permissions = await self.get_user_permissions(user_id)
        
        highest_scope = None
        scope_order = [AccessScope.OWN, AccessScope.TEAM, AccessScope.TERRITORY, AccessScope.ALL]
        
        for perm in permissions:
            if perm.matches(resource, action):
                if highest_scope is None:
                    highest_scope = perm.scope
                elif scope_order.index(perm.scope) > scope_order.index(highest_scope):
                    highest_scope = perm.scope
        
        return highest_scope
    
    # Default role
    async def get_default_role(self) -> Optional[Role]:
        """Get the default role for new users."""
        for role in self.roles.values():
            if role.is_default:
                return role
        return None
    
    async def set_default_role(self, role_id: str) -> bool:
        """Set a role as the default."""
        role = self.roles.get(role_id)
        if not role:
            return False
        
        # Unset current default
        for r in self.roles.values():
            r.is_default = False
        
        role.is_default = True
        return True


# Singleton instance
_role_service: Optional[RoleService] = None


def get_role_service() -> RoleService:
    """Get role service singleton."""
    global _role_service
    if _role_service is None:
        _role_service = RoleService()
    return _role_service
