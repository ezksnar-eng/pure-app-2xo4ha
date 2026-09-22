import os
import sys
import time
import requests
from flask import Flask, request, Response
from flask_cors import CORS
from gevent.pywsgi import WSGIServer

app = Flask(__name__)
CORS(app)  # السماح بطلبات CORS لتفادي أي رفض بالصفحة

# الهيدرز للتمويه كأن الطلب جاي من متصفح حقيقي لتجاوز الحظر
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://azorafly.com/'
}

@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
def proxy():
    target_url = request.args.get('url')
    
    if not target_url:
        return Response("⚠️ البروكسي الداخلي شغّال وجاهز لاستلام الطلبات...", status=200, mimetype='text/plain; charset=utf-8')

    try:
        # إرسال الطلب للموقع الأصلي
        resp = requests.get(target_url, headers=HEADERS, timeout=15, verify=False)
        
        # استرجاع النتيجة وتمريرها للساحب
        response = Response(resp.content, status=resp.status_code)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Content-Type'] = resp.headers.get('Content-Type', 'text/html; charset=utf-8')
        return response

    except Exception as e:
        return Response(f"Error fetching site: {str(e)}", status=500)

def run_server_forever():
    """حلقة تشغيل مستمرة بالخلفية لمنع إغلاق البروكسي نهائياً"""
    while True:
        try:
            print("🛡️ جاري تشغيل خادم البروكسي الداخلي على المنفذ 8080...")
            # استخدام WSGIServer من Gevent لتحمل الـ 25 عامل والطلبات المتوازية بكفاءة
            http_server = WSGIServer(('0.0.0.0', 8080), app)
            http_server.serve_forever()
        except Exception as e:
            print(f"⚠️ حدث انقطاع بالبروكسي: {e}. جاري إعادة التشغيل خلال ثانية...")
            time.sleep(1)

if __name__ == '__main__':
    # إيقاف تحذيرات الشهادات الأمنية غير الموثقة
    requests.packages.urllib3.disable_warnings()
    run_server_forever()
