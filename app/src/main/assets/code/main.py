import json
import urllib.request

# ضع هنا رابط أو IP سيرفر البروكسي مالتك
PROXY_URL = "http://YOUR_SERVER_IP:8080"


def send_action(action_name):
  payload = json.dumps({"action": action_name}).encode("utf-8")
  req = urllib.request.Request(
      PROXY_URL,
      data=payload,
      headers={"Content-Type": "application/json"},
      method="POST",
  )
  try:
    with urllib.request.urlopen(req, timeout=10) as response:
      res_data = json.loads(response.read().decode("utf-8"))
      print(f"✅ استجابة البروكسي: {res_data.get('message')}")
  except Exception as e:
    print(f"❌ خطأ بالاتصال بالبروكسي: {e}")


if __name__ == "__main__":
  print("=== تطبيق السحب والتحكم ===")
  print("1. بدء السحب الشامل (616 كائن)")
  print("2. بدء تنظيف المكررات بالكامل")

  cmd = input("اختر رقم الأمر (1 أو 2): ").strip()

  if cmd == "1":
    send_action("start_scraper")
  elif cmd == "2":
    send_action("clean_duplicates")
  else:
    print("أمر غير معروف!")
