import json
import re
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import quote

from bs4 import BeautifulSoup
import cloudscraper
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# 1. إعدادات الفايربيس (Firebase Config)
# ==========================================
# يمكنك استخدام ملف المفتاح serviceAccountKey.json أو وضع البيانيات مباشرة
try:
  cred = credentials.Certificate("serviceAccountKey.json")
  firebase_admin.initialize_app(cred)
except Exception as e:
  print(f"⚠️ تنبيه الفايربيس: لم يتم العثور على serviceAccountKey.json ({e})")

db = firestore.client()

PORT = 8080
BASE_ARCHIVE_URL = "https://azorafly.com/series/"
NUM_WORKERS = 616  # عدد الكائنات المتوازية

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "desktop": True}
)


# ==========================================
# 2. الدوال المساعدة ونظام السحب
# ==========================================
def safe_doc_id(text):
  return quote(text.strip().lower()).replace("%", "_")


def clean_chapter_name(text):
  match = re.search(r"(?:الفصل|chapter)\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
  return f"الفصل {match.group(1)}" if match else text.strip()


def process_manga_worker(manga_item):
  manga_title = manga_item["title"]
  manga_url = manga_item["href"]
  doc_id = safe_doc_id(manga_title)

  manga_ref = db.collection("manga").document(doc_id)

  # 1. فحص منع التكرار والقفل التلقائي
  doc_snap = manga_ref.get()
  if doc_snap.exists:
    data = doc_snap.to_dict()
    if data.get("status") == "completed":
      print(f"⏩ [تخطي - موجودة سابقاً]: {manga_title}")
      return
    if data.get("status") == "in_progress":
      print(f"🔒 [تخطي - كائن آخر يعمل عليها]: {manga_title}")
      return

  # 2. قفل المانهوا لحساب هذا الكائن
  print(f"🚀 [استلام كائن] بدء سحب: {manga_title}")
  manga_ref.set({
      "title": manga_title,
      "source_url": manga_url,
      "status": "in_progress",
      "updated_at": firestore.SERVER_TIMESTAMP,
  }, merge=True)

  try:
    res = scraper.get(manga_url, timeout=20)
    if res.status_code != 200:
      manga_ref.update({"status": "failed"})
      return

    soup = BeautifulSoup(res.text, "html.parser")

    # التقييم والغلاف والتصنيفات
    rating = soup.select_one("div.num, span.rating, div.rating")
    rating_val = rating.text.strip() if rating else "N/A"

    cover = soup.select_one("div.thumb img, div.summary_image img")
    cover_url = cover.get("src") or cover.get("data-src") if cover else ""

    genres = [
        g.text.strip() for g in soup.select("div.genres-content a, div.mgen a")
    ]

    # جلب قائمة الفصول
    chapter_links = soup.select(
        'ul.clist li a, div.eplister li a, a[href*="/chapter"]'
    )
    chapters = []
    for a in chapter_links:
      href = a.get("href")
      text = a.text.strip()
      if href and not any(c["url"] == href for c in chapters):
        chapters.append({"title": clean_chapter_name(text), "url": href})

    # سحب الصور لكل فصل
    for ch in chapters:
      ch_res = scraper.get(ch["url"], timeout=20)
      if ch_res.status_code == 200:
        ch_soup = BeautifulSoup(ch_res.text, "html.parser")
        imgs = ch_soup.select(
            "#readerarea img, div.rdcontent img, div.reader-area img"
        )
        img_urls = [
            i.get("data-src") or i.get("src")
            for i in imgs
            if i.get("src") or i.get("data-src")
        ]
        img_urls = [
            url
            for url in img_urls
            if url and not any(x in url for x in ["logo", "banner", "avatar"])
        ]

        ch_doc_id = safe_doc_id(ch["title"])
        manga_ref.collection("chapters").document(ch_doc_id).set({
            "title": ch["title"],
            "images": img_urls,
            "url": ch["url"],
            "updated_at": firestore.SERVER_TIMESTAMP,
        }, merge=True)

    # حسم حالة المانهوا إلى مكتمل
    manga_ref.set({
        "rating": rating_val,
        "cover": cover_url,
        "genres": genres,
        "chapters_count": len(chapters),
        "status": "completed",
        "updated_at": firestore.SERVER_TIMESTAMP,
    }, merge=True)

    print(f"✅ [إكمال ناجح]: {manga_title} ({len(chapters)} فصل)")

  except Exception as e:
    print(f"❌ خطأ أثناء السحب ({manga_title}): {e}")
    manga_ref.update({"status": "failed"})


def start_full_archive_scraper():
  print("🌐 جاري فحص أرشيف أزورا الكامل...")
  all_manga_list = []
  page = 1

  while True:
    url = BASE_ARCHIVE_URL if page == 1 else f"{BASE_ARCHIVE_URL}page/{page}/"
    res = scraper.get(url, timeout=15)
    if res.status_code != 200:
      break

    soup = BeautifulSoup(res.text, "html.parser")
    links = soup.select("div.bsx a, div.listupd a")
    if not links:
      break

    page_manga = []
    for a in links:
      href = a.get("href")
      title = a.get("title") or a.text.strip()
      if href and "/series/" in href:
        page_manga.append({"href": href, "title": title})

    unique_manga = {m["href"]: m for m in page_manga}.values()
    all_manga_list.extend(unique_manga)
    page += 1

  print(
      f"📊 تم العثور على {len(all_manga_list)} مانهوا. تشغيل المحرك بـ"
      f" {NUM_WORKERS} كائن..."
  )
  with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
    executor.map(process_manga_worker, all_manga_list)

  print("🎉 اكتمل السحب الشامل!")


def clean_duplicate_manga():
  print("🧹 جاري تنظيف المانهوا المكررة بالكامل...")
  manga_docs = db.collection("manga").stream()
  seen_titles = {}
  deleted_count = 0

  for doc in manga_docs:
    data = doc.to_dict()
    title = data.get("title", "")
    normalized_title = re.sub(r"[^\w\s]", "", title).strip().lower()

    if normalized_title in seen_titles:
      print(f"🗑️ مسح نسخة مكررة: {title} (ID: {doc.id})")
      chapters = (
          db.collection("manga")
          .document(doc.id)
          .collection("chapters")
          .stream()
      )
      for ch in chapters:
        ch.reference.delete()
      doc.reference.delete()
      deleted_count += 1
    else:
      if normalized_title:
        seen_titles[normalized_title] = doc.id

  print(f"✅ تم تنظيف القاعده! تم مسح {deleted_count} مانهوا مكررة.")


# ==========================================
# 3. كود واجهة HTML المدمجة
# ==========================================
HTML_INTERFACE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>محرك سحب وتنظيف Pure Library</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background-color: #121212; color: #fff; font-family: system-ui, sans-serif; padding: 20px; }
        .container { max-width: 650px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 20px; color: #00e676; font-size: 20px; }
        .card { background: #1e1e1e; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #333; }
        button { width: 100%; padding: 12px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; margin-bottom: 8px; font-size: 14px; }
        .btn-scrape { background: #00e676; color: #000; }
        .btn-clean { background: #ab47bc; color: #fff; }
        #logBox { background: #000; border: 1px solid #222; padding: 10px; border-radius: 5px; height: 320px; overflow-y: auto; font-family: monospace; font-size: 12px; color: #00ff66; }
    </style>
</head>
<body>
<div class="container">
    <h1>🤖 محرك سحب وتنظيف Pure Library (ملف واحد)</h1>
    <div class="card">
        <button class="btn-scrape" id="btnScrape">🚀 بدء السحب الشامل (616 كائن)</button>
        <button class="btn-clean" id="btnClean">🧹 بدء تنظيف المكررات بالكامل</button>
    </div>
    <div class="card">
        <div id="logBox">[SYSTEM] محرك Pure Library جاهز بالكامل...</div>
    </div>
</div>
<script>
  function log(msg) {
      const box = document.getElementById('logBox');
      box.innerHTML += `<br>[${new Date().toLocaleTimeString()}] ${msg}`;
      box.scrollTop = box.scrollHeight;
  }

  async function sendAction(actionType) {
      try {
          log(`⏳ جاري إرسال أمر (${actionType})...`);
          const res = await fetch('/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ action: actionType })
          });
          const data = await res.json();
          log(`✅ استجابة السيرفر: ${data.message}`);
      } catch (err) {
          log(`❌ خطأ بالاتصال: ${err.message}`);
      }
  }

  document.getElementById('btnScrape').addEventListener('click', () => sendAction('start_scraper'));
  document.getElementById('btnClean').addEventListener('click', () => sendAction('clean_duplicates'));
</script>
</body>
</html>
"""


# ==========================================
# 4. السيرفر الموحد
# ==========================================
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):

  daemon_threads = True


class UnifiedHandler(BaseHTTPRequestHandler):

  def _set_cors(self):
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")

  def do_OPTIONS(self):
    self.send_response(200)
    self._set_cors()
    self.end_headers()

  def do_GET(self):
    """إرجاع واجهة التحكم عند فتح الرابط"""
    self.send_response(200)
    self.send_header("Content-Type", "text/html; charset=utf-8")
    self.end_headers()
    self.wfile.write(HTML_INTERFACE.encode("utf-8"))

  def do_POST(self):
    """استقبال الأوامر وتنفيذها بالخلفية"""
    content_length = int(self.headers.get("Content-Length", 0))
    data = json.loads(self.rfile.read(content_length).decode("utf-8"))
    action = data.get("action")

    if action == "start_scraper":
      threading.Thread(target=start_full_archive_scraper).start()
      self.respond({
          "status": "started",
          "message": "تم تشغيل محرك السحب بـ 616 كائن بنجاح!",
      })
    elif action == "clean_duplicates":
      threading.Thread(target=clean_duplicate_manga).start()
      self.respond(
          {"status": "started", "message": "بدأت عملية تنظيف المكررات بالكامل!"}
      )

  def respond(self, res_data):
    self.send_response(200)
    self._set_cors()
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.end_headers()
    self.wfile.write(json.dumps(res_data, ensure_ascii=False).encode("utf-8"))

  def log_message(self, format, *args):
    return


if __name__ == "__main__":
  server = ThreadedHTTPServer(("", PORT), UnifiedHandler)
  print(
      f"🚀 السيرفر الموحد والواجهة تعمل بنجاح على: http://127.0.0.1:{PORT}"
  )
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\n🛑 تم إيقاف السيرفر.")
