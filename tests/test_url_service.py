from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from app.store import SQLiteStore
from app.url_service import UrlService
from app.models import UrlCreate

def service(tmp_path): return UrlService(SQLiteStore(str(tmp_path/'t.db')), 'http://test')

def test_create_resolve_analytics(tmp_path):
    s=service(tmp_path); r=s.shorten(UrlCreate(url='https://example.com/a'))
    assert s.resolve(r['code']) == 'https://example.com/a'
    assert s.analytics(r['code'])['clicks'] == 1

def test_collision(tmp_path):
    s=service(tmp_path); s.shorten(UrlCreate(url='https://example.com', custom_alias='abc'))
    with pytest.raises(HTTPException) as e: s.shorten(UrlCreate(url='https://other.com', custom_alias='abc'))
    assert e.value.status_code == 409

def test_expired(tmp_path):
    s=service(tmp_path)
    with pytest.raises(HTTPException) as e: s.shorten(UrlCreate(url='https://example.com', expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)))
    assert e.value.status_code == 400

def test_scheme_validation(tmp_path):
    s=service(tmp_path)
    with pytest.raises(HTTPException) as e: s.shorten(UrlCreate(url='ftp://example.com'))
    assert e.value.status_code == 400
