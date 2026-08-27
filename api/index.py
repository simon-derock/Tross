"""
api/index.py
────────────
Vercel serverless entry point.
Vercel's Python runtime expects a WSGI/ASGI handler named `app` in api/index.py.
We re-export the FastAPI `app` object so Vercel can serve it.
"""

from app.main import app  # noqa: F401  — re-exported for Vercel

__all__ = ["app"]
