#!/usr/bin/env python3
"""Backward-compatible entrypoint for the shortificator pipeline.

The implementation now lives in the ``shortificator`` package; this module is
kept so existing invocations (``python shorts_factory.py ...``) keep working.
"""

from shortificator.cli import main

if __name__ == "__main__":
    main()
