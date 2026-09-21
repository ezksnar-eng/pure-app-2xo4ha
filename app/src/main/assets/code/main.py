import urllib.parse
from flask import Flask, Response, request
from flask_cors import CORS
import requests

app = Flask(__name__)
# تفعيل الـ CORS للكل
CORS(app)


@app.route('/proxy', methods=['GET'])
def proxy():
    target_url = request.args.get('url')

    if not target_url:
        return Response('الرابط مطلوب!', status=400)

    # فك تشفير الرابط
    target_url = urllib.parse.unquote(target_url)

    # هيدرز تمويه كأنك متصفح حقيقي لتجاوز الحماية
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        ),
        'Accept': (
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        ),
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
    }

    try:
        resp = requests.get(target_url, headers=headers, timeout=15)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type='text/html; charset=utf-8',
        )
    except Exception as e:
        return Response(f'حدث خطأ: {str(e)}', status=500)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
