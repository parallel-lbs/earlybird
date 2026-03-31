"""Shared auth dependency — avoids circular imports."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException

API_TOKEN = os.environ.get("EARLYBIRD_API_TOKEN")


def verify_token(authorization: str | None = Header(None)):
    if not API_TOKEN:
        return
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="invalid token")
