"""CaseyOS CLI - Local deployment and management.

Sprint 18: Local Deployment

Usage:
    python -m src [command]
    
Commands:
    run         Start the full stack (API + Celery worker + beat)
    api         Start only the API server
    worker      Start only Celery worker
    beat        Start only Celery beat scheduler
    migrate     Run database migrations
    shell       Open Python shell with app context
    health      Check system health
    docker-up   Start Docker Compose stack
    docker-down Stop Docker Compose stack
    docker-logs Tail Docker Compose logs
"""
import sys
import os
import subprocess
import asyncio
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_banner():
    """Print CaseyOS banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║      ██████╗ █████╗ ███████╗███████╗██╗   ██╗ ██████╗ ███████╗║
║     ██╔════╝██╔══██╗██╔════╝██╔════╝╚██╗ ██╔╝██╔═══██╗██╔════╝║
║     ██║     ███████║███████╗█████╗   ╚████╔╝ ██║   ██║███████╗║
║     ██║     ██╔══██║╚════██║██╔══╝    ╚██╔╝  ██║   ██║╚════██║║
║     ╚██████╗██║  ██║███████║███████╗   ██║   ╚██████╔╝███████║║
║      ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝    ╚═════╝ ╚══════╝║
║                                                               ║
║           GTM Command Center - Your Digital Chief of Staff    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_docker():
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_env_file():
    """Check if .env.local exists."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.local")
    return os.path.exists(env_path)


def cmd_run():
    """Start the full local stack."""
    print_banner()
    print("Starting CaseyOS full stack...")
    
    if not check_docker():
        print("❌ Docker not found. Please install Docker Desktop.")
        sys.exit(1)
    
    if not check_env_file():
        print("❌ .env.local not found. Copy .env.local.template to .env.local and configure.")
        sys.exit(1)
    
    print("✅ Docker available")
    print("✅ Environment configured")
    print("\n🚀 Starting services...")
    
    subprocess.run(["docker", "compose", "up", "--build", "-d"])
    print("\n✅ Stack started! Access at http://localhost:8000")
    print("\nUseful commands:")
    print("  python -m src docker-logs  # View logs")
    print("  python -m src health       # Check health")
    print("  python -m src docker-down  # Stop stack")


def cmd_api():
    """Start only the API server (for development)."""
    print_banner()
    print("Starting CaseyOS API server...")
    os.system("uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload")


def cmd_worker():
    """Start Celery worker."""
    print("Starting Celery worker...")
    os.system("celery -A src.celery_app worker --loglevel=info")


def cmd_beat():
    """Start Celery beat scheduler."""
    print("Starting Celery beat scheduler...")
    os.system("celery -A src.celery_app beat --loglevel=info")


def cmd_migrate():
    """Run database migrations."""
    print("Running database migrations...")
    os.system("alembic -c infra/alembic.ini upgrade head")
    print("✅ Migrations complete")


def cmd_shell():
    """Open interactive Python shell with app context."""
    print("Opening CaseyOS shell...")
    import code
    
    # Import common modules
    from src.main import app
    from src.config import get_settings
    from src.agents.jarvis import get_jarvis
    from src.db import async_session
    
    settings = get_settings()
    jarvis = get_jarvis()
    
    banner = """
CaseyOS Interactive Shell
Available objects:
  - app: FastAPI application
  - settings: Application settings
  - jarvis: Jarvis agent instance
  - async_session: Database session factory

Example:
  >>> import asyncio
  >>> asyncio.run(jarvis.ask("What can you do?"))
"""
    
    local_vars = {
        "app": app,
        "settings": settings,
        "jarvis": jarvis,
        "async_session": async_session,
    }
    
    code.interact(banner=banner, local=local_vars)


def cmd_health():
    """Check system health."""
    print("Checking CaseyOS health...\n")
    
    import httpx
    
    checks = [
        ("API", "http://localhost:8000/health"),
        ("Jarvis", "http://localhost:8000/api/jarvis/health"),
    ]
    
    for name, url in checks:
        try:
            response = httpx.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: healthy")
            else:
                print(f"⚠️  {name}: status {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: unreachable ({e})")
    
    print()


def cmd_docker_up():
    """Start Docker Compose stack."""
    print_banner()
    subprocess.run(["docker", "compose", "up", "--build", "-d"])


def cmd_docker_down():
    """Stop Docker Compose stack."""
    print("Stopping CaseyOS stack...")
    subprocess.run(["docker", "compose", "down"])


def cmd_docker_logs():
    """Tail Docker Compose logs."""
    subprocess.run(["docker", "compose", "logs", "-f", "--tail=100"])


def cmd_help():
    """Show help message."""
    print(__doc__)


COMMANDS = {
    "run": cmd_run,
    "api": cmd_api,
    "worker": cmd_worker,
    "beat": cmd_beat,
    "migrate": cmd_migrate,
    "shell": cmd_shell,
    "health": cmd_health,
    "docker-up": cmd_docker_up,
    "docker-down": cmd_docker_down,
    "docker-logs": cmd_docker_logs,
    "help": cmd_help,
    "--help": cmd_help,
    "-h": cmd_help,
}


def main():
    """CLI entrypoint."""
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command in COMMANDS:
        COMMANDS[command]()
    else:
        print(f"Unknown command: {command}")
        cmd_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
