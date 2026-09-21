from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import urllib.request

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # التعامل مع طلبات OPTIONS و CORS Preflight
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == '/proxy':
            query = urllib.parse.parse_qs(parsed_path.query)
            target_url = query.get('url', [None])[0]

            if not target_url:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Missing url parameter')
                return

            try:
                # تجهيز الطلب مع هيدرز المتصفح لتجاوز الحظر
                req = urllib.request.Request(
                    target_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8'
                    }
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    content = response.read()
                    
                    self.send_response(200)
                    # هيدرز الـ CORS الكاملة
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', '*')
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(f'Error: {str(e)}'.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        # السماح بطلبات CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

if __name__ == '__main__':
    # تشغيل السيرفر على البورت 8080
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, ProxyHandler)
    print("Proxy server running on port 8080...")
    httpd.serve_forever()
