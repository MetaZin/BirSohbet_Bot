from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN
from database import init_db, set_vip, is_vip, log_event, get_vip_statuses
import sqlite3
import asyncio
import threading
from datetime import datetime

waiting_users = []
active_chats = {}

init_db()
ADMIN_IDS = [5469215864]  # 👈 kendi Telegram ID’in

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in active_chats:
        await update.message.reply_text("❗ Zaten bir sohbette bulunuyorsun. Yeni eşleşme için /next yaz.")
        return

    if waiting_users and waiting_users[0] != user_id:
        vip_waiters = [u for u in waiting_users if is_vip(u)]
        if vip_waiters:
            partner_id = vip_waiters[0]
            waiting_users.remove(partner_id)
        else:
            partner_id = waiting_users.pop(0)

        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        await context.bot.send_message(chat_id=user_id, text="🎯 Bir kişiyle eşleştirildin! Sohbete başlayabilirsin 💬")
        await context.bot.send_message(chat_id=partner_id, text="🎯 Bir kişiyle eşleştirildin! Sohbete başlayabilirsin 💬")
        log_event(f"User {user_id} eşleşti -> {partner_id}")
    else:
        waiting_users.append(user_id)
        msg = "🌟 VIP kullanıcı olarak öncelikli sıradasın." if is_vip(user_id) else "🔎 Eşleşme bekleniyor..."
        await update.message.reply_text(msg)
        log_event(f"User {user_id} beklemeye alındı")

# /next komutu
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Karşı taraf sohbeti sonlandırdı.")
        await update.message.reply_text("🔁 Yeni eşleşme aranıyor...")
        log_event(f"User {user_id} /next komutu verdi (önceki partner: {partner_id})")
        await start(update, context)
    else:
        await update.message.reply_text("🔁 Şu anda kimseyle konuşmuyorsun. /start yazabilirsin.")

# /stop komutu
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Karşı taraf sohbeti bitirdi.")
        log_event(f"User {user_id} sohbeti sonlandırdı (partner: {partner_id})")
        await update.message.reply_text("✅ Sohbet sonlandırıldı.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        log_event(f"User {user_id} bekleme listesinden çıktı.")
        await update.message.reply_text("🚫 Eşleşme beklemesinden çıktın.")
    else:
        await update.message.reply_text("Zaten bir sohbette değilsin.")

# /vip komutu
from payment import create_checkout_session, confirm_payment

async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_vip(user_id):
        await update.message.reply_text("✅ Zaten aktif bir VIP üyeliğin var 🌟")
        return

    await update.message.reply_text("💳 VIP ödeme bağlantısı hazırlanıyor...")

    payment_url = create_checkout_session(user_id)
    if payment_url:
        await update.message.reply_text(
            f"🌟 Haftalık VIP Üyelik (10 TL)\n\n"
            f"👉 [Stripe üzerinden öde]({payment_url})\n\n"
            "💡 Ödeme tamamlandıktan sonra VIP üyeliğin otomatik aktif olur.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("⚠️ Ödeme bağlantısı oluşturulamadı. Lütfen daha sonra tekrar dene.")

# /makevip komutu (Admin)
async def make_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Bu komutu kullanma yetkin yok.")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Kullanım: /makevip <user_id>")
        return
    target_id = int(context.args[0])
    set_vip(target_id)
    await update.message.reply_text(f"🌟 Kullanıcı {target_id} artık VIP olarak ayarlandı!")
    log_event(f"ADMIN {user_id} kullanıcıyı VIP yaptı -> {target_id}")

# /panel komutu
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Bu komutu kullanma yetkin yok.")
        return

    conn = sqlite3.connect("birsohbet.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE is_vip=1")
    vip_count = c.fetchone()[0]
    conn.close()

    msg = (
        "📊 *BirSohbet Durum Paneli*\n\n"
        f"👥 Aktif sohbetler: {len(active_chats)//2}\n"
        f"🕒 Bekleyen kullanıcılar: {len(waiting_users)}\n"
        f"🌟 VIP üyeler: {vip_count}\n"
        f"📅 Günlük log dosyası: birsohbet.log\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# Mesaj yönlendirme
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        log_event(f"Mesaj: {user_id} → {partner_id}")

# 🔔 Günlük rapor fonksiyonu
async def daily_report_task(app):
    log_event("📊 Günlük rapor sistemi başlatıldı...")
    await app.bot.send_message(chat_id=ADMIN_IDS[0], text="⏳ Günlük rapor sistemi başlatıldı...")

    while True:
        now = datetime.now()
        if now.hour == 5 and now.minute == 0:  # Her akşam 20:00
            vip_statuses = get_vip_statuses()
            expiring = [uid for uid, days in vip_statuses if 0 <= days <= 1]

            msg = (
                "📅 *Günlük BirSohbet Özeti*\n\n"
                f"👥 Aktif sohbetler: {len(active_chats)//2}\n"
                f"🕒 Bekleyen kullanıcılar: {len(waiting_users)}\n"
                f"🌟 VIP üyeler: {len(vip_statuses)}\n"
                f"⚠️ Süresi dolmak üzere: {len(expiring)}\n\n"
                "🗂️ Log dosyası: birsohbet.log"
            )

            log_event("📊 Günlük rapor oluşturuldu:\n" + msg.replace("\n", " | "))
            await app.bot.send_message(chat_id=ADMIN_IDS[0], text=msg, parse_mode="Markdown")

            await asyncio.sleep(60)
        await asyncio.sleep(60)


# 🔹 Arka plan thread başlatıcı
def start_background_tasks():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(daily_report_task(app))
    loop.run_forever()

# ✅ Hatasız main fonksiyonu
def main():
    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("vip", vip))
    app.add_handler(CommandHandler("makevip", make_vip))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay))

    print("🚀 BirSohbet Günlük Rapor Sistemi aktif!")

    # 🔹 Günlük rapor sistemi ayrı thread’de çalışacak
    threading.Thread(target=start_background_tasks, daemon=True).start()

    # 🔹 Telegram botu başlat
    app.run_polling()

if __name__ == "__main__":
    main()
