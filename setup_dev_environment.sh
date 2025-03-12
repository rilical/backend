#!/bin/bash

# Exit on error
set -e

echo "Setting up development environment..."

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit
pip install pre-commit

# Install pre-commit hooks
pre-commit install

echo "Development environment setup complete!"
echo "Pre-commit hooks installed. They will run automatically on each commit."
echo ""
echo "To run code style checks manually, use:"
echo "  ./code_style.sh"
echo ""
echo "To run pre-commit hooks manually on all files:"
echo "  pre-commit run --all-files" 