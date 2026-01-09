.PHONY: help test test-cov coverage coverage-html coverage-report lint format typecheck check install clean run

# Default target
help:
	@echo "Available targets:"
	@echo "  make test          - Run all tests"
	@echo "  make test-cov      - Run tests with coverage"
	@echo "  make coverage      - Run tests with coverage and show report"
	@echo "  make coverage-html - Generate HTML coverage report"
	@echo "  make lint          - Run ruff linter (check only)"
	@echo "  make format        - Format code with ruff"
	@echo "  make typecheck     - Run pyright type checker"
	@echo "  make check         - Run all checks (lint + typecheck + test-cov)"
	@echo "  make install       - Install dependencies"
	@echo "  make clean         - Clean up temporary files"
	@echo "  make run           - Run bom-bench (setup + benchmark)"

# Run tests
test:
	uv run pytest tests/ -v

# Run tests with coverage
coverage:
	uv run pytest tests/ --cov=src/bom_bench --cov-report=term-missing

# Generate HTML coverage report
coverage-html:
	uv run pytest tests/ --cov=src/bom_bench --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

# Run linter (check only)
lint:
	uv run ruff check src/ tests/

# Format code
format:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

# Type checking
typecheck:
	uv run pyright src/

# Run all checks
check: lint typecheck test-cov

# Install dependencies
install:
	uv sync
	uv run pre-commit install

# Clean temporary files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pyright -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage.* 2>/dev/null || true

# Run benchmark
benchmark:
	uv run bom-bench benchmark
