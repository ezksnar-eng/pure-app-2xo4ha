import sys
import os
import json
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080

class ProxyHandler(BaseHTTPRequestHandler):
    # إضافة معالجة طلبات OPTIONS الخاصة بالـ CORS
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except Exception:
            data = {}

        target_url = data.get('url')
        if not target_url:
            self._send_json({'error': 'No URL provided'}, status=400)
            return

        print(f"🔄 [PROXY] جاري جلب: {target_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            req = urllib.request.Request(target_url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                self._send_json({'status': 'success', 'html': html_content})
        except Exception as e:
            print(f"❌ [PROXY] خطأ للجلب: {e}")
            self._send_json({'status': 'error', 'message': str(e)}, status=500)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')  # التمرير الآمن بدون منع CORS
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

def run_proxy():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, ProxyHandler)
    print(f"🚀 تطبيق البروكسي شغال على المنفذ {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف البروكسي.")

if __name__ == "__main__":
    run_proxy()
