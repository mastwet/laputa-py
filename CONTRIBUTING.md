# Contributing to Laputa-Py

Thank you for your interest in contributing to Laputa-Py! This document provides guidelines and information for contributors.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bug fix
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

### Installation

```bash
# Clone your fork
git clone https://github.com/yourusername/laputa-py.git
cd laputa-py

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/laputa --cov-report=html

# Run specific test file
pytest tests/test_service.py
```

### Code Quality

```bash
# Run linting
flake8 src/ tests/

# Run type checking (if configured)
mypy src/
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and small
- Use meaningful variable and function names

## Pull Request Process

1. Update the README.md if needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update documentation if necessary
5. Request a review from maintainers

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Any error messages or logs

## License

By contributing to Laputa-Py, you agree that your contributions will be licensed under the MIT License.