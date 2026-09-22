import time
import threading
import urllib.parse
import urllib.request
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer

class IntegratedProxyHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        target_url = query.get('url', [None])[0]
        if not target_url and len(self.path) > 1:
            target_url = self.path[1:].lstrip('/')

        if not target_url:
            self._set_headers(400)
            self.wfile.write(b'Missing url parameter')
            return

        if 'appassets.androidplatform.net' in target_url:
            target_url = target_url.replace('https://appassets.androidplatform.net', 'https://azorafly.com')
            target_url = target_url.replace('http://appassets.androidplatform.net', 'https://azorafly.com')

        if not target_url.startswith('http://') and not target_url.startswith('https://'):
            target_url = 'https://' + target_url

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                target_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Referer': 'https://azorafly.com/'
                }
            )

            with urllib.request.urlopen(req, timeout=20, context=ctx) as response:
                content = response.read()
                self._set_headers(200)
                self.wfile.write(content)

        except Exception as e:
            self._set_headers(200)
            self.wfile.write(f'Error fetching site: {str(e)}'.encode('utf-8'))

    def log_message(self, format, *args):
        return

def run_proxy_server():
    while True:
        try:
            server_address = ('0.0.0.0', 8080)
            httpd = HTTPServer(server_address, IntegratedProxyHandler)
            print("🚀 Proxy server running on port 8080...")
            httpd.serve_forever()
        except Exception as e:
            print(f"⚠️ إعادة تشغيل البروكسي تلقائياً بسبب: {e}")
            time.sleep(2)

if __name__ == '__main__':
    proxy_thread = threading.Thread(target=run_proxy_server, daemon=True)
    proxy_thread.start()

    print("✅ سيرفر البروكسي شغّال بكتفاء ذاتي بالخلفية بدون انقطاع.")
    
    while True:
        time.sleep(1)
