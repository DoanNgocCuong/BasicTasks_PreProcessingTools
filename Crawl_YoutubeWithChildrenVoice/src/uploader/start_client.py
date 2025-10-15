#!/usr/bin/env python3
"""
Convenience script to start the upload client.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from client import main

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python start_client.py <path_to_manifest.json>")
        sys.exit(1)
    manifest_path = sys.argv[1]
    main(manifest_path)