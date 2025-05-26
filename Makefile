# Makefile for Foe Be Gone - Wildlife Detection & Deterrent System

.PHONY: help setup clean start test lint format install-playwright dev

# Default target
help: ## Show this help message
	@echo "Foe Be Gone - Development Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial project setup (install dependencies, setup Playwright)
	@echo "🚀 Setting up Foe Be Gone development environment..."
	@echo "📦 Installing Python dependencies..."
	uv sync
	@echo "🎭 Installing Playwright browsers..."
	uv run playwright install
	@echo "✅ Setup complete! Run 'make start' to start the development server"

clean: ## Clean up cache files, logs, and temporary files
	@echo "🧹 Cleaning up project files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.log" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ 2>/dev/null || true
	@echo "✅ Cleanup complete!"

start: ## Start the development server with hot reload
	@echo "🌟 Starting Foe Be Gone development server..."
	@echo "🔗 Server will be available at: http://localhost:8000"
	@echo "📁 Templates and static files will auto-reload"
	@echo "⏹️  Press Ctrl+C to stop"
	uv run uvicorn app.main:app --reload --reload-include='*.html' --reload-include='*.jinja' --host 0.0.0.0 --port 8000

dev: start ## Alias for start command

test: ## Run all tests
	@echo "🧪 Running tests..."
	uv run pytest tests/ -v

test-ui: ## Run tests with Playwright UI mode
	@echo "🎭 Running Playwright tests with UI..."
	uv run pytest --browser=chromium --headed tests/

test-all: ## Run tests on all browsers
	@echo "🌐 Running tests on all browsers..."
	uv run pytest --browser=all tests/

lint: ## Run code linting (when we add it later)
	@echo "🔍 Running linters..."
	@echo "Note: Linting tools not yet configured"

format: ## Format code (when we add it later)
	@echo "✨ Formatting code..."
	@echo "Note: Code formatting tools not yet configured"

install-playwright: ## Install/update Playwright browsers
	@echo "🎭 Installing/updating Playwright browsers..."
	uv run playwright install

db-init: ## Initialize database (when we add Alembic)
	@echo "🗄️  Initializing database..."
	@echo "Note: Database migrations not yet configured"

db-migrate: ## Run database migrations (when we add Alembic)
	@echo "🗄️  Running database migrations..."
	@echo "Note: Database migrations not yet configured"

check: test ## Run all checks (tests, linting, etc.)
	@echo "✅ All checks completed!"

install: setup ## Alias for setup command

build: ## Build the application for production
	@echo "🏗️  Building application..."
	@echo "Note: Production build not yet configured"

health: ## Check if the development server is running
	@echo "🏥 Checking server health..."
	@curl -f http://localhost:8000/health || echo "❌ Server is not running. Run 'make start' first."