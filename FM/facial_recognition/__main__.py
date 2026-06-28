"""Package entry point: enables ``python -m facial_recognition``.

Delegates to :func:`facial_recognition.cli.main`, forwarding the process
arguments (excluding the program name) and exiting with its return code.
"""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
