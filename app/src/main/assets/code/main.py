import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request
import urllib.error
import ssl

PORT = 8080

# إعداد ترويسات متصفح حقيقي لتجاوز الحماية
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Upgrade-Insecure-Requests': '1'
}

class ProxyHandler(BaseHTTPRequestHandler):

    def _set_cors_headers(self):
        """إضافة ترويسات CORS للسماح للـ HTML بالاتصال بدون قيود"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        """الاستجابة لطلبات المعاينة (Preflight requests)"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            payload = json.loads(post_data.decode('utf-8'))
            target_url = payload.get('url')

            if not target_url:
                self.respond_json({'status': 'error', 'message': 'رابط غير موجود'}, 400)
                return

            print(f"🌐 [Proxy Fetching]: {target_url}")

            # جلب محتوى الصفحة مع محاولات إعادة الاتصال
            html_content = self.fetch_with_retry(target_url)

            if html_content:
                self.respond_json({'status': 'success', 'html': html_content}, 200)
            else:
                self.respond_json({'status': 'error', 'message': 'فشل جلب المحتوى من الموقع'}, 500)

        except Exception as e:
            print(f"❌ خطأ في البروكسي: {e}")
            self.respond_json({'status': 'error', 'message': str(e)}, 500)

    def fetch_with_retry(self, url, retries=3):
        """دالة جلب الصفحة مع إعادة المحاولة تلقائياً عند الفشل"""
        # التغاضي عن مشاكل شهادات SSL
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers=HEADERS)

        for attempt in range(1, retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                    # فك تشفير المحتوى
                    encoding = response.headers.get_param('charset') or 'utf-8'
                    return response.read().decode(encoding, errors='ignore')
            except urllib.error.HTTPError as e:
                print(f"⚠️ خطأ HTTP ({e.code}) في المحاولة {attempt} للرابط: {url}")
            except urllib.error.URLError as e:
                print(f"⚠️ خطأ اتصال ({e.reason}) في المحاولة {attempt} للرابط: {url}")
            except Exception as e:
                print(f"⚠️ استثناء غير متوقع ({e}) في المحاولة {attempt}")
            
            time.sleep(1)  # انتظر ثانية واحدة قبل إعادة المحاولة

        return None

    def respond_json(self, data, status_code):
        self.send_response(status_code)
        self._set_cors_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        # تعطيل طباعة الطلبات العادية للحفاظ على نظافة التيرمنال
        return

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, ProxyHandler)
    print(f"🚀 سيرفر البروكسي يعمل بنجاح على المنفذ: http://127.0.0.1:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف سيرفر البروكسي.")

if __name__ == '__main__':
    run_server()
