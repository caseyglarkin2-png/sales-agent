---
name: newRoute
description: Create a new FastAPI route following CaseyOS patterns
---
Create a new FastAPI route following CaseyOS conventions:

## Route Details
- **Endpoint**: `/api/${1:endpoint_path}`
- **Method**: ${2:GET|POST|PUT|DELETE}
- **Purpose**: ${3:Brief description}

## Implementation

1. Create route file at `src/routes/${route_name}.py`:

```python
"""${RouteName} API endpoints."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header

from src.db import get_session
from src.config import get_settings
from src.logger import get_logger
from src.security.csrf import verify_csrf_token
from src.security.admin_auth import verify_admin_token

logger = get_logger(__name__)
router = APIRouter(prefix="/api/${endpoint_path}", tags=["${tag}"])


@router.get("/")
async def list_items():
    """List all items."""
    async with get_session() as session:
        # Query logic
        return {"items": [], "count": 0}


@router.get("/{item_id}")
async def get_item(item_id: str):
    """Get a specific item."""
    async with get_session() as session:
        # Query logic
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"item": item}


@router.post("/")
async def create_item(
    data: dict,
    x_csrf_token: str = Header(...),
):
    """Create a new item. Requires CSRF token."""
    verify_csrf_token(x_csrf_token)
    async with get_session() as session:
        # Create logic
        return {"status": "created", "id": new_id}
```

2. Register in `src/main.py`:
```python
from src.routes.${route_name} import router as ${route_name}_router
app.include_router(${route_name}_router)
```

## Security Checklist
- [ ] State-changing endpoints require CSRF token
- [ ] Admin endpoints require X-Admin-Token header
- [ ] Use `async with get_session()` for DB access
- [ ] Add proper error handling with HTTPException
- [ ] Add logging with context
