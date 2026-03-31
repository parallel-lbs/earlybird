"""Admin API router — authentication, stats, sources, LLM config."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from earlybird.config import DATA_DIR, MAP_DIR, SOURCE_GROUPS

log = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin/api", tags=["admin"])

# ── Hardcoded admin credentials ──────────────────────────────────────────────
ADMIN_USERNAME = "magera"
ADMIN_PASSWORD = "Moorechip1965$"

# ── JWT helpers (HMAC-SHA256, no PyJWT dependency) ───────────────────────────
JWT_SECRET = os.urandom(32).hex()
JWT_EXPIRY_SECONDS = 86400  # 24 hours


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _jwt_encode(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig_input = f"{h}.{p}".encode()
    sig = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def _jwt_decode(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("bad token")
        h, p, s = parts
        sig_input = f"{h}.{p}".encode()
        expected = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
        actual = _b64url_decode(s)
        if not hmac.compare_digest(expected, actual):
            raise ValueError("bad signature")
        payload = json.loads(_b64url_decode(p))
        if payload.get("exp", 0) < time.time():
            raise ValueError("token expired")
        return payload
    except Exception as exc:
        raise ValueError(f"invalid token: {exc}") from exc


# ── Auth dependency ──────────────────────────────────────────────────────────

def require_admin(authorization: str | None = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing or invalid Authorization header")
    token = authorization[7:]
    try:
        payload = _jwt_decode(token)
    except ValueError as exc:
        raise HTTPException(401, str(exc))
    return payload


# ── LLM config persistence ──────────────────────────────────────────────────
LLM_CONFIG_PATH = DATA_DIR / "llm_config.json"


def _read_llm_config() -> dict:
    if LLM_CONFIG_PATH.exists():
        try:
            return json.loads(LLM_CONFIG_PATH.read_text())
        except Exception:
            pass
    return {"provider": "openai", "model": "gpt-5.4", "api_key": ""}


def _write_llm_config(cfg: dict) -> None:
    LLM_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


# ── Models ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class SourceConfig(BaseModel):
    name: str
    group: str = ""
    enabled: bool = True


class LLMConfigUpdate(BaseModel):
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None


class OAuthCallback(BaseModel):
    code: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@admin_router.post("/login")
def admin_login(req: LoginRequest):
    if req.username != ADMIN_USERNAME or req.password != ADMIN_PASSWORD:
        raise HTTPException(401, "invalid credentials")
    payload = {
        "sub": req.username,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
    }
    token = _jwt_encode(payload)
    return {"token": token, "username": req.username}


@admin_router.get("/me")
def admin_me(user: dict = Depends(require_admin)):
    return {"username": user["sub"], "role": "admin"}


@admin_router.get("/stats")
def admin_stats(user: dict = Depends(require_admin)):
    item_count = 0
    categories = []
    sources_count = 0

    geojson_path = MAP_DIR / "latest.geojson"
    if geojson_path.exists():
        try:
            data = json.loads(geojson_path.read_text())
            features = data.get("features", [])
            item_count = len(features)
            cluster_labels = set()
            source_names = set()
            for f in features:
                props = f.get("properties", {})
                cl = props.get("cluster_label")
                if cl:
                    cluster_labels.add(cl)
                src = props.get("source")
                if src:
                    source_names.add(src)
            categories = sorted(cluster_labels)
            sources_count = len(source_names)
        except Exception:
            pass

    feed_path = DATA_DIR / "daily-feed.json"
    if item_count == 0 and feed_path.exists():
        try:
            feed = json.loads(feed_path.read_text())
            items = feed.get("items", [])
            item_count = len(items)
        except Exception:
            pass

    return {
        "item_count": item_count,
        "categories": categories,
        "category_count": len(categories),
        "sources_count": sources_count,
    }


@admin_router.get("/sources")
def admin_get_sources(user: dict = Depends(require_admin)):
    result = []
    for group, members in SOURCE_GROUPS.items():
        if group == "all":
            continue
        result.append({
            "group": group,
            "sources": members,
            "enabled": True,
        })
    return result


@admin_router.post("/sources")
def admin_add_source(cfg: SourceConfig, user: dict = Depends(require_admin)):
    group = cfg.group or cfg.name
    if group not in SOURCE_GROUPS:
        SOURCE_GROUPS[group] = []
    if cfg.name not in SOURCE_GROUPS[group]:
        SOURCE_GROUPS[group].append(cfg.name)
    if cfg.name not in SOURCE_GROUPS["all"]:
        SOURCE_GROUPS["all"].append(cfg.name)
    return {"status": "ok", "group": group, "sources": SOURCE_GROUPS[group]}


@admin_router.get("/llm/config")
def admin_get_llm_config(user: dict = Depends(require_admin)):
    cfg = _read_llm_config()
    masked_key = ""
    if cfg.get("api_key"):
        k = cfg["api_key"]
        masked_key = k[:4] + "****" + k[-4:] if len(k) > 8 else "****"
    return {
        "provider": cfg.get("provider", "openai"),
        "model": cfg.get("model", "gpt-5.4"),
        "api_key_set": bool(cfg.get("api_key")),
        "api_key_masked": masked_key,
    }


@admin_router.post("/llm/config")
def admin_update_llm_config(update: LLMConfigUpdate, user: dict = Depends(require_admin)):
    cfg = _read_llm_config()
    if update.provider is not None:
        cfg["provider"] = update.provider
    if update.model is not None:
        cfg["model"] = update.model
    if update.api_key is not None:
        cfg["api_key"] = update.api_key
    _write_llm_config(cfg)
    return {"status": "ok", "provider": cfg["provider"], "model": cfg["model"]}


@admin_router.post("/llm/oauth/callback")
def admin_oauth_callback(cb: OAuthCallback, user: dict = Depends(require_admin)):
    # Placeholder: in production this would exchange the code for an access token
    log.info("OAuth callback received with code: %s...", cb.code[:8] if len(cb.code) > 8 else cb.code)
    return {"status": "ok", "message": "OAuth code received (exchange not yet implemented)"}
