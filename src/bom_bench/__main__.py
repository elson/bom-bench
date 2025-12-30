"""Entry point for running bom-bench as a module.

Allows the package to be run as:
    python -m bom_bench
"""

import sys

from bom_bench.cli import main

if __name__ == "__main__":
    sys.exit(main())
