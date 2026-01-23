#!/bin/bash
# Task 6.2: Data Retention & GDPR - Validation Script

set -e

echo "=== Task 6.2: Data Retention & GDPR - Validation ==="
echo ""

# Check 1: GDPR files created
echo "1. GDPR Files Created"
if [ -f "src/gdpr.py" ]; then
  echo "   ✅ src/gdpr.py"
else
  echo "   ❌ FAIL: src/gdpr.py not found"
  exit 1
fi

if [ -f "src/routes/gdpr.py" ]; then
  echo "   ✅ src/routes/gdpr.py"
else
  echo "   ❌ FAIL: src/routes/gdpr.py not found"
  exit 1
fi

if [ -f "src/tasks/retention.py" ]; then
  echo "   ✅ src/tasks/retention.py"
else
  echo "   ❌ FAIL: src/tasks/retention.py not found"
  exit 1
fi

echo ""

# Check 2: GDPR routes registered in main.py
echo "2. GDPR Routes Registered"
if grep -q "gdpr.router" src/main.py; then
  echo "   ✅ GDPR router included in main.py"
else
  echo "   ❌ FAIL: GDPR router not registered"
  exit 1
fi

echo ""

# Check 3: DELETE endpoint exists
echo "3. DELETE Endpoint Implementation"
if grep -q "@router.delete.*user" src/routes/gdpr.py; then
  echo "   ✅ DELETE /api/gdpr/user/{email} endpoint exists"
else
  echo "   ❌ FAIL: DELETE endpoint not found"
  exit 1
fi

echo ""

# Check 4: Automated cleanup task exists
echo "4. Automated Cleanup Task"
if grep -q "cleanup_old_drafts_task" src/tasks/retention.py; then
  echo "   ✅ cleanup_old_drafts_task implemented"
else
  echo "   ❌ FAIL: Cleanup task not found"
  exit 1
fi

if grep -q "@shared_task" src/tasks/retention.py; then
  echo "   ✅ Celery task decorators present"
else
  echo "   ❌ FAIL: Celery task decorators missing"
  exit 1
fi

echo ""

# Check 5: GDPR service methods
echo "5. GDPR Service Methods"
if grep -q "delete_user_data" src/gdpr.py; then
  echo "   ✅ delete_user_data() method exists"
else
  echo "   ❌ FAIL: delete_user_data() not found"
  exit 1
fi

if grep -q "cleanup_old_drafts" src/gdpr.py; then
  echo "   ✅ cleanup_old_drafts() method exists"
else
  echo "   ❌ FAIL: cleanup_old_drafts() not found"
  exit 1
fi

echo ""

# Check 6: Admin authentication on GDPR endpoints
echo "6. Admin Authentication"
if grep -q "require_admin_role" src/routes/gdpr.py; then
  echo "   ✅ Admin authentication required on DELETE endpoint"
else
  echo "   ⚠️  WARNING: Admin auth not found in GDPR routes"
fi

echo ""

# Check 7: Rate limiting on public endpoints
echo "7. Rate Limiting"
if grep -q "@rate_limit" src/routes/gdpr.py; then
  echo "   ✅ Rate limiting applied to GDPR endpoints"
else
  echo "   ⚠️  WARNING: Rate limiting not found"
fi

echo ""

# Check 8: Audit logging
echo "8. Audit Logging"
if grep -q "log_audit_event" src/gdpr.py; then
  echo "   ✅ Audit logging implemented"
else
  echo "   ⚠️  WARNING: Audit logging not found"
fi

echo ""

# Check 9: Python syntax validation
echo "9. Python Syntax Validation"
python -m py_compile src/gdpr.py src/routes/gdpr.py src/tasks/retention.py 2>/dev/null
if [ $? -eq 0 ]; then
  echo "   ✅ All Python files compile successfully"
else
  echo "   ❌ FAIL: Python syntax errors"
  exit 1
fi

echo ""
echo "✅ Task 6.2 Validation Complete!"
echo ""
echo "=== Manual Testing Commands ==="
echo ""
echo "1. Test retention policy endpoint:"
echo "   curl http://localhost:8000/api/gdpr/policy"
echo ""
echo "2. Test GDPR status:"
echo "   curl http://localhost:8000/api/gdpr/status"
echo ""
echo "3. Test user deletion (requires admin token):"
echo "   curl -X DELETE http://localhost:8000/api/gdpr/user/test@example.com \\"
echo "     -H 'X-Admin-Token: \$ADMIN_PASSWORD'"
echo ""
echo "4. Test cleanup task (dry run):"
echo "   curl -X POST 'http://localhost:8000/api/gdpr/cleanup-old-drafts?dry_run=true' \\"
echo "     -H 'X-Admin-Token: \$ADMIN_PASSWORD'"
echo ""
