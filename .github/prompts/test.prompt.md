# Run Tests

Execute tests and fix any failures.

## Instructions

1. Run all tests:
```bash
pytest tests/ -v --tb=short
```

2. If failures:
   - Identify which tests failed
   - Check if it's test bug or code bug
   - Fix the root cause
   - Re-run to verify

3. For specific file:
```bash
pytest tests/test_specific.py -v
```

4. For specific test:
```bash
pytest tests/test_file.py::test_function -v
```

5. With coverage:
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

## Common Test Issues
- Missing fixtures → Check `tests/conftest.py`
- Import errors → Check if module exists
- Async issues → Use `@pytest.mark.asyncio`
- DB issues → Tests should use test database
