# Lily

Lily is an AI and agent framework designed to provide powerful tools for building intelligent applications.

## Features

- Modern Python framework for AI and agent development
- Comprehensive testing and documentation setup
- Development tools for code quality and formatting
- Integration with Petal framework for tandem development

## Installation

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd lily
   ```

2. Set up the development environment:
   ```bash
   python scripts/setup_dev.py
   ```

   This script will:
   - Install Lily dependencies
   - Install Petal (local editable if available, GitHub version otherwise)
   - Set up pre-commit hooks

3. For manual setup:
   ```bash
   uv pip install -e ".[dev,docs]"
   uv pip install -e ../petal  # If local Petal exists
   pre-commit install
   ```

## Development

### Available Commands

Use the Makefile for common development tasks:

```bash
# Show all available commands
make help

# Format code
make format

# Lint code
make lint

# Run tests
make test

# Run tests with coverage
make test-cov

# Build documentation
make docs

# Serve documentation locally
make docs-serve
```

### Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Linting and import sorting
- **MyPy**: Type checking
- **pytest**: Testing with coverage
- **pre-commit**: Git hooks for quality checks

### Testing

Tests are located in the `tests/` directory:

- `tests/lily/`: Unit tests for the lily package
- `tests/integration/`: Integration tests
- `tests/fixtures/`: Test fixtures and data

Run tests with:
```bash
uv run pytest tests/
```

### Documentation

Documentation is built using Sphinx and located in `docs/`:

- Build documentation: `make docs`
- Serve locally: `make docs-serve`
- Clean build: `make docs-clean`

## Project Structure

```
lily/
├── src/lily/           # Main package source code
├── tests/              # Test suite
├── docs/               # Documentation
├── examples/           # Usage examples
├── scripts/            # Utility scripts
├── data/               # Project data
├── .github/            # GitHub workflows
├── .vscode/            # VS Code configuration
├── pyproject.toml      # Project configuration
├── Makefile           # Development commands
└── README.md          # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting: `make checkit`
5. Commit your changes
6. Push to your fork and submit a pull request

## Development Strategy

This project is currently in MVP phase using a rapid prototyping approach. See [Development Strategy](docs/DEVELOPMENT_STRATEGY.md) for details on the current approach and future migration plans.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Jeff Richley - jeffrichley@gmail.com
