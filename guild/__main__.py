"""Allow running guild as ``python -m guild``."""

import sys

from guild.cli import main

if __name__ == "__main__":
    sys.exit(main())
