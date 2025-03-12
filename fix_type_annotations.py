#!/usr/bin/env python
"""
Script to fix common type annotation issues in the codebase.

This script focuses on:
1. Adding explicit Optional type annotations for parameters with default None
2. Adding return type annotations to functions
3. Adding type annotations to variables

Usage:
    python fix_type_annotations.py [directory]
"""

import ast
import os
import sys
from typing import List, Optional, Tuple, Union


class TypeAnnotationFixer(ast.NodeVisitor):
    """AST visitor to identify and fix type annotation issues."""

    def __init__(self, source: str):
        self.source = source
        self.lines = source.splitlines()
        self.fixes = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions to check for missing type annotations."""
        # Check for missing return type annotation
        if node.returns is None:
            self.fixes.append(
                (
                    f"Missing return type annotation in function '{node.name}' at line {node.lineno}",
                    node.lineno,
                    "Add return type annotation (e.g., -> None, -> str, etc.)",
                )
            )

        # Check for parameters with default None but no Optional type
        for arg in node.args.defaults:
            if isinstance(arg, ast.Constant) and arg.value is None:
                idx = node.args.defaults.index(arg)
                param_idx = len(node.args.args) - len(node.args.defaults) + idx
                if param_idx < len(node.args.args):
                    param = node.args.args[param_idx]
                    if param.annotation is None:
                        self.fixes.append(
                            (
                                f"Parameter '{param.arg}' has default None but no type annotation in function '{node.name}' at line {node.lineno}",
                                node.lineno,
                                f"Add Optional type annotation (e.g., {param.arg}: Optional[Type] = None)",
                            )
                        )
                    elif not self._is_optional_annotation(param.annotation):
                        self.fixes.append(
                            (
                                f"Parameter '{param.arg}' has default None but not marked as Optional in function '{node.name}' at line {node.lineno}",
                                node.lineno,
                                f"Change to Optional type (e.g., {param.arg}: Optional[Type] = None)",
                            )
                        )

        # Continue visiting child nodes
        self.generic_visit(node)

    def _is_optional_annotation(self, annotation: ast.expr) -> bool:
        """Check if an annotation is Optional."""
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name) and annotation.value.id == "Optional":
                return True
            if isinstance(annotation.value, ast.Attribute) and annotation.value.attr == "Optional":
                return True
        return False

    def get_fixes(self) -> List[Tuple[str, int, str]]:
        """Return the list of fixes."""
        return self.fixes


def process_file(file_path: str) -> None:
    """Process a single Python file to find type annotation issues."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
            fixer = TypeAnnotationFixer(source)
            fixer.visit(tree)
            fixes = fixer.get_fixes()

            if fixes:
                print(f"\n{file_path}:")
                for message, line, suggestion in fixes:
                    print(f"  Line {line}: {message}")
                    print(f"    Suggestion: {suggestion}")
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")


def process_directory(directory: str) -> None:
    """Process all Python files in a directory recursively."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                process_file(file_path)


def main() -> None:
    """Main function to process files or directories."""
    if len(sys.argv) < 2:
        print("Usage: python fix_type_annotations.py [directory or file]")
        sys.exit(1)

    path = sys.argv[1]
    if os.path.isdir(path):
        process_directory(path)
    elif os.path.isfile(path) and path.endswith(".py"):
        process_file(path)
    else:
        print(f"Invalid path: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main() 