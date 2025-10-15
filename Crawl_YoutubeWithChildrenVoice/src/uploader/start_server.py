#!/usr/bin/env python3
"""
Convenience script to start the upload server.
"""

import uvicorn
from server import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)