"""Unit tests for secrets checker."""
import os
import pytest

from src.commands.check_secrets import (
    validate_var,
    check_secrets,
    format_report,
    VarStatus,
    VarCategory,
)


class TestSecretsChecker:
    """Test secrets readiness checker."""

    def test_validate_var_present(self):
        """Test validation detects present var."""
        os.environ["TEST_VAR"] = "valid_value"
        
        # Temporarily add to check
        from src.commands.check_secrets import ENV_VARS
        ENV_VARS["TEST_VAR"] = {
            "category": VarCategory.OPTIONAL,
            "description": "Test var",
            "validator": lambda v: True,
        }
        
        status, message = validate_var("TEST_VAR")
        
        assert status == VarStatus.PRESENT
        
        # Cleanup
        del ENV_VARS["TEST_VAR"]
        del os.environ["TEST_VAR"]

    def test_validate_var_missing(self):
        """Test validation detects missing var."""
        status, message = validate_var("NONEXISTENT_VAR_XYZ")
        
        assert status == VarStatus.MISSING

    def test_validate_var_invalid(self):
        """Test validation detects invalid format."""
        os.environ["GOOGLE_CREDENTIALS_FILE"] = "invalid_format.txt"
        
        status, message = validate_var("GOOGLE_CREDENTIALS_FILE")
        
        assert status == VarStatus.INVALID
        
        # Cleanup
        del os.environ["GOOGLE_CREDENTIALS_FILE"]

    def test_check_secrets_returns_dict(self):
        """Test check_secrets returns structured result."""
        results = check_secrets(strict=False)
        
        assert isinstance(results, dict)
        assert "total" in results
        assert "present" in results
        assert "missing" in results
        assert "invalid" in results
        assert "details" in results
        assert "exit_code" in results

    def test_check_secrets_strict_mode(self):
        """Test strict mode fails if any variable missing."""
        results = check_secrets(strict=True)
        
        if results["missing"] > 0:
            assert results["exit_code"] != 0
        else:
            assert results["exit_code"] == 0

    def test_check_secrets_critical_missing(self):
        """Test exit code non-zero if critical missing."""
        results = check_secrets()
        
        if results["critical_missing"] > 0:
            assert results["exit_code"] != 0
            assert results["ready_for_ci"] is False

    def test_format_report_generates_output(self):
        """Test format_report generates readable output."""
        results = check_secrets()
        report = format_report(results)
        
        assert isinstance(report, str)
        assert "SECRETS READINESS CHECK" in report
        assert "CRITICAL" in report or "REQUIRED" in report

    def test_report_contains_status(self):
        """Test report contains status indicators."""
        results = check_secrets()
        report = format_report(results)
        
        assert "Present:" in report
        assert "Missing:" in report
