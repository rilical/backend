#!/usr/bin/env python3
"""
Script to run MyPy with the correct configuration to avoid module name conflicts.

This script:
1. Sets up the proper Python path
2. Runs MyPy with the appropriate options
3. Properly handles namespace packages

Usage:
    python run_mypy.py [directory...]
"""

import os
import subprocess
import sys


def main():
    """Run MyPy with correct configuration."""
    # Directories to check
    directories = sys.argv[1:] if len(sys.argv) > 1 else ["apps", "remit_scout", "quotes"]
    
    # Current directory (project root)
    project_root = os.path.abspath(os.getcwd())
    
    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = project_root
    env["MYPYPATH"] = project_root
    
    # Build the MyPy command
    cmd = [
        "mypy",
        "--namespace-packages",
        "--explicit-package-bases",
        "--ignore-missing-imports",
        "--config-file=mypy.ini",
    ] + directories
    
    print(f"Running: {' '.join(cmd)}")
    
    # Run MyPy
    result = subprocess.run(cmd, env=env, check=False)
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    main() 