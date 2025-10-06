# payment.py
import stripe
import time
from database import set_vip, log_event

stripe.api_key = "sk_test_51NRKXaEXAMPLEKEYKENDİNDEĞİŞTİR"

BASE_URL = "https://birsohbet.vip"

def create_checkout_session(user_id):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "try",
                    "product_data": {"name": "BirSohbet VIP Üyelik"},
                    "unit_amount": 1000,  # 10 TL
                },
                "quantity": 1,
            }],
            mode="payment",
           success_url=f"https://birsohbet.vip/success/{user_id}",
           cancel_url=f"https://birsohbet.vip/cancel/{user_id}",

        )
        log_event(f"Stripe ödeme linki oluşturuldu -> {user_id}")
        return session.url
    except Exception as e:
        log_event(f"Stripe hata -> {e}")
        return None


def confirm_payment(user_id):
    """Test için otomatik VIP onayı"""
    time.sleep(1)
    set_vip(user_id)
    log_event(f"VIP üyelik onaylandı -> {user_id}")
    return True
