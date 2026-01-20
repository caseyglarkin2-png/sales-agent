#!/usr/bin/env python3
"""Secrets readiness checker CLI.

Validates that all required environment variables are set.
Fails with exit code 1 if any critical secrets are missing.

Usage:
    python -m src.cli.secrets_check              # Check all required vars
    python -m src.cli.secrets_check --strict     # Include optional vars
    python -m src.cli.secrets_check --json       # Output as JSON
"""
import json
import os
import sys
from enum import Enum
from typing import Any


class VarStatus(Enum):
    """Status of an environment variable."""

    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"


class VarCategory(Enum):
    """Category of environment variable."""

    CRITICAL = "critical"  # Fail if missing
    REQUIRED = "required"  # Fail if missing (can be relaxed in dev)
    OPTIONAL = "optional"  # Warn if missing


# Define all required environment variables
ENV_VARS = {
    # Critical: Must be present
    "DATABASE_URL": {
        "category": VarCategory.CRITICAL,
        "description": "PostgreSQL connection string",
        "example": "postgresql+asyncpg://user:pass@localhost:5432/sales_agent",
    },
    "REDIS_URL": {
        "category": VarCategory.CRITICAL,
        "description": "Redis connection string",
        "example": "redis://localhost:6379/0",
    },
    "API_HOST": {
        "category": VarCategory.CRITICAL,
        "description": "FastAPI host",
        "example": "0.0.0.0",
    },
    "API_PORT": {
        "category": VarCategory.CRITICAL,
        "description": "FastAPI port",
        "example": "8000",
    },
    # Required: Needed for full functionality
    "GOOGLE_CLIENT_ID": {
        "category": VarCategory.REQUIRED,
        "description": "Google OAuth 2.0 Client ID",
        "example": "xxx-yyy.apps.googleusercontent.com",
    },
    "GOOGLE_CLIENT_SECRET": {
        "category": VarCategory.REQUIRED,
        "description": "Google OAuth 2.0 Client Secret",
        "example": "GOCSPX-xxxxxxxxxxxxx",
    },
    "GOOGLE_REDIRECT_URI": {
        "category": VarCategory.REQUIRED,
        "description": "Google OAuth 2.0 Redirect URI",
        "example": "http://localhost:8000/auth/google/callback",
    },
    "HUBSPOT_API_KEY": {
        "category": VarCategory.REQUIRED,
        "description": "HubSpot API key",
        "example": "pat-na1-xxxxxxxxxxxxxxxxxxxxx",
    },
    "OPENAI_API_KEY": {
        "category": VarCategory.REQUIRED,
        "description": "OpenAI API key",
        "example": "sk-xxxxxxxxxxxxxxxxxxxxx",
    },
    # Optional: Can be omitted in development
    "HUBSPOT_APP_ID": {
        "category": VarCategory.OPTIONAL,
        "description": "HubSpot app ID (for private app)",
        "example": "123456",
    },
    "OPENAI_MODEL": {
        "category": VarCategory.OPTIONAL,
        "description": "OpenAI model name",
        "example": "gpt-4-turbo-preview",
    },
    "FEATURE_COLD_START_DEMO": {
        "category": VarCategory.OPTIONAL,
        "description": "Enable demo endpoints",
        "example": "true",
    },
    "OPERATOR_MODE_ENABLED": {
        "category": VarCategory.OPTIONAL,
        "description": "Enable operator mode (draft approval)",
        "example": "true",
    },
}


def validate_var(name: str, value: str | None, config: dict[str, Any]) -> tuple[VarStatus, str]:
    """Validate a single environment variable.

    Returns:
        (status, message)
    """
    if value is None:
        return VarStatus.MISSING, f"Not set"

    if not value.strip():
        return VarStatus.INVALID, f"Set but empty"

    if name == "API_PORT":
        try:
            port = int(value)
            if not (0 < port < 65536):
                return VarStatus.INVALID, f"Port {port} out of range (0-65536)"
        except ValueError:
            return VarStatus.INVALID, f"Port must be numeric, got: {value}"

    if name in ["FEATURE_COLD_START_DEMO", "FEATURE_VALIDATION_AGENT", "OPERATOR_MODE_ENABLED"]:
        if value.lower() not in ["true", "false"]:
            return VarStatus.INVALID, f"Must be 'true' or 'false', got: {value}"

    return VarStatus.PRESENT, "OK"


def check_secrets(strict: bool = False, json_output: bool = False) -> dict[str, Any]:
    """Check all required secrets.

    Args:
        strict: Include optional vars in check
        json_output: Output as JSON

    Returns:
        Report dict with status, results, and exit code
    """
    report = {
        "timestamp": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
        "strict_mode": strict,
        "results": {},
        "summary": {"present": 0, "missing": 0, "invalid": 0},
        "critical_missing": [],
        "required_missing": [],
        "optional_missing": [],
        "invalid": [],
    }

    for var_name, config in ENV_VARS.items():
        # Skip optional vars unless --strict
        if config["category"] == VarCategory.OPTIONAL and not strict:
            continue

        value = os.environ.get(var_name)
        status, message = validate_var(var_name, value, config)

        report["results"][var_name] = {
            "status": status.value,
            "message": message,
            "category": config["category"].value,
            "description": config["description"],
        }

        if status == VarStatus.PRESENT:
            report["summary"]["present"] += 1
        elif status == VarStatus.MISSING:
            report["summary"]["missing"] += 1
            if config["category"] == VarCategory.CRITICAL:
                report["critical_missing"].append(var_name)
            elif config["category"] == VarCategory.REQUIRED:
                report["required_missing"].append(var_name)
            elif config["category"] == VarCategory.OPTIONAL:
                report["optional_missing"].append(var_name)
        else:
            report["summary"]["invalid"] += 1
            report["invalid"].append(var_name)

    # Determine exit code
    exit_code = 0
    if report["critical_missing"]:
        exit_code = 1
    elif report["required_missing"] and not os.environ.get("DEV_MODE"):
        exit_code = 1
    elif report["invalid"]:
        exit_code = 1

    report["exit_code"] = exit_code
    report["status"] = "pass" if exit_code == 0 else "fail"

    return report


def format_report(report: dict[str, Any]) -> str:
    """Format report as human-readable text."""
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append("SECRETS READINESS CHECK")
    lines.append("=" * 70)
    lines.append(f"Status: {report['status'].upper()}")
    lines.append(f"Timestamp: {report['timestamp']}")
    lines.append("")

    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(
        f"  ✓ Present: {report['summary']['present']} | "
        f"✗ Missing: {report['summary']['missing']} | "
        f"⚠ Invalid: {report['summary']['invalid']}"
    )
    lines.append("")

    # Issues
    if report["critical_missing"]:
        lines.append("CRITICAL (Must be set):")
        for var in report["critical_missing"]:
            lines.append(f"  ✗ {var}")
        lines.append("")

    if report["required_missing"]:
        lines.append("REQUIRED (Should be set):")
        for var in report["required_missing"]:
            lines.append(f"  ✗ {var}")
        lines.append("")

    if report["invalid"]:
        lines.append("INVALID:")
        for var in report["invalid"]:
            result = report["results"][var]
            lines.append(f"  ⚠ {var}: {result['message']}")
        lines.append("")

    if report["optional_missing"] and os.environ.get("DEV_MODE"):
        lines.append("OPTIONAL (Not set):")
        for var in report["optional_missing"]:
            lines.append(f"  ○ {var}")
        lines.append("")

    # Details
    if report["results"]:
        lines.append("DETAILS")
        lines.append("-" * 70)
        for var_name in sorted(report["results"].keys()):
            result = report["results"][var_name]
            status_symbol = (
                "✓" if result["status"] == "present" else "✗" if result["status"] == "missing" else "⚠"
            )
            lines.append(
                f"  {status_symbol} {var_name:<30} [{result['category']:<8}] {result['message']}"
            )
            lines.append(f"     {result['description']}")

    lines.append("")
    lines.append("=" * 70)

    if report["exit_code"] != 0:
        lines.append("❌ FAILED - See critical issues above")
        if os.environ.get("CI"):
            lines.append("This check is enforced in CI. Set missing variables before merging.")
    else:
        lines.append("✅ PASSED - All required secrets are set")

    lines.append("=" * 70 + "\n")

    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check that all required environment variables are set.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check critical vars only (default)
  python -m src.cli.secrets_check

  # Check all vars including optional
  python -m src.cli.secrets_check --strict

  # Output as JSON for CI/CD
  python -m src.cli.secrets_check --json

  # Run in development mode (relaxes 'required' vars)
  DEV_MODE=1 python -m src.cli.secrets_check

  # Use in CI pipeline
  python -m src.cli.secrets_check && echo "Ready to deploy"
        """,
    )

    parser.add_argument("--strict", action="store_true", help="Check optional vars too")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    report = check_secrets(strict=args.strict, json_output=args.json)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report))

    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
