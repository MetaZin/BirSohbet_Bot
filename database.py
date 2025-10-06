import sqlite3
from datetime import datetime, timedelta
import os

# 📁 Veritabanı ve log yolları
DB_NAME = os.path.join(os.path.dirname(__file__), "birsohbet.db")

# Masaüstüne otomatik log kaydı
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "BirSohbet_Loglar")
os.makedirs(DESKTOP_PATH, exist_ok=True)

def _get_log_path():
    """Her gün için ayrı log dosyası üretir."""
    tarih = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(DESKTOP_PATH, f"BirSohbet_Log_{tarih}.txt")


# 🧱 Veritabanı başlatma
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    is_vip INTEGER DEFAULT 0,
                    vip_until TEXT
                )''')
    conn.commit()
    conn.close()


# 🌟 VIP üyelik ekleme / yenileme
def set_vip(user_id, days=7):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    vip_until = datetime.now() + timedelta(days=days)
    c.execute("""
        INSERT OR REPLACE INTO users (user_id, is_vip, vip_until)
        VALUES (?, ?, ?)
    """, (user_id, 1, vip_until.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    log_event(f"🌟 VIP aktif edildi -> {user_id} ({days} gün)")


# 🔍 VIP durumu kontrolü
def is_vip(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT is_vip, vip_until FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return False

    active, vip_until = row
    if active == 1 and vip_until:
        expire_date = datetime.strptime(vip_until, "%Y-%m-%d %H:%M:%S")
        return expire_date > datetime.now()

    return False


# 🧾 Gelişmiş log kaydı (UTF-8, günlük dosya)
def log_event(text):
    try:
        log_path = _get_log_path()
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        line = f"{timestamp} {text}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)

    except Exception as e:
        print(f"[LOG HATASI] {e}")
        # Yedek olarak ana klasöre kaydet
        try:
            fallback_path = os.path.join(os.path.dirname(__file__), "birsohbet_fallback.log")
            with open(fallback_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] Log kaydedilemedi: {e}\n")
        except:
            pass


# 📅 VIP kalan günleri hesapla
def get_vip_statuses():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, vip_until FROM users WHERE is_vip=1")
    rows = c.fetchall()
    conn.close()

    results = []
    for uid, vip_until in rows:
        if not vip_until:
            continue
        try:
            expire_date = datetime.strptime(vip_until, "%Y-%m-%d %H:%M:%S")
            days_left = (expire_date - datetime.now()).days
            results.append((uid, days_left))
        except Exception as e:
            log_event(f"⚠️ VIP hesaplama hatası -> {uid}: {e}")

    return results
