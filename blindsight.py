#!/usr/bin/env python3
"""Convenience entry point so the tool runs without installation:

    python blindsight.py path/to/image.jpg
"""

from blindsight.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
