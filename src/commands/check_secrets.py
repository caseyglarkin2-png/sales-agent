"""Secrets readiness checker CLI."""
import os
import sys
from enum import Enum

from src.logger import get_logger

logger = get_logger(__name__)


class VarStatus(Enum):
    """Status of an environment variable."""
    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"


class VarCategory(Enum):
    """Category of environment variable."""
    CRITICAL = "critical"  # System won't function
    REQUIRED = "required"  # Feature won't work
    OPTIONAL = "optional"  # Nice to have


# Define all environment variables to check
ENV_VARS = {
    # Critical secrets
    "GOOGLE_CREDENTIALS_FILE": {
        "category": VarCategory.CRITICAL,
        "description": "Path to Google OAuth credentials JSON",
        "validator": lambda v: v.endswith(".json"),
    },
    "HUBSPOT_API_KEY": {
        "category": VarCategory.CRITICAL,
        "description": "HubSpot API key for CRM operations",
        "validator": lambda v: len(v) > 10,
    },
    "DATABASE_URL": {
        "category": VarCategory.CRITICAL,
        "description": "PostgreSQL database URL",
        "validator": lambda v: v.startswith("postgresql"),
    },
    
    # Required secrets
    "OPENAI_API_KEY": {
        "category": VarCategory.REQUIRED,
        "description": "OpenAI API key for LLM features",
        "validator": lambda v: len(v) > 5,
    },
    "EXPECTED_HUBSPOT_FORM_ID": {
        "category": VarCategory.REQUIRED,
        "description": "HubSpot form ID to accept",
        "validator": lambda v: len(v) > 5,
    },
    
    # Optional secrets
    "CHARLIE_PESTI_FOLDER_ID": {
        "category": VarCategory.OPTIONAL,
        "description": "Charlie Pesti Drive folder ID for asset hunting",
        "validator": lambda v: len(v) > 5,
    },
    "SENTRY_DSN": {
        "category": VarCategory.OPTIONAL,
        "description": "Sentry error tracking DSN",
        "validator": lambda v: v.startswith("https://"),
    },
}


def validate_var(var_name: str) -> tuple[VarStatus, str]:
    """Validate a single environment variable."""
    if var_name not in ENV_VARS:
        return VarStatus.MISSING, f"Unknown variable: {var_name}"

    var_config = ENV_VARS[var_name]
    value = os.environ.get(var_name)

    if not value:
        return VarStatus.MISSING, f"Not set"

    try:
        validator = var_config.get("validator")
        if validator and not validator(value):
            return VarStatus.INVALID, f"Invalid format: {value[:20]}..."
    except Exception as e:
        return VarStatus.INVALID, f"Validation error: {str(e)}"

    return VarStatus.PRESENT, f"Valid"


def check_secrets(strict: bool = False) -> dict:
    """Check all secrets and return status."""
    results = {
        "timestamp": os.environ.get("TIMESTAMP", ""),
        "total": len(ENV_VARS),
        "present": 0,
        "missing": 0,
        "invalid": 0,
        "critical_missing": 0,
        "details": {},
    }

    for var_name, var_config in ENV_VARS.items():
        status, message = validate_var(var_name)
        category = var_config["category"]

        results["details"][var_name] = {
            "status": status.value,
            "category": category.value,
            "description": var_config["description"],
            "message": message,
        }

        if status == VarStatus.PRESENT:
            results["present"] += 1
        elif status == VarStatus.MISSING:
            results["missing"] += 1
            if category == VarCategory.CRITICAL:
                results["critical_missing"] += 1
        elif status == VarStatus.INVALID:
            results["invalid"] += 1

    # Determine exit code
    results["exit_code"] = 0
    results["ready_for_ci"] = True

    if results["critical_missing"] > 0:
        results["exit_code"] = 1
        results["ready_for_ci"] = False

    if strict and results["missing"] > 0:
        results["exit_code"] = 1
        results["ready_for_ci"] = False

    return results


def format_report(results: dict) -> str:
    """Format results as human-readable report."""
    lines = []
    lines.append("╔════════════════════════════════════════════════════════╗")
    lines.append("║           SECRETS READINESS CHECK                     ║")
    lines.append("╚════════════════════════════════════════════════════════╝")
    lines.append("")

    # Summary
    lines.append(f"Present:   {results['present']}/{results['total']}")
    lines.append(f"Missing:   {results['missing']}/{results['total']}")
    lines.append(f"Invalid:   {results['invalid']}/{results['total']}")
    lines.append("")

    if results["critical_missing"] > 0:
        lines.append(f"⚠️  CRITICAL MISSING: {results['critical_missing']}")
        lines.append("")

    # Details by category
    for category in [VarCategory.CRITICAL, VarCategory.REQUIRED, VarCategory.OPTIONAL]:
        lines.append(f"## {category.value.upper()}")
        for var_name, details in results["details"].items():
            if ENV_VARS[var_name]["category"] == category:
                status = details["status"]
                symbol = "✓" if status == "present" else "✗" if status == "missing" else "⚠"
                lines.append(f"  {symbol} {var_name}: {details['message']}")
        lines.append("")

    # Status
    if results["exit_code"] == 0:
        lines.append("✅ All critical secrets are present!")
    else:
        lines.append("❌ Missing critical secrets. Cannot proceed.")

    lines.append("")
    return "\n".join(lines)


async def main(strict: bool = False, json_output: bool = False) -> int:
    """Main entry point."""
    results = check_secrets(strict=strict)

    if json_output:
        import json
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results))

    return results["exit_code"]


if __name__ == "__main__":
    import asyncio

    strict = "--strict" in sys.argv
    json_output = "--json" in sys.argv

    exit_code = asyncio.run(main(strict=strict, json_output=json_output))
    sys.exit(exit_code)
