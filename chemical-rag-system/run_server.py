"""
FastAPI Server Runner Script
Automatically detects Docker environment and adjusts host/port accordingly
"""
import sys
import os

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
        # Local development: bind to localhost and port 8000 with reload
        host = "127.0.0.1"
        port = 8000
        is_reload = True
    
    print(f"🚀 Starting FastAPI server on {host}:{port}")
    if running_in_docker:
        print("   Running in Docker mode (reload disabled)")
    else:
        print("   Running in local development mode (reload enabled)")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=is_reload,
        log_level="info"
    )
