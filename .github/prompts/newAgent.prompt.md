---
name: newAgent
description: Scaffold a new CaseyOS agent following the BaseAgent pattern
---
Create a new CaseyOS agent following these requirements:

## Agent Details
- **Agent Name**: ${1:AgentName}
- **Domain**: ${2:content|fulfillment|contracts|ops|sales}
- **Purpose**: ${3:Brief description of what this agent does}

## Implementation Steps

1. Create the agent file at `src/agents/${domain}/${agent_name_snake}.py`

2. Follow this structure:
```python
"""${AgentName} - ${Purpose}.

Detailed description of the agent's capabilities.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class ${AgentName}(BaseAgent):
    """${Purpose}.
    
    Features:
    - Feature 1
    - Feature 2
    
    Example:
        agent = ${AgentName}()
        result = await agent.execute({"action": "list"})
    """

    def __init__(self, connectors=None):
        super().__init__(
            name="${Agent Name with Spaces}",
            description="${Purpose}"
        )
        # Add any connectors (hubspot, gmail, etc.)

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input context."""
        action = context.get("action", "list")
        # Add validation logic
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent action."""
        action = context.get("action", "list")
        
        if action == "create":
            return await self._create(context)
        elif action == "list":
            return await self._list(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _create(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new item."""
        # Implementation
        pass

    async def _list(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List items."""
        # Implementation
        pass
```

3. Export from domain `__init__.py`
4. Register in `src/agents/jarvis.py`
5. Add unit tests in `tests/unit/test_agents.py`

## Checklist
- [ ] Extends BaseAgent
- [ ] Has validate_input() method
- [ ] Has execute() method with action routing
- [ ] Uses structured logging
- [ ] Has docstrings and examples
- [ ] Registered in Jarvis
