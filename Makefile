.PHONY: help install install-dev test lint format clean build publish-test publish bump-patch bump-minor bump-major

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package
	pip install -e .

install-dev:  ## Install package with development dependencies
	pip install -e .[dev]

test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ -v --cov=appctx --cov-report=html --cov-report=term

lint:  ## Run linting checks
	black --check src/ tests/
	flake8 src/ tests/
	mypy src/

format:  ## Format code
	black src/ tests/
	isort src/ tests/

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build package
	python -m build

publish-test:  ## Publish to Test PyPI
	twine upload --repository testpypi dist/*

publish:  ## Publish to PyPI
	twine upload dist/*

bump-patch:  ## Bump patch version
	python scripts/bump_version.py patch

bump-minor:  ## Bump minor version
	python scripts/bump_version.py minor

bump-major:  ## Bump major version
	python scripts/bump_version.py major

check-build:  ## Check if package builds correctly
	python -m build
	twine check dist/*