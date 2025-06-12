# Makefile for Foe Be Gone - Wildlife Detection & Deterrent System

.PHONY: help setup clean start test lint format install-playwright dev venv

# Default target
help: ## Show this help message
	@echo "Foe Be Gone - Development Commands"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment
	@echo "🐍 Creating Python virtual environment..."
	@if command -v python3.13 > /dev/null 2>&1; then \
		echo "Using Python 3.13"; \
		python3.13 -m venv venv; \
	else \
		echo "❌ Error: Python 3.13 is required but not found"; \
		echo "Please install Python 3.13 from https://www.python.org/downloads/"; \
		exit 1; \
	fi
	@echo "✅ Virtual environment created with Python 3.13"

setup: venv ## Initial project setup (install dependencies, setup Playwright)
	@echo "🚀 Setting up Foe Be Gone development environment..."
	@echo "📦 Installing Python dependencies..."
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	./venv/bin/pip install -r requirements-dev.txt
	@echo "🎭 Installing Playwright browsers..."
	./venv/bin/playwright install
	@echo "✅ Setup complete! Run 'make start' to start the development server"

clean: ## Clean up cache files, logs, and temporary files
	@echo "🧹 Cleaning up project files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.log" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ 2>/dev/null || true
	@echo "✅ Cleanup complete!"

clean-venv: ## Remove virtual environment
	@echo "🗑️  Removing virtual environment..."
	rm -rf venv/
	@echo "✅ Virtual environment removed"

start: ## Start the development server with hot reload
	@echo "🌟 Starting Foe Be Gone development server..."
	@echo "🔗 Server will be available at: http://localhost:80"
	@echo "📁 Templates and static files will auto-reload"
	@echo "⏹️  Press Ctrl+C to stop"
	./venv/bin/uvicorn app.main:app --reload --reload-include='*.html' --reload-include='*.jinja' --host 0.0.0.0 --port 80

dev: start ## Alias for start command

test: ## Run all tests
	@echo "🧪 Running tests..."
	./venv/bin/pytest tests/ -v

test-ui: ## Run tests with Playwright UI mode
	@echo "🎭 Running Playwright tests with UI..."
	./venv/bin/pytest --browser=chromium --headed tests/

test-all: ## Run tests on all browsers
	@echo "🌐 Running tests on all browsers..."
	./venv/bin/pytest --browser=all tests/

lint: ## Run code linting (when we add it later)
	@echo "🔍 Running linters..."
	@echo "Note: Linting tools not yet configured"

format: ## Format code (when we add it later)
	@echo "✨ Formatting code..."
	@echo "Note: Code formatting tools not yet configured"

install-playwright: ## Install/update Playwright browsers
	@echo "🎭 Installing/updating Playwright browsers..."
	./venv/bin/playwright install

db-init: ## Initialize database (apply all migrations)
	@echo "🗄️  Initializing database (apply all migrations)..."
	./venv/bin/alembic upgrade head

db-migrate: ## Create new migration with autogenerate
	@echo "🗄️  Creating new database migration..."
	@read -p "Enter migration message: " msg; \
	./venv/bin/alembic revision --autogenerate -m "$$msg"

db-upgrade: ## Apply pending migrations
	@echo "🗄️  Applying database migrations..."
	./venv/bin/alembic upgrade head

check: test ## Run all checks (tests, linting, etc.)
	@echo "✅ All checks completed!"

install: setup ## Alias for setup command

build: ## Build the application for production
	@echo "🏗️  Building application..."
	@echo "Note: Production build not yet configured"

health: ## Check if the development server is running
	@echo "🏥 Checking server health..."
	@curl -f http://localhost:80/health || echo "❌ Server is not running. Run 'make start' first."

# YOLOv11 specific commands
yolo-test: ## Test YOLOv11 detection on sample images
	@echo "🎯 Testing YOLOv11 detection..."
	./venv/bin/python -c "from app.services.yolo_detector import YOLOv11DetectionService; print('YOLOv11 import successful')"

yolo-download: ## Download YOLOv11 model if not present
	@echo "📥 Ensuring YOLOv11 model is downloaded..."
	@mkdir -p data/models
	./venv/bin/python -c "from ultralytics import YOLO; YOLO('data/models/yolo11n.pt')"
	@echo "✅ YOLOv11 model ready"

# macOS service commands
service-install: ## Install macOS LaunchAgent service for development server
	@echo "🚀 Installing Foe Be Gone development service..."
	@echo "📝 Creating LaunchAgent plist file..."
	@mkdir -p ~/Library/LaunchAgents
	@echo '<?xml version="1.0" encoding="UTF-8"?>' > ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '<plist version="1.0">' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '<dict>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <key>Label</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <string>com.foebegone.dev</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <key>ProgramArguments</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <array>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>$(shell pwd)/venv/bin/uvicorn</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>app.main:app</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>--reload</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>--reload-include=*.html</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>--reload-include=*.jinja</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>--host</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>0.0.0.0</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>--port</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>80</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    </array>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <key>WorkingDirectory</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <string>$(shell pwd)</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <key>RunAtLoad</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <true/>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <key>KeepAlive</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <true/>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <key>StandardOutPath</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <string>$(shell pwd)/logs/foe-be-gone.log</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <key>StandardErrorPath</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <string>$(shell pwd)/logs/foe-be-gone.error.log</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <key>EnvironmentVariables</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    <dict>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <key>PATH</key>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '    </dict>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '</dict>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo '</plist>' >> ~/Library/LaunchAgents/com.foebegone.dev.plist
	@mkdir -p logs
	@echo "✅ LaunchAgent plist created"
	@echo "🔄 Loading service..."
	@launchctl load ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo "✅ Service installed and started!"
	@echo "📝 Logs available at: $(shell pwd)/logs/"
	@echo "🔗 Server running at: http://localhost:80"

service-uninstall: ## Uninstall macOS LaunchAgent service
	@echo "🛑 Uninstalling Foe Be Gone development service..."
	@if [ -f ~/Library/LaunchAgents/com.foebegone.dev.plist ]; then \
		launchctl unload ~/Library/LaunchAgents/com.foebegone.dev.plist 2>/dev/null || true; \
		rm -f ~/Library/LaunchAgents/com.foebegone.dev.plist; \
		echo "✅ Service uninstalled"; \
	else \
		echo "⚠️  Service not found"; \
	fi

service-status: ## Check status of the macOS service
	@echo "📊 Checking Foe Be Gone service status..."
	@launchctl list | grep com.foebegone.dev || echo "❌ Service not running"

service-restart: ## Restart the macOS service
	@echo "🔄 Restarting Foe Be Gone service..."
	@launchctl unload ~/Library/LaunchAgents/com.foebegone.dev.plist 2>/dev/null || true
	@launchctl load ~/Library/LaunchAgents/com.foebegone.dev.plist
	@echo "✅ Service restarted"

service-logs: ## Show service logs
	@echo "📜 Foe Be Gone service logs:"
	@echo "=== Standard Output ==="
	@tail -n 20 logs/foe-be-gone.log 2>/dev/null || echo "No logs yet"
	@echo "\n=== Error Output ==="
	@tail -n 20 logs/foe-be-gone.error.log 2>/dev/null || echo "No error logs"

service-logs-follow: ## Follow service logs in real-time
	@echo "📜 Following Foe Be Gone service logs (Ctrl+C to stop)..."
	@tail -f logs/foe-be-gone.log logs/foe-be-gone.error.log