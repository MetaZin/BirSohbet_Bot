from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from config import BOT_TOKEN
from database import init_db, register_user, get_user_preferences, log_event
import asyncio
import sqlite3

waiting_users = []
active_chats = {}
pending_registrations = {}

init_db()
ADMIN_IDS = [5469215864]  # senin Telegram ID’in


# 📸 /start — sadece giriş ekranı
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🪪 Kayıt Ol", callback_data="kayit_basla")],
        [InlineKeyboardButton("💖 Destek Ol (Bağış)", url="https://www.buymeacoffee.com/birsohbet")],
        [InlineKeyboardButton("💬 Sohbete Başla", callback_data="sohbet_basla")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "🤖 *BirSohbet'e Hoş Geldin!*\n\n"
        "🕊️ Bu platform tamamen *ücretsiz*, *anonim* ve *güvenli* bir sohbet deneyimi sunar.\n"
        "💬 Yeni insanlarla tanışabilir, gizliliğini koruyarak yazışabilirsin.\n\n"
        "💖 Geliştirilmesine katkı sağlamak istersen bağış yapabilirsin.\n\n"
        "🔒 Kişisel bilgiler toplanmaz ve tüm konuşmalar gizlidir.\n\n"
        "_Lütfen anonim kalmak için özel bilgilerini paylaşma._"
    )

    photo_url = "https://i.imgur.com/HZbQJtW.jpeg"

    try:
        await update.message.reply_photo(
            photo=photo_url,
            caption=welcome_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo_url,
            caption=welcome_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


# 📋 “Kayıt Ol” veya “Sohbete Başla” butonu
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "kayit_basla":
        pending_registrations[user_id] = {"step": "nick"}
        await query.message.reply_text("🪪 Lütfen bir *takma ad (nick)* yaz:")
        log_event(f"Kayıt süreci başladı -> {user_id}")

    elif query.data == "sohbet_basla":
        await sohbet(update, context, from_button=True)


# ✏️ Kayıt süreci
async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in pending_registrations:
        return

    step = pending_registrations[user_id]["step"]

    if step == "nick":
        pending_registrations[user_id]["nick"] = text
        pending_registrations[user_id]["step"] = "gender"
        await update.message.reply_text("👤 Cinsiyetini yaz (erkek / kadın / gey / lezbiyen):")

    elif step == "gender":
        gender = text.lower()
        valid_genders = ["erkek", "kadın", "gey", "lezbiyen"]
        if gender not in valid_genders:
            await update.message.reply_text("⚠️ Geçerli cinsiyetler: erkek, kadın, gey, lezbiyen")
            return
        pending_registrations[user_id]["gender"] = gender
        pending_registrations[user_id]["step"] = "target"
        await update.message.reply_text("🎯 Aradığın cinsiyeti yaz (kadın / erkek / gey / lezbiyen):")

    elif step == "target":
        target = text.lower()
        valid_genders = ["erkek", "kadın", "gey", "lezbiyen"]
        if target not in valid_genders:
            await update.message.reply_text("⚠️ Geçerli cinsiyetler: erkek, kadın, gey, lezbiyen")
            return

        info = pending_registrations[user_id]
        nickname, gender = info["nick"], info["gender"]
        register_user(user_id, nickname, gender, target)
        del pending_registrations[user_id]

        await update.message.reply_text(
            f"✅ Kayıt tamamlandı, {nickname}!\n"
            f"Sen: {gender.capitalize()}, aradığın: {target.capitalize()}\n\n"
            "Artık *💬 Sohbete Başla* butonuna basarak eşleşmeye başlayabilirsin."
        )
        log_event(f"Kayıt tamamlandı -> {user_id} ({gender} arıyor: {target})")


# 💬 Sohbet başlatma
async def sohbet(update: Update, context: ContextTypes.DEFAULT_TYPE, from_button=False):
    if from_button:
        user_id = update.callback_query.from_user.id
    else:
        user_id = update.effective_user.id

    user_gender, target_gender = get_user_preferences(user_id)

    if not user_gender:
        if from_button:
            await context.bot.send_message(chat_id=user_id, text="ℹ️ Önce kayıt olmalısın.")
        else:
            await update.message.reply_text("ℹ️ Önce kayıt olmalısın (/start).")
        return

    if user_id in active_chats:
        msg = "❗ Zaten bir sohbette bulunuyorsun. /next yazabilirsin."
        if from_button:
            await context.bot.send_message(chat_id=user_id, text=msg)
        else:
            await update.message.reply_text(msg)
        return

    # 🎯 Önce tercih eşleşmesi aranır
    for partner_id in waiting_users:
        p_gender, p_target = get_user_preferences(partner_id)
        if p_gender and p_target and p_gender == target_gender and p_target == user_gender:
            waiting_users.remove(partner_id)
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id

            conn = sqlite3.connect("birsohbet.db")
            c = conn.cursor()
            c.execute("SELECT nickname, gender FROM users WHERE user_id=?", (user_id,))
            user_info = c.fetchone()
            c.execute("SELECT nickname, gender FROM users WHERE user_id=?", (partner_id,))
            partner_info = c.fetchone()
            conn.close()

            user_nick, user_g = user_info or ("Bilinmiyor", "?")
            partner_nick, partner_g = partner_info or ("Bilinmiyor", "?")

            await context.bot.send_message(chat_id=user_id, text=f"🎯 {partner_nick} ({partner_g}) ile eşleştirildin 💬")
            await context.bot.send_message(chat_id=partner_id, text=f"🎯 {user_nick} ({user_g}) ile eşleştirildin 💬")
            log_event(f"Eşleşme (tercih) -> {user_id}:{user_nick} <-> {partner_id}:{partner_nick}")
            return

    # ⏳ Bekleme listesi
    waiting_users.append(user_id)
    await context.bot.send_message(chat_id=user_id, text="🔎 Uygun eşleşme aranıyor (1 dakika)...")
    log_event(f"Bekleme -> {user_id} ({user_gender} arıyor: {target_gender})")

    await asyncio.sleep(60)

    if user_id in waiting_users:
        waiting_users.remove(user_id)
        if waiting_users:
            partner_id = waiting_users.pop(0)
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id

            await context.bot.send_message(chat_id=user_id, text="⚡ Kimse bulunamadı, rastgele biriyle eşleştirildin 💬")
            await context.bot.send_message(chat_id=partner_id, text="⚡ Kimse bulunamadı, rastgele biriyle eşleştirildin 💬")
            log_event(f"Eşleşme (rastgele) -> {user_id} <-> {partner_id}")
        else:
            await context.bot.send_message(chat_id=user_id, text="⏳ Şu anda kimse yok. Birazdan tekrar dene.")


# 🔁 /next
async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Karşı taraf sohbeti sonlandırdı.")
        await update.message.reply_text("🔁 Yeni eşleşme aranıyor...")
        await sohbet(update, context)
    else:
        await update.message.reply_text("🔁 Şu anda kimseyle konuşmuyorsun. /start yazabilirsin.")


# 🛑 /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=partner_id, text="❌ Karşı taraf sohbeti bitirdi.")
        await update.message.reply_text("✅ Sohbet sonlandırıldı.")
        log_event(f"Sohbet sonlandırıldı -> {user_id}")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("🚫 Eşleşme beklemesinden çıktın.")
    else:
        await update.message.reply_text("Zaten bir sohbette değilsin.")


# 💬 Mesaj yönlendirme
async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        log_event(f"Mesaj: {user_id} → {partner_id}")


# 🚀 Ana çalışma
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("next", next_chat))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_registration))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay))

    print("🚀 BirSohbet v3.1 (Giriş ekranı + Sohbet butonu) aktif!")
    app.run_polling()


if __name__ == "__main__":
    main()
