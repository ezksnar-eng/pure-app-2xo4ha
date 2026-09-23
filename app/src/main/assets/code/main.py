"""
proxy.py — بروكسي بسيط بملف وحيد
====================================
يستقبل GET /fetch?url=<TARGET_URL> ويرجّع HTML الصفحة المطلوبة بعد
تمريرها عبر cloudscraper (تجاوز Cloudflare). مبني فقط على مكتبة
Python القياسية (http.server) + مكتبة واحدة خارجية لا غنى عنها
(cloudscraper) — بدون أي framework.

التشغيل:
    pip install cloudscraper
    python proxy.py
يشتغل افتراضياً على http://0.0.0.0:8000
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import cloudscraper

PORT = 8000
REQUEST_TIMEOUT = 30

# نسخة scraper منفصلة لكل thread (الـ ThreadingHTTPServer يفتح thread لكل طلب)
_local = threading.local()


def get_scraper():
    if not hasattr(_local, "scraper"):
        _local.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    return _local.scraper


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[proxy] {self.address_string()} - {fmt % args}")

    def _send(self, status: int, body: str, content_type="text/plain; charset=utf-8"):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._send(200, json.dumps({"status": "ok"}), "application/json")
            return

        if parsed.path != "/fetch":
            self._send(404, "not found")
            return

        qs = parse_qs(parsed.query)
        target = qs.get("url", [None])[0]
        if not target or not target.startswith(("http://", "https://")):
            self._send(400, "missing or invalid url param")
            return

        try:
            scraper = get_scraper()
            resp = scraper.get(target, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                self._send(200, resp.text, "text/html; charset=utf-8")
            else:
                self._send(502, f"upstream status {resp.status_code}")
        except Exception as e:
            self._send(502, f"fetch error: {e}")

    def do_OPTIONS(self):
        # لتسهيل النداء من صفحة HTML تشتغل بمتصفح (CORS preflight)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), ProxyHandler)
    print(f"proxy.py يشتغل على http://0.0.0.0:{PORT}  (جرب: /fetch?url=https://example.com)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
