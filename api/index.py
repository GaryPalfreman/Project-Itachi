"""Vercel Python entrypoint forwarding to the shared Itachi FastAPI app."""
from api._app import app

__all__ = ["app"]
