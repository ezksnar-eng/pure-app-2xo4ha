from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import urllib.request
import ssl

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        
        # استخراج الرابط من الـ query أو من المسار المباشر
        target_url = query.get('url', [None])[0]
        if not target_url and len(self.path) > 1:
            target_url = self.path[1:].lstrip('/')

        if not target_url:
            self.send_response(400)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'Missing url parameter')
            return

        # تصليح الروابط اللي تجي من تطبيق الأندرويد الداخلي
        if 'appassets.androidplatform.net' in target_url:
            target_url = target_url.replace('https://appassets.androidplatform.net', 'https://azorafly.com')
            target_url = target_url.replace('http://appassets.androidplatform.net', 'https://azorafly.com')

        if not target_url.startswith('http://') and not target_url.startswith('https://'):
            target_url = 'https://' + target_url

        print(f"[📡 Fetching] -> {target_url}")

        try:
            # تجاوز فحص شهادات SSL حتى ما ينطي Internal Error 500
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                target_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
                    'Referer': 'https://azorafly.com/'
                }
            )

            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                content = response.read()
                
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', '*')
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)

        except Exception as e:
            print(f"[❌ Error] -> {str(e)}")
            self.send_response(200) # نرجع 200 ويا النص حتى ما يضرب البروكسي كراش 500
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(f'Error fetching site: {str(e)}'.encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

if __name__ == '__main__':
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, ProxyHandler)
    print("🚀 Proxy server running on port 8080 (SSL Fixed)...")
    httpd.serve_forever()
