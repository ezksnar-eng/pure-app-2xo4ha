"""
proxy-gateway
=============
Lightweight async HTTP proxy that fetches a target URL through
cloudscraper (Cloudflare/anti-bot bypass) and returns the raw HTML.

Run:
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

Note: cloudscraper's underlying session is NOT safe to share across
threads while mid-request in all versions, so this service keeps a
small pool of scraper instances (one per worker slot) instead of one
global instance hit by hundreds of concurrent callers.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import os
import threading

import cloudscraper
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("proxy-gateway")

app = FastAPI(title="proxy-gateway")

# Pool size: how many independent cloudscraper sessions to rotate
# across. Each is its own TLS/header fingerprint session.
POOL_SIZE = int(os.environ.get("SCRAPER_POOL_SIZE", "12"))
REQUEST_TIMEOUT = int(os.environ.get("FETCH_TIMEOUT", "30"))

_local = threading.local()
_pool_counter = itertools.count()


def _get_scraper() -> cloudscraper.CloudScraper:
    """One cloudscraper session per worker thread (threads are reused
    by the default asyncio thread-pool executor), rotating browser
    fingerprints across a small pool for basic header diversity.
    """
    if not hasattr(_local, "scraper"):
        idx = next(_pool_counter) % POOL_SIZE
        browsers = [
            {"browser": "chrome", "platform": "windows", "mobile": False},
            {"browser": "chrome", "platform": "darwin", "mobile": False},
            {"browser": "firefox", "platform": "windows", "mobile": False},
        ]
        _local.scraper = cloudscraper.create_scraper(browser=browsers[idx % len(browsers)])
    return _local.scraper


def _sync_fetch(url: str) -> tuple[int, str]:
    scraper = _get_scraper()
    resp = scraper.get(url, timeout=REQUEST_TIMEOUT)
    return resp.status_code, resp.text


@app.get("/fetch", response_class=PlainTextResponse)
async def fetch(url: str = Query(..., description="Target URL to fetch through cloudscraper")):
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must start with http:// or https://")

    try:
        status_code, html = await asyncio.to_thread(_sync_fetch, url)
    except Exception as e:
        log.warning("Fetch failed for %s: %s", url, e)
        raise HTTPException(status_code=502, detail=f"upstream fetch failed: {e}")

    if status_code != 200:
        raise HTTPException(status_code=502, detail=f"upstream returned {status_code}")

    return html


@app.get("/health")
async def health():
    return {"status": "ok"}
