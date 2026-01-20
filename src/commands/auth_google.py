#!/usr/bin/env python3
"""Google OAuth authentication command.

Interactive setup for Gmail, Drive, and Calendar access.

Usage:
    python -m src.commands.auth_google               # Full setup
    python -m src.commands.auth_google --gmail       # Gmail only
    python -m src.commands.auth_google --info        # Show token info
    python -m src.commands.auth_google --revoke      # Revoke & delete token
"""
import argparse
import sys
from pathlib import Path

from src.auth.google_oauth import (
    CALENDAR_SCOPES,
    DRIVE_SCOPES,
    GMAIL_SCOPES,
    get_oauth_manager,
)
from src.logger import get_logger

logger = get_logger(__name__)


def ensure_credentials_file() -> bool:
    """Check for client_secret.json or provide setup instructions."""
    creds_file = Path("client_secret.json")

    if creds_file.exists():
        logger.info(f"✓ Found credentials file: {creds_file}")
        return True

    logger.warning("client_secret.json not found in current directory")
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  SETUP: Google OAuth Credentials                                   ║
╚════════════════════════════════════════════════════════════════════╝

You need to create a Google OAuth application first.

1. Go to Google Cloud Console:
   https://console.cloud.google.com/

2. Create a new project (or select existing):
   - Project Name: "Sales Agent Local"
   - Click CREATE

3. Enable Google APIs:
   - Search for "Gmail API" → Enable
   - Search for "Google Drive API" → Enable
   - Search for "Google Calendar API" → Enable

4. Create OAuth 2.0 Credentials:
   - Go to: APIs & Services → Credentials
   - Click: + CREATE CREDENTIALS
   - Choose: OAuth 2.0 Desktop Application
   - Name: "Sales Agent CLI"
   - Authorized redirect URIs: http://localhost:8888/

5. Download credentials:
   - Click the download icon (⬇) on your credential
   - Choose "JSON"
   - Save as: client_secret.json (in project root)

Then re-run:
   make auth-google
""")

    return False


def show_token_info() -> int:
    """Show information about current token."""
    manager = get_oauth_manager()
    info = manager.get_token_info()

    print("\n" + "=" * 70)
    print("GOOGLE OAUTH TOKEN INFO")
    print("=" * 70)

    if info["status"] == "no_token":
        print("Status: No token cached")
        print("\nRun: make auth-google")
        print("=" * 70 + "\n")
        return 1

    print(f"Status: {info['status'].upper()}")
    print(f"Client ID: {info.get('client_id', 'unknown')}")
    print(f"Expires At: {info.get('expires_at', 'unknown')}")

    if info.get("time_until_expiry"):
        hours = info["time_until_expiry"] / 3600
        print(f"Time Until Expiry: {hours:.1f} hours")

    print(f"Scopes: {len(info.get('scopes', []))} service(s)")
    for scope in info.get("scopes", []):
        service = "Gmail" if "gmail" in scope else "Drive" if "drive" in scope else "Calendar"
        access = "read/write" if "send" in scope else "read-only"
        print(f"  - {service} ({access})")

    print("=" * 70 + "\n")

    return 0 if info["status"] == "valid" else 1


def authorize_gmail() -> int:
    """Authorize Gmail access."""
    print("\n📧 Authorizing Gmail access...")
    print("A browser window will open. Log in with your Google account.")
    print("Grant permission for: Read & Send Emails\n")

    try:
        manager = get_oauth_manager()
        manager.authorize_user(GMAIL_SCOPES)
        print("✓ Gmail authorization successful\n")
        return 0
    except Exception as e:
        logger.error(f"Authorization failed: {e}")
        return 1


def authorize_drive() -> int:
    """Authorize Google Drive access."""
    print("\n💾 Authorizing Google Drive access...")
    print("A browser window will open. Log in with your Google account.")
    print("Grant permission for: Read Files\n")

    try:
        manager = get_oauth_manager()
        manager.authorize_user(DRIVE_SCOPES)
        print("✓ Google Drive authorization successful\n")
        return 0
    except Exception as e:
        logger.error(f"Authorization failed: {e}")
        return 1


def authorize_calendar() -> int:
    """Authorize Google Calendar access."""
    print("\n📅 Authorizing Google Calendar access...")
    print("A browser window will open. Log in with your Google account.")
    print("Grant permission for: Read Calendar\n")

    try:
        manager = get_oauth_manager()
        manager.authorize_user(CALENDAR_SCOPES)
        print("✓ Google Calendar authorization successful\n")
        return 0
    except Exception as e:
        logger.error(f"Authorization failed: {e}")
        return 1


def authorize_all() -> int:
    """Authorize all services."""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  GOOGLE OAUTH SETUP                                                ║
║  Grant access to: Gmail, Drive, Calendar                           ║
╚════════════════════════════════════════════════════════════════════╝

Browser will open for authentication. You may see:
  - "This app isn't verified" → Click "Advanced" → "Go to Sales Agent"
  - Permission requests → Click "Allow"

""")

    try:
        manager = get_oauth_manager()
        manager.authorize_user(GMAIL_SCOPES + DRIVE_SCOPES + CALENDAR_SCOPES)
        print("\n✓ All authorizations successful!")
        print("\n📁 Token saved to: .tokens/google_tokens.json")
        print("   (This file is in .gitignore - never commit it)")
        print("\nYou can now use:")
        print("  - Gmail API (read, send)")
        print("  - Google Drive API (read)")
        print("  - Google Calendar API (read)\n")
        return 0
    except Exception as e:
        logger.error(f"Authorization failed: {e}")
        return 1


def revoke_access() -> int:
    """Revoke tokens and delete cached file."""
    print("\n" + "=" * 70)
    print("REVOKE GOOGLE OAUTH ACCESS")
    print("=" * 70)

    response = input("Delete cached token? (yes/no): ").strip().lower()
    if response != "yes":
        print("Cancelled.")
        return 0

    try:
        manager = get_oauth_manager()
        manager.revoke()
        print("✓ Token revoked and deleted\n")
        return 0
    except Exception as e:
        logger.error(f"Revocation failed: {e}")
        return 1


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Google OAuth setup for Gmail, Drive, Calendar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full setup (all services)
  python -m src.commands.auth_google

  # Gmail only
  python -m src.commands.auth_google --gmail

  # Show current token info
  python -m src.commands.auth_google --info

  # Revoke access and delete token
  python -m src.commands.auth_google --revoke

Via Makefile:
  make auth-google           # Full setup
        """,
    )

    parser.add_argument("--gmail", action="store_true", help="Authorize Gmail only")
    parser.add_argument("--drive", action="store_true", help="Authorize Drive only")
    parser.add_argument("--calendar", action="store_true", help="Authorize Calendar only")
    parser.add_argument("--info", action="store_true", help="Show token information")
    parser.add_argument("--revoke", action="store_true", help="Revoke access and delete token")

    args = parser.parse_args()

    # Check credentials file exists
    if not any([args.info, args.revoke]):
        if not ensure_credentials_file():
            return 1

    # Handle commands
    if args.info:
        return show_token_info()

    if args.revoke:
        return revoke_access()

    if args.gmail:
        return authorize_gmail()

    if args.drive:
        return authorize_drive()

    if args.calendar:
        return authorize_calendar()

    # Default: authorize all
    return authorize_all()


if __name__ == "__main__":
    sys.exit(main())
