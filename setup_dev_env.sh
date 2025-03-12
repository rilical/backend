#!/bin/bash
set -e

# Check if Python 3.9+ is installed
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9.0"

echo "Checking Python version..."
if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    echo "Error: Python 3.9 or higher required, you have $python_version"
    exit 1
fi
echo "Python $python_version detected, continuing..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install development dependencies
echo "Installing development dependencies..."
pip install -r requirements-dev.txt

# Creating pre-commit hook
echo "Setting up pre-commit hook..."
PRE_COMMIT_HOOK=".git/hooks/pre-commit"

cat > "$PRE_COMMIT_HOOK" <<EOL
#!/bin/bash
set -e

# Activate virtual environment
source .venv/bin/activate

# Format code with Black
echo "Running Black..."
black .

# Sort imports with isort
echo "Running isort..."
isort .

# Lint code with flake8
echo "Running flake8..."
flake8

# Check types with mypy
echo "Running mypy..."
mypy .
EOL

chmod +x "$PRE_COMMIT_HOOK"

echo "Development environment setup complete!"
echo "Run 'source .venv/bin/activate' to activate the virtual environment."
echo "Use 'black .', 'isort .', 'flake8', and 'mypy .' to manually run the tools."
