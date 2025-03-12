#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.

This is the standard Django management script that provides commands for
managing the RemitScout application, including running the development server,
creating database migrations, and managing users.

Version: 1.0
"""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "remit_scout.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django. Are you sure it's installed?") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
