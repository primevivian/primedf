"""PyInstaller entry point for the windowed ``PrimeDF.exe``."""

import sys

from primedf.gui import main

if __name__ == "__main__":
    sys.exit(main())
