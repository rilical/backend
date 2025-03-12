#!/usr/bin/env python
"""
Script to fix common flake8 issues in the codebase.

This script focuses on:
1. Removing unused imports (F401)
2. Removing trailing whitespace (W291)
3. Fixing unused variables (F841)
4. Fixing f-string issues (F541)

Usage:
    python fix_flake8_issues.py [directory]
"""

import ast
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple


class ImportFinder(ast.NodeVisitor):
    """AST visitor to find all imports and their usage."""

    def __init__(self):
        self.imports = {}  # name -> (module, alias, lineno)
        self.used_names = set()

    def visit_Import(self, node):
        """Visit import statements."""
        for name in node.names:
            alias = name.asname or name.name
            self.imports[alias] = (name.name, name.asname, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Visit from ... import statements."""
        for name in node.names:
            alias = name.asname or name.name
            module = node.module if node.module else ""
            self.imports[alias] = (f"{module}.{name.name}", name.asname, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node):
        """Visit name references."""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def get_unused_imports(self) -> Dict[int, List[str]]:
        """Return unused imports grouped by line number."""
        unused = {}
        for name, (module, alias, lineno) in self.imports.items():
            if name not in self.used_names and name != "_":
                if lineno not in unused:
                    unused[lineno] = []
                unused[lineno].append(name)
        return unused


def fix_unused_imports(file_path: str) -> List[Tuple[int, str, str]]:
    """Find and fix unused imports in a file."""
    fixes = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
            finder = ImportFinder()
            finder.visit(tree)
            unused_imports = finder.get_unused_imports()

            lines = source.splitlines()
            for lineno, names in unused_imports.items():
                line = lines[lineno - 1]
                for name in names:
                    # Simple case: import x
                    if re.search(rf"\bimport\s+{name}\b", line):
                        fixes.append((lineno, line, f"Remove unused import: {name}"))
                    # from module import x
                    elif re.search(rf"\bfrom\s+\S+\s+import\s+.*\b{name}\b", line):
                        if "," in line:  # Multiple imports on the same line
                            fixes.append(
                                (lineno, line, f"Remove unused import: {name} from line")
                            )
                        else:
                            fixes.append((lineno, line, f"Remove entire line: {line.strip()}"))
                    # import module as name
                    elif re.search(rf"\bimport\s+\S+\s+as\s+{name}\b", line):
                        fixes.append((lineno, line, f"Remove unused import: {name}"))

        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return fixes


def fix_trailing_whitespace(file_path: str) -> List[Tuple[int, str, str]]:
    """Find and fix trailing whitespace in a file."""
    fixes = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if line.rstrip() != line[:-1] if line.endswith("\n") else line:
                fixes.append(
                    (i + 1, line, f"Remove trailing whitespace: {repr(line)}")
                )
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return fixes


def fix_unused_variables(file_path: str) -> List[Tuple[int, str, str]]:
    """Find unused variables (simple cases only)."""
    fixes = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Simple regex pattern for variable assignments that might be unused
        # This is a simplified approach and won't catch all cases
        pattern = r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=.*$"
        lines = source.splitlines()
        
        for i, line in enumerate(lines):
            match = re.match(pattern, line)
            if match:
                var_name = match.group(1)
                # Check if the variable is used in subsequent lines
                is_used = False
                for next_line in lines[i+1:]:
                    if re.search(rf"\b{var_name}\b", next_line):
                        is_used = True
                        break
                
                if not is_used:
                    fixes.append(
                        (i + 1, line, f"Unused variable: {var_name}")
                    )
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return fixes


def fix_fstring_issues(file_path: str) -> List[Tuple[int, str, str]]:
    """Find f-string issues (F541: f-string without any placeholders)."""
    fixes = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Look for f-strings without placeholders
        pattern = r"f['\"](?:(?!\{).)*['\"]"
        for i, line in enumerate(lines):
            matches = re.findall(pattern, line)
            for match in matches:
                fixes.append(
                    (i + 1, line, f"f-string without placeholders: {match}")
                )
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return fixes


def process_file(file_path: str) -> None:
    """Process a single Python file to find and report flake8 issues."""
    unused_imports = fix_unused_imports(file_path)
    whitespace_issues = fix_trailing_whitespace(file_path)
    unused_vars = fix_unused_variables(file_path)
    fstring_issues = fix_fstring_issues(file_path)
    
    all_issues = unused_imports + whitespace_issues + unused_vars + fstring_issues
    
    if all_issues:
        print(f"\n{file_path}:")
        for lineno, line, suggestion in all_issues:
            print(f"  Line {lineno}: {suggestion}")


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
        print("Usage: python fix_flake8_issues.py [directory or file]")
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