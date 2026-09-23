from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import threading
from urllib.parse import quote

from bs4 import BeautifulSoup
import cloudscraper
import firebase_admin
from firebase_admin import credentials, firestore

# ==========================================
# 1. تهيئة الفايربيس والمحرك
# ==========================================
try:
  cred = credentials.Certificate("serviceAccountKey.json")
  firebase_admin.initialize_app(cred)
except Exception as e:
  print(f"⚠️ تنبيه الفايربيس: {e}")

db = firestore.client()
PORT = 8080
BASE_ARCHIVE_URL = "https://azorafly.com/series/"
NUM_WORKERS = 616

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "desktop": True}
)


# ==========================================
# 2. الدوال المساعدة ونظام السحب والتنظيف
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

  # منع التكرار والقفل
  doc_snap = manga_ref.get()
  if doc_snap.exists:
    data = doc_snap.to_dict()
    if data.get("status") in ["completed", "in_progress"]:
      return

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
    rating = soup.select_one("div.num, span.rating, div.rating")
    rating_val = rating.text.strip() if rating else "N/A"

    cover = soup.select_one("div.thumb img, div.summary_image img")
    cover_url = cover.get("src") or cover.get("data-src") if cover else ""

    genres = [
        g.text.strip() for g in soup.select("div.genres-content a, div.mgen a")
    ]

    chapter_links = soup.select(
        'ul.clist li a, div.eplister li a, a[href*="/chapter"]'
    )
    chapters = []
    for a in chapter_links:
      href = a.get("href")
      text = a.text.strip()
      if href and not any(c["url"] == href for c in chapters):
        chapters.append({"title": clean_chapter_name(text), "url": href})

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

    manga_ref.set({
        "rating": rating_val,
        "cover": cover_url,
        "genres": genres,
        "chapters_count": len(chapters),
        "status": "completed",
        "updated_at": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    print(f"✅ تم السحب بنجاح: {manga_title}")

  except Exception as e:
    print(f"❌ خطأ أثناء السحب ({manga_title}): {e}")
    manga_ref.update({"status": "failed"})


def start_full_archive_scraper():
  print("🌐 جاري بدء السحب الشامل والأرشيف كامل...")
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
    all_manga_list.extend({m["href"]: m for m in page_manga}.values())
    page += 1

  print(
      f"📊 تم حصر {len(all_manga_list)} مانهوا. تشغيل المحرك بـ"
      f" {NUM_WORKERS} كائن..."
  )
  with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
    executor.map(process_manga_worker, all_manga_list)


def clean_duplicate_manga():
  print("🧹 جاري تنظيف المكررات بالكامل...")
  manga_docs = db.collection("manga").stream()
  seen_titles = {}
  deleted_count = 0
  for doc in manga_docs:
    title = doc.to_dict().get("title", "")
    norm_title = re.sub(r"[^\w\s]", "", title).strip().lower()
    if norm_title in seen_titles:
      print(f"🗑️ مسح نسخة مكررة: {title}")
      for ch in (
          db.collection("manga")
          .document(doc.id)
          .collection("chapters")
          .stream()
      ):
        ch.reference.delete()
      doc.reference.delete()
      deleted_count += 1
    else:
      if norm_title:
        seen_titles[norm_title] = doc.id
  print(f"✅ اكتمل التنظيف! تم حذف {deleted_count} مانهوا مكررة.")


# ==========================================
# 3. معالج الطلبات (يستقبل من التطبيق)
# ==========================================
class FullProxyHandler(BaseHTTPRequestHandler):

  def _set_cors(self):
    self.send_header("Access-Control-Allow-Origin", "*")
    self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")

  def do_OPTIONS(self):
    self.send_response(200)
    self._set_cors()
    self.end_headers()

  def do_POST(self):
    content_length = int(self.headers.get("Content-Length", 0))
    raw_data = self.rfile.read(content_length).decode("utf-8")

    try:
      data = json.loads(raw_data)
      action = data.get("action")

      if action == "start_scraper":
        threading.Thread(target=start_full_archive_scraper).start()
        msg = "تم بدء السحب الشامل بـ 616 كائن بنجاح!"
      elif action == "clean_duplicates":
        threading.Thread(target=clean_duplicate_manga).start()
        msg = "بدأت عملية تنظيف المكررات بالكامل!"
      else:
        msg = "أمر استجابة مجهول"

      self.send_response(200)
      self._set_cors()
      self.send_header("Content-Type", "application/json; charset=utf-8")
      self.end_headers()
      self.wfile.write(
          json.dumps({"status": "success", "message": msg}, ensure_ascii=False).encode(
              "utf-8"
          )
      )

    except Exception as e:
      self.send_response(500)
      self._set_cors()
      self.end_headers()
      self.wfile.write(
          json.dumps({"status": "error", "message": str(e)}).encode("utf-8")
      )


if __name__ == "__main__":
  server = HTTPServer(("", PORT), FullProxyHandler)
  print(f"🚀 البروكسي الموحد الشامل يعمل بنجاح على المنفذ: {PORT}")
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\n🛑 تم إيقاف البروكسي.")
