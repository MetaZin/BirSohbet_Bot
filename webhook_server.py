from flask import Flask, request, jsonify
import json
from datetime import datetime
from database import set_vip, log_event  # ✅ ekledik

app = Flask(__name__)

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return jsonify({"status": "BirSohbet Webhook çalışıyor ✅"}), 200

    payload = request.data
    try:
        event = json.loads(payload)
    except Exception as e:
        print(f"[{datetime.now()}] ❌ JSON parse hatası:", e)
        return jsonify(success=False), 400

    event_type = event.get("type")
    print(f"[{datetime.now()}] 🎯 Webhook isteği alındı → {event_type}")
    log_event(f"Webhook alındı → {event_type}")

    # Stripe olaylarını işle
    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        customer_id = session.get("client_reference_id", "bilinmiyor")

        print(f"✅ Ödeme başarıyla tamamlandı! Kullanıcı ID: {customer_id}")
        log_event(f"Ödeme tamamlandı → VIP aktif edildi (User: {customer_id})")

        # Eğer client_reference_id varsa VIP yap
        if customer_id != "bilinmiyor":
            try:
                set_vip(int(customer_id))
                print(f"🌟 Kullanıcı {customer_id} VIP olarak işaretlendi!")
                log_event(f"🌟 Kullanıcı {customer_id} otomatik VIP yapıldı")
            except Exception as e:
                print("❌ VIP atama hatası:", e)
                log_event(f"❌ VIP atama hatası: {e}")
        else:
            log_event("⚠️ client_reference_id bulunamadı → VIP atlanıyor")

    else:
        print("ℹ️ Farklı türde bir webhook olayı alındı:", event_type)
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
