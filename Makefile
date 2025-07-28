# Makefile for agentic-spec project
# Provides automated code quality workflows and development tasks

.PHONY: help install install-dev format lint check test test-coverage clean build docs spec-commit spec-publish spec-publish-all spec-complete audit-models

# Default target
help:
	@echo "agentic-spec Development Makefile"
	@echo "================================="
	@echo ""
	@echo "Available commands:"
	@echo "  install      Install package in development mode"
	@echo "  install-dev  Install package with development dependencies"
	@echo "  format       Format code using ruff"
	@echo "  lint         Run linting checks using ruff"
	@echo "  check        Run both formatting and linting checks"
	@echo "  test         Run tests using pytest"
	@echo "  test-cov     Run tests with coverage reporting"
	@echo "  test-fast    Run tests excluding slow tests"
	@echo "  clean        Clean build artifacts and cache files"
	@echo "  build        Build distribution packages"
	@echo "  docs         Generate documentation (placeholder)"
	@echo "  ci           Run full CI pipeline (format, lint, test)"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  format-check Check if code needs formatting"
	@echo "  lint-fix     Auto-fix linting issues where possible"
	@echo "  quality      Run comprehensive code quality checks"
	@echo "  audit-models Audit data model consistency (dataclass vs Pydantic)"
	@echo ""
	@echo "Specification Workflow Commands:"
	@echo "  spec-commit     Commit specifications and implementation changes"
	@echo "  spec-publish    Publish new draft specifications as implemented"
	@echo "  spec-publish-all Publish ALL specifications in specs/ directory as implemented"
	@echo "  spec-complete   Complete specification workflow (commit + publish)"

# Installation commands
install:
	pip install -e .

install-dev:
	pip install -e .[dev]
	pip install -r requirements-dev.txt 2>/dev/null || echo "No requirements-dev.txt found"

# Code formatting
format:
	@echo "Formatting code with ruff..."
	ruff format agentic_spec/ tests/

format-check:
	@echo "Checking code formatting..."
	ruff format --check agentic_spec/ tests/

# Linting
lint:
	@echo "Running linting checks..."
	ruff check agentic_spec/ tests/

lint-fix:
	@echo "Auto-fixing linting issues..."
	ruff check --fix agentic_spec/ tests/

# Combined checks
check: format-check lint
	@echo "All code quality checks completed"

quality: format lint test-fast
	@echo "Comprehensive quality checks completed"

# Testing
test:
	@echo "Running tests..."
	pytest

test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=agentic_spec --cov-report=term-missing --cov-report=html

test-fast:
	@echo "Running fast tests (excluding slow tests)..."
	pytest -m "not slow"

test-integration:
	@echo "Running integration tests..."
	pytest -m "integration"

test-unit:
	@echo "Running unit tests..."
	pytest -m "unit"

# CI pipeline
ci: format lint test-cov
	@echo "CI pipeline completed successfully"
	@echo "Code is properly formatted, linted, and tested"

# Cleanup
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Build
build: clean
	@echo "Building distribution packages..."
	python -m build

# Documentation (placeholder for future implementation)
docs:
	@echo "Documentation generation not yet implemented"
	@echo "Future: Generate API docs and user documentation"

# Development workflow helpers
dev-setup: install-dev
	@echo "Development environment setup complete"
	@echo "Run 'make check' to verify code quality"
	@echo "Run 'make test' to run tests"

pre-commit: format lint test-fast
	@echo "Pre-commit checks completed"
	@echo "Code is ready for commit"

# Verbose versions for debugging
format-verbose:
	@echo "Formatting code with verbose output..."
	ruff format --verbose agentic_spec/ tests/

lint-verbose:
	@echo "Running linting with verbose output..."
	ruff check --verbose agentic_spec/ tests/

test-verbose:
	@echo "Running tests with verbose output..."
	pytest -v

# Performance and analysis
test-performance:
	@echo "Running performance tests..."
	pytest -m "slow" --durations=10

analyze:
	@echo "Running code analysis..."
	ruff check --statistics agentic_spec/ tests/
	@echo ""
	@echo "Test coverage summary:"
	pytest --cov=agentic_spec --cov-report=term --quiet

# Release helpers
version-check:
	@echo "Current version information:"
	@python -c "import agentic_spec; print(f'Package version: {agentic_spec.__version__ if hasattr(agentic_spec, \"__version__\") else \"Not defined\"}')" 2>/dev/null || echo "Package not installed"
	@python --version
	@ruff --version
	@pytest --version

# Security checks (for future implementation)
security:
	@echo "Security checks not yet implemented"
	@echo "Future: Run security linting and dependency checks"

# Docker helpers (for future implementation)
docker-build:
	@echo "Docker build not yet implemented"

docker-test:
	@echo "Docker test not yet implemented"

# Model consistency audit
audit-models:
	@echo "🔍 Auditing data model consistency..."
	@python tools/audit_models.py

# IDE integration helpers
vscode-setup:
	@echo "Setting up VS Code configuration..."
	@mkdir -p .vscode
	@echo "VS Code setup complete"

# Database/migration helpers (if needed in future)
migrate:
	@echo "No database migrations needed for this project"

# Benchmark helpers
benchmark:
	@echo "Benchmark tests not yet implemented"
	@echo "Future: Performance benchmarking for AI operations"

# Specification workflow commands
spec-commit:
	@echo "Committing specifications and implementation..."
	git add .
	git add specs/ agentic_spec/ tests/ pyproject.toml Makefile CLAUDE.md .pre-commit-config.yaml
	@git diff --quiet --cached || git commit -m "📋 Complete specification implementation and publish specs" \
		-m "" \
		-m "- Implemented specification requirements and fixes" \
		-m "- Updated codebase according to specifications" \
		-m "- Published completed specifications as implemented" \
		-m "" \
		-m "🤖 Generated with [Claude Code](https://claude.ai/code)" \
		-m "" \
		-m "Co-Authored-By: Claude <noreply@anthropic.com>" || echo "No changes to commit"

spec-publish:
	@echo "Publishing new draft specifications (cross-platform)..."
	python tools/publish_drafts.py

spec-publish-all:
	@echo "Publishing ALL specifications in specs/ directory..."
	@published_count=0; \
	failed_count=0; \
	for spec_file in $$(find specs/ -name "*.yaml"); do \
		spec_id=$$(basename $$spec_file .yaml | sed 's/^[0-9-]*-//'); \
		echo "📋 Publishing spec: $$spec_id"; \
		if agentic-spec publish $$spec_id 2>/dev/null; then \
			published_count=$$((published_count + 1)); \
		else \
			echo "❌ Failed to publish $$spec_id"; \
			failed_count=$$((failed_count + 1)); \
		fi; \
	done; \
	echo "========================================"; \
	echo "✅ Published $$published_count specifications"; \
	if [ $$failed_count -gt 0 ]; then \
		echo "❌ Failed to publish $$failed_count specifications"; \
	fi; \
	echo "========================================"

spec-complete: spec-commit spec-publish
	@echo "========================================="
	@echo "📋 Specification Workflow Complete:"
	@echo "✅ Changes committed to git"
	@echo "✅ Specifications published as implemented"
	@echo "✅ Ready for next development cycle"
	@echo "========================================="

# All-in-one quality gate
quality-gate: clean format lint test-cov
	@echo "========================================="
	@echo "Quality Gate Results:"
	@echo "✅ Code formatting: PASSED"
	@echo "✅ Linting checks: PASSED"
	@echo "✅ Test coverage: PASSED"
	@echo "========================================="
	@echo "Code is ready for production!"
