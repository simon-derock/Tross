"""
main.py
───────
Root entrypoint for Tross LinkedIn Profile API.
Allows running with `uvicorn main:app --reload` as well as `uvicorn app.main:app --reload`.
"""

from app.main import app  # noqa: F401

__all__ = ["app"]
