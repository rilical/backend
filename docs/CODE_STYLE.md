# Python Code Style Guide

This document outlines the code style tools and practices used in this project.

## Tools

We use the following tools to maintain code quality and consistency:

- **Black**: Code formatter that enforces a consistent style
- **isort**: Sorts and organizes imports
- **Flake8**: Linter that checks for style and potential errors
- **MyPy**: Static type checker for Python
- **pre-commit**: Framework for managing git pre-commit hooks

## Setup

To set up the development environment with all necessary tools:

```bash
./setup_dev_environment.sh
```

This script will:
1. Install required Python dependencies
2. Install pre-commit
3. Set up pre-commit hooks

## Running Code Style Checks

### Automatic Checks

Once set up, pre-commit hooks will automatically run before each commit, checking only the files that have been changed.

### Manual Checks

To manually run all code style checks:

```bash
./code_style.sh
```

This script will run:
1. Black formatter
2. isort
3. Flake8
4. MyPy
5. Optionally, pre-commit on all files

To run pre-commit on all files:

```bash
pre-commit run --all-files
```

## Configuration Files

- `.pre-commit-config.yaml`: Configuration for pre-commit hooks
- `setup.cfg` or `pyproject.toml`: Configuration for Black, isort, Flake8, and MyPy

## Common Issues and Solutions

### Module Name Conflicts in MyPy

If you encounter module name conflicts in MyPy (e.g., "source file found twice under different module names"), consider:

1. Adding `__init__.py` files to ensure proper package structure
2. Setting the `MYPYPATH` environment variable
3. Using the `--namespace-packages` flag with MyPy

### Type Annotation Issues

For type annotation issues:

1. Use explicit type annotations for function parameters and return values
2. Import types from the `typing` module (e.g., `List`, `Dict`, `Optional`)
3. Consider using type stubs for third-party libraries

## Best Practices

1. **Run code style checks before committing**: This prevents style issues from being committed
2. **Fix issues incrementally**: Focus on fixing one type of issue at a time
3. **Keep configurations consistent**: Ensure all tools are configured to work together (e.g., line length)
4. **Document exceptions**: If you need to ignore a specific rule, document why
