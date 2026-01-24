---
name: fixBug
description: Systematic bug fix following CaseyOS patterns
---
Fix the bug using a systematic approach:

## Bug Details
- **Location**: ${1:File or component with the bug}
- **Symptom**: ${2:What's happening}
- **Expected**: ${3:What should happen}

## Investigation Steps

### 1. Reproduce the Bug
```bash
# Run the failing test or command
pytest tests/test_${component}.py -v -s

# Or trigger via API
curl -X POST http://localhost:8000/api/... | jq
```

### 2. Add Diagnostic Logging
```python
from src.logger import get_logger
logger = get_logger(__name__)

# Add at the suspected location
logger.debug("Debug checkpoint", extra={
    "variable": variable,
    "type": type(variable).__name__,
    "context": str(context)[:200],
})
```

### 3. Identify Root Cause

Common causes:
| Symptom | Likely Cause |
|---------|--------------|
| `NoneType` error | Missing null check |
| `KeyError` | Dict access without `.get()` |
| Empty results | Filter too restrictive |
| Timeout | External API slow/down |
| 500 error | Unhandled exception |

### 4. Implement Fix

```python
# Before (buggy)
result = data["key"]  # Crashes if missing

# After (fixed)
result = data.get("key")
if result is None:
    logger.warning("Missing expected key", extra={"data_keys": list(data.keys())})
    return {"status": "error", "error": "Missing required field: key"}
```

### 5. Write Regression Test

```python
@pytest.mark.asyncio
async def test_handles_missing_key():
    """Regression test for bug: ${symptom}"""
    result = await function_under_test({"incomplete": "data"})
    assert result["status"] == "error"
    assert "Missing" in result["error"]
```

### 6. Verify Fix

```bash
# Run the specific test
pytest tests/test_${component}.py::test_handles_missing_key -v

# Run full test suite
make test
```

## Fix Checklist
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Regression test added
- [ ] All tests pass
- [ ] Logging added for future debugging
- [ ] No other code affected
