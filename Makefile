.PHONY: install dev-stdio dev-http test lint format clean

# =============================================================================
# Development
# =============================================================================

# Install dependencies
install:
	pip install -e ".[dev]"

# Run in stdio mode (for Cursor connection via command)
# Add to mcp.json: "command": "python", "args": ["-m", "src.server", "--stdio"]
dev-stdio:
	python -m src.server --stdio

# Run in HTTP mode (emulates cloud deployment)
# Add to mcp.json: "url": "http://localhost:8000/mcp/dev-session"
dev-http:
	python -m src.server_http

# Run HTTP on custom port
dev-http-port:
	MCP_PORT=9000 python -m src.server_http

# =============================================================================
# Testing
# =============================================================================

# Run tests
test:
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	python -m pytest tests/ -v --cov=src --cov-report=term-missing

# =============================================================================
# Code Quality
# =============================================================================

# Lint code
lint:
	ruff check src/ tests/

# Format code
format:
	ruff format src/ tests/

# =============================================================================
# Deployment
# =============================================================================

# Deploy to Fly.io
deploy:
	fly deploy

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
