.PHONY: install test lint clean

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest --cov=src/laputa --cov-report=html --cov-report=term

lint:
	flake8 src/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete