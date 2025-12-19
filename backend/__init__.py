# Backend Package Initialization
# Exports the FastAPI app instance for use by uvicorn server.
# When you run: uvicorn backend.api:app
# This imports the app created in api.py

from .api import app

__version__ = "1.0.0"
__all__ = ["app"]
