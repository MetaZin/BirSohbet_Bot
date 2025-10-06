import stripe

# 🧠 Stripe gizli anahtarını buraya doğrudan yaz (test modunu kullan!)
# Örnek: sk_test_51ABCDEFxxxxx
STRIPE_SECRET_KEY = "whsec_GboKrzXA2Pz2t5Z21DRBAZYa9RbORZ0W"  # 👈 kendi test anahtarını buraya yapıştır

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(user_id):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "BirSohbet Bağış"},
                    "unit_amount": 500,  # 5 USD (500 cent)
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url="https://t.me/BirSohbetBot?start=success",
            cancel_url="https://t.me/BirSohbetBot?start=cancel",
            metadata={"user_id": user_id}
        )
        print(f"✅ Stripe session oluşturuldu: {session.url}")
        return session.url

    except Exception as e:
        print(f"❌ [Stripe Hatası]: {e}")
        return None
