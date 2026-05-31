"""
FastAPI Server Runner Script
Automatically detects Docker environment and adjusts host/port accordingly
"""
import sys
import os
import warnings

# Suppress all warnings
warnings.filterwarnings("ignore")

# Suppress RDKit deprecation warnings at stderr level
import logging
logging.getLogger("rdkit").setLevel(logging.ERROR)

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn

if __name__ == "__main__":
    # Detect if running in Docker
    running_in_docker = os.path.exists('/.dockerenv')
    
    if running_in_docker:
        # In Docker: bind to 0.0.0.0 and port 5000 (matches docker-compose mapping)
        host = "0.0.0.0"
        port = 5000
        is_reload = False  # Disable reload in Docker
    else:
        # Local development: bind to localhost and port 8000 WITHOUT reload (to let index build complete)
        host = "127.0.0.1"
        port = 8000
        is_reload = False  # DISABLED: Don't interrupt index building with auto-reload
    
    print(f"[STARTUP] Starting FastAPI server on {host}:{port}")
    if running_in_docker:
        print("   Running in Docker mode (reload disabled)")
    else:
        print("   Running in local development mode (reload disabled for index stability)")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=is_reload,
        log_level="info"
    )
