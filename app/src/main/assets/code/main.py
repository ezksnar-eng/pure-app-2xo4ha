import time
import requests
import urllib3
from flask import Flask, request, Response
from flask_cors import CORS

# إيقاف تحذيرات شهادات SSL غير الموثقة
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)  # تفعيل CORS لتجاوز القيود بين التطبيقين

# هيدرز للتمويه كأن الطلب جاي من متصفح حقيقي لتجاوز حظر أزورا
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://azorafly.com/'
}

@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
def proxy():
    target_url = request.args.get('url')
    
    # صفحة التحقق من عمل البروكسي بالخلفية
    if not target_url:
        return Response("🛡️ سيرفر البروكسي الداخلي شغال بالخلفية وجاهز 100%!", status=200, mimetype='text/plain; charset=utf-8')

    try:
        # إرسال الطلب للموقع الأصلي وتجاوز الحظر
        resp = requests.get(target_url, headers=HEADERS, timeout=15, verify=False)
        
        # إرجاع النتيجة للتطبيق الساحب
        response = Response(resp.content, status=resp.status_code)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Content-Type'] = resp.headers.get('Content-Type', 'text/html; charset=utf-8')
        return response

    except Exception as e:
        return Response(f"Error fetching site: {str(e)}", status=500)

def run_server_forever():
    """حلقة تشغيل مستمرة بالخلفية تعيد تشغيل السيرفر فوراً لو حدث أي انقطاع"""
    while True:
        try:
            print("⚡ جاري تشغيل سيرفر البروكسي على المنفذ 8080...")
            # استخدام سيرفر Flask المدمج القياسي لتفادي المشاكل مع Chaquopy
            app.run(host='0.0.0.0', port=8080, threaded=True, debug=False)
        except Exception as e:
            print(f"⚠️ إعادة تشغيل السيرفر تلقائياً بالخلفية: {e}")
            time.sleep(1)

if __name__ == '__main__':
    run_server_forever()
