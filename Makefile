.PHONY: help install dev test lint format clean docker-build docker-up docker-down secrets-check auth-google smoke-formlead local-up local-down local-logs local-shell

help:
	@echo "Sales Agent Makefile"
	@echo ""
	@echo "Setup & Development:"
	@echo "  make install          - Install dependencies (poetry)"
	@echo "  make dev              - Install dev dependencies"
	@echo "  make secrets-check    - Validate required environment variables"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     - Build Docker image"
	@echo "  make docker-up        - Start Docker Compose stack"
	@echo "  make docker-down      - Stop Docker Compose stack"
	@echo "  make docker-logs      - View Docker logs"
	@echo ""
	@echo "Local Development (Sprint 18):"
	@echo "  make local-up         - Start full local stack (API + Celery)"
	@echo "  make local-down       - Stop local stack"
	@echo "  make local-logs       - Tail local stack logs"
	@echo "  make local-shell      - Open CaseyOS Python shell"
	@echo "  make local-health     - Check local stack health"
	@echo ""
	@echo "Authentication & Integration:"
	@echo "  make auth-google      - Authenticate with Google (Gmail, Drive, Calendar)"
	@echo ""
	@echo "Testing & Validation:"
	@echo "  make test             - Run all tests (pytest)"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-smoke       - Run smoke tests"
	@echo "  make smoke-formlead   - E2E smoke test (form → draft → task)"
	@echo "  make coverage         - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             - Lint code (ruff + pyright)"
	@echo "  make format           - Format code (ruff + black)"
	@echo "  make pre-commit       - Run pre-commit hooks"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove build artifacts"
	@echo "  make clean-all        - Clean + remove venv & .pytest_cache"

install:
	@echo "Installing dependencies with poetry..."
	poetry install

dev:
	@echo "Installing dev dependencies..."
	poetry install --with dev

secrets-check:
	@echo "Checking secrets readiness..."
	python -m src.commands.check_secrets

check-secrets: secrets-check
	@true

check-secrets-strict:
	@echo "Checking all secrets (including optional)..."
	python -m src.commands.check_secrets --strict

check-secrets-json:
	@echo "Checking secrets (JSON output)..."
	python -m src.commands.check_secrets --json

smoke-formlead-mock:
	@echo "🚀 Running formlead E2E test with MOCKED connectors (DRAFT_ONLY)..."
	python -m src.commands.smoke_formlead_formlead --mock

smoke-formlead-live:
	@echo "🚀 Running formlead E2E test with LIVE connectors (DRAFT_ONLY)..."
	python -m src.commands.smoke_formlead_formlead --live

smoke-formlead: smoke-formlead-mock
	@true

docker-build:
	@echo "Building Docker image..."
	docker build -t sales-agent:latest .

docker-up:
	@echo "Starting Docker Compose stack..."
	docker compose up --wait

docker-down:
	@echo "Stopping Docker Compose stack..."
	docker compose down

docker-logs:
	@echo "Viewing Docker logs..."
	docker compose logs -f

# ============================================================================
# Local Development (Sprint 18)
# ============================================================================

local-up:
	@echo "🚀 Starting CaseyOS local stack..."
	@if [ ! -f .env.local ]; then \
		echo "❌ .env.local not found. Copying template..."; \
		cp .env.local.template .env.local; \
		echo "📝 Please edit .env.local with your API keys, then run 'make local-up' again."; \
		exit 1; \
	fi
	docker compose up --build -d
	@echo "✅ Stack started! Access at http://localhost:8000"
	@echo "   View logs: make local-logs"
	@echo "   Check health: make local-health"

local-down:
	@echo "Stopping CaseyOS local stack..."
	docker compose down

local-logs:
	@echo "Tailing CaseyOS logs (Ctrl+C to exit)..."
	docker compose logs -f --tail=100

local-shell:
	@echo "Opening CaseyOS Python shell..."
	python -m src shell

local-health:
	@echo "Checking CaseyOS health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ API not responding"
	@curl -s http://localhost:8000/api/jarvis/health | python -m json.tool || echo "⚠️  Jarvis not responding"

local-worker:
	@echo "Starting Celery worker..."
	celery -A src.celery_app worker --loglevel=info

local-beat:
	@echo "Starting Celery beat..."
	celery -A src.celery_app beat --loglevel=info

# ============================================================================
# Tests
# ============================================================================

test:
	@echo "Running all tests..."
	pytest tests/ -v --tb=short

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v --tb=short

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -v --tb=short

test-smoke:
	@echo "Running smoke tests..."
	pytest tests/smoke/ -v --tb=short -s

coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:
	@echo "Linting code..."
	ruff check src tests
	pyright src tests

format:
	@echo "Formatting code..."
	ruff format src tests
	ruff check --fix src tests

pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

auth-google:
	@echo "Authenticating with Google..."
	@python -m src.commands.auth_google

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ .eggs/ *.egg-info/
	rm -rf .pytest_cache/ .ruff_cache/ .pytype/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-all: clean
	@echo "Cleaning all (including venv)..."
	rm -rf .venv/

# Timeline guard: Fail if docs contain timeline language
timeline-guard:
	@echo "Checking for timeline language in docs..."
	python -m src.commands.timeline_guard docs/GO_LIVE_TONIGHT.md

timeline-guard-all:
	@echo "Checking all docs for timeline language..."
	python -m src.commands.timeline_guard --all-docs

# Go-live validation sequence
go-live-check: check-secrets smoke-formlead timeline-guard
	@echo "✓ Go-live validation complete"

.DEFAULT_GOAL := help
