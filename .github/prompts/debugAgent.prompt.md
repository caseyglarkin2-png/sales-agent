---
name: debugAgent
description: Debug and fix issues with a CaseyOS agent
---
Debug the specified CaseyOS agent by following this systematic approach:

## Agent to Debug
- **Agent**: ${1:AgentName}
- **Issue**: ${2:Describe the problem}

## Debugging Steps

### 1. Check Agent Structure
- Verify agent extends `BaseAgent`
- Verify `validate_input()` returns boolean
- Verify `execute()` returns dict with status

### 2. Add Diagnostic Logging
```python
logger.debug("Entering execute", extra={
    "action": context.get("action"),
    "context_keys": list(context.keys()),
})
```

### 3. Check Common Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `NoneType` error | Missing null check | Add `if value is not None:` |
| `KeyError` | Missing context key | Use `.get()` with default |
| Timeout | Slow external API | Add circuit breaker |
| Empty result | Query filter too strict | Log and check filters |
| Import error | Circular import | Use lazy imports |

### 4. Test in Isolation
```python
# In Python REPL or test file
import asyncio
from src.agents.domain.my_agent import MyAgent

async def test():
    agent = MyAgent()
    result = await agent.execute({"action": "list"})
    print(result)

asyncio.run(test())
```

### 5. Check Jarvis Integration
```python
from src.agents.jarvis import get_jarvis

jarvis = get_jarvis()
# Verify agent is registered
print(jarvis._agents.keys())
```

## Fix Template
```python
# Before (broken)
value = context["key"]  # Crashes if missing

# After (safe)
value = context.get("key")
if not value:
    return {"status": "error", "error": "Missing required key"}
```
