"""Emergency Rollback Script.

Quickly rollback to previous stable version.
"""

#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Emergency rollback script for sales-agent.

OPTIONS:
    --to-version VERSION    Rollback to specific version (e.g., v1.2.3)
    --dry-run               Show what would happen without doing it
    --help                  Show this help

EXAMPLES:
    # Rollback to previous version
    $0

    # Rollback to specific version
    $0 --to-version v1.2.3

    # Dry run
    $0 --dry-run

EOF
    exit 1
}

rollback() {
    local TARGET_VERSION=$1
    local DRY_RUN=$2
    
    echo "🔄 Starting rollback to ${TARGET_VERSION}..."
    
    if [ "$DRY_RUN" = "true" ]; then
        echo "DRY RUN: Would rollback to ${TARGET_VERSION}"
        echo "  1. Pull Docker image: sales-agent:${TARGET_VERSION}"
        echo "  2. Stop current containers"
        echo "  3. Start containers with previous image"
        echo "  4. Verify health checks"
        return 0
    fi
    
    # Pull previous image
    echo "📦 Pulling Docker image: sales-agent:${TARGET_VERSION}"
    docker pull "sales-agent:${TARGET_VERSION}"
    
    # Stop current containers
    echo "🛑 Stopping current containers..."
    docker-compose down
    
    # Start with previous version
    echo "🚀 Starting containers with version ${TARGET_VERSION}..."
    docker-compose up -d --force-recreate
    
    # Wait for health check
    echo "⏳ Waiting for health check..."
    sleep 5
    
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Rollback complete! Service is healthy."
            exit 0
        fi
        echo "Waiting for service... ($i/30)"
        sleep 2
    done
    
    echo "❌ Health check failed after rollback"
    exit 1
}

# Parse arguments
TO_VERSION=""
DRY_RUN=false

while [ $# -gt 0 ]; do
    case "$1" in
        --to-version)
            TO_VERSION=$2
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Get previous version if not specified
if [ -z "$TO_VERSION" ]; then
    TO_VERSION=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "v1.0.0")
    echo "No version specified, using previous tag: $TO_VERSION"
fi

rollback "$TO_VERSION" "$DRY_RUN"
