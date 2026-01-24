# Refactor Code

Improve code quality without changing behavior.

## Instructions

1. Identify the target:
   - Which file/module/function?
   - What's wrong with current code?
   - What should it look like after?

2. Ensure test coverage:
   - Check if tests exist
   - Run tests to establish baseline
   - Add tests if missing (before refactoring!)

3. Refactor incrementally:
   - Small changes, verify tests pass
   - Don't change behavior
   - Keep commits atomic

4. Common refactors:
   - Extract repeated code to function
   - Add type hints
   - Improve error handling
   - Add logging
   - Split large functions
   - Remove dead code

5. Verify:
   - All tests still pass
   - Manual verification if needed
   - No new errors in production

## Don't
- Change behavior while refactoring
- Refactor everything at once
- Skip testing
