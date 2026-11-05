#!/usr/bin/env python
"""Django command-line utility for development tasks."""

import os
import sys


def main():
    """Run a Django management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cardfactory.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
