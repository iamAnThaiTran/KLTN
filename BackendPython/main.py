#!/usr/bin/env python
# main.py

import uvicorn
import logging
import sys
from app.api.routes import app

if __name__ == "__main__":
    # Configure logging to force unbuffered output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        stream=sys.stdout,
        force=True
    )
    
    # Force stdout/stderr to unbuffered mode
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
