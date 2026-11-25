"""PyInstaller entry point for the standalone ``primedf`` executable."""

import sys

from primedf.cli import main

if __name__ == "__main__":
    sys.exit(main())
