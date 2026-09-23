import sys
import os
import re
import json
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080

class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        target_url = data.get('url')
        if not target_url:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No URL provided'}).encode('utf-8'))
            return

        print(f"🔄 [PROXY] جاري جلب: {target_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            req = urllib.request.Request(target_url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                res_payload = {'status': 'success', 'html': html_content}
                self.wfile.write(json.dumps(res_payload).encode('utf-8'))
        except Exception as e:
            print(f"❌ [PROXY] خطأ للجلب: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            res_payload = {'status': 'error', 'message': str(e)}
            self.wfile.write(json.dumps(res_payload).encode('utf-8'))

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
