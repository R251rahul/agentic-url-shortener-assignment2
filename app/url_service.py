from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from fastapi import HTTPException
from .models import UrlCreate

class UrlService:
    def __init__(self, store, base_url: str = "http://localhost:8000"):
        self.store = store
        self.base_url = base_url.rstrip("/")

    def shorten(self, request: UrlCreate):
        if not re.match(r"^https?://", request.url, re.I):
            raise HTTPException(400, "Only http/https URLs are supported")
        code = request.custom_alias or self._code(request.url)
        if self.store.get_url(code):
            raise HTTPException(409, "Short code already exists")
        now = datetime.now(timezone.utc)
        if request.expires_at and request.expires_at <= now:
            raise HTTPException(400, "expires_at must be in the future")
        self.store.create_url(code, request.url, now, request.expires_at)
        return {"code": code, "short_url": f"{self.base_url}/{code}", "target_url": request.url, "expires_at": request.expires_at}

    def resolve(self, code: str):
        row = self.store.get_url(code)
        if not row:
            raise HTTPException(404, "Short URL not found")
        if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
            raise HTTPException(410, "Short URL has expired")
        self.store.record_click(code, datetime.now(timezone.utc))
        return row["target_url"]

    def analytics(self, code: str):
        row = self.store.get_url(code)
        if not row:
            raise HTTPException(404, "Short URL not found")
        return {"code": code, "target_url": row["target_url"], "clicks": row["clicks"],
                "last_accessed_at": datetime.fromisoformat(row["last_accessed_at"]) if row["last_accessed_at"] else None}

    @staticmethod
    def _code(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:8]
