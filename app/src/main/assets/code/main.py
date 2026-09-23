import asyncio
import itertools
import logging
import os
import threading
from urllib.parse import parse_qs, urlparse

import cloudscraper

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("proxy-gateway")

# إعدادات الـ Scraper Pool
POOL_SIZE = int(os.environ.get("SCRAPER_POOL_SIZE", "12"))
REQUEST_TIMEOUT = int(os.environ.get("FETCH_TIMEOUT", "30"))

_local = threading.local()
_pool_counter = itertools.count()


def _get_scraper() -> cloudscraper.CloudScraper:
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


# تطبيق WSGI/Web خفيف بدون الحاجة لـ FastAPI أو Uvicorn لتسهيل بناء الـ APK
def application(environ, start_response):
    path = environ.get("PATH_INFO", "")
    query_string = environ.get("QUERY_STRING", "")

    if path == "/health":
        start_response("200 OK", [("Content-Type", "application/json")])
        return [b'{"status": "ok"}']

    elif path == "/fetch":
        params = parse_qs(query_string)
        url_list = params.get("url", [])

        if not url_list:
            start_response("400 Bad Request", [("Content-Type", "text/plain")])
            return [b"Missing url parameter"]

        target_url = url_list[0]
        if not target_url.startswith(("http://", "https://")):
            start_response("400 Bad Request", [("Content-Type", "text/plain")])
            return [b"url must start with http:// or https://"]

        try:
            status_code, html = _sync_fetch(target_url)
            if status_code != 200:
                start_response("502 Bad Gateway", [("Content-Type", "text/plain")])
                return [f"Upstream returned status code {status_code}".encode("utf-8")]

            start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
            return [html.encode("utf-8")]
        except Exception as e:
            log.warning("Fetch failed for %s: %s", target_url, e)
            start_response("502 Bad Gateway", [("Content-Type", "text/plain")])
            return [f"Upstream fetch failed: {e}".encode("utf-8")]

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not Found"]


app = application

if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    log.info("Starting proxy gateway server on port 8000...")
    httpd = make_server("0.0.0.0", 8000, application)
    httpd.serve_forever()
