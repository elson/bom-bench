.PHONY: help test lint format typecheck check install clean run

# Default target
help:
	@echo "Available targets:"
	@echo "  make test       - Run all tests"
	@echo "  make lint       - Run ruff linter (check only)"
	@echo "  make format     - Format code with ruff"
	@echo "  make typecheck  - Run mypy type checker"
	@echo "  make check      - Run all checks (lint + typecheck + test)"
	@echo "  make install    - Install dependencies"
	@echo "  make clean      - Clean up temporary files"
	@echo "  make run        - Run bom-bench (setup command)"

# Run tests
test:
	uv run pytest tests/ -v

# Run linter (check only)
lint:
	uv run ruff check src/ tests/

# Format code
format:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

# Type checking
typecheck:
	uv run mypy src/

# Run all checks
check: lint typecheck test

# Install dependencies
install:
	uv sync
	uv run pre-commit install

# Clean temporary files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true

# Run bom-bench
run:
	uv run bom-bench setup
	uv run bom-bench benchmark
