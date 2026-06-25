import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://seyedalimoosavi369.github.io/-Minerbyner_bot")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8030373785"))
API = os.environ.get("API_URL", "https://web-production-aa8bad.up.railway.app")
CHANNEL = "@minerbyner_bot_chanel"

async def check_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_member = await check_membership(context.bot, user.id)
    if not is_member:
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/minerbyner_bot_chanel")],
            [InlineKeyboardButton("✅ I Joined", callback_data="check_membership")]
        ]
        await update.message.reply_text(
            "⚠️ To play MINER PRO, you must first join our channel!\n\n"
            "1️⃣ Join the channel below\n"
            "2️⃣ Come back and press ✅ I Joined",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    ref = context.args[0] if context.args else ""
    url = f"{WEBAPP_URL}?ref={ref}" if ref else WEBAPP_URL
    keyboard = [[InlineKeyboardButton("⚡ Play MINER PRO", web_app=WebAppInfo(url=url))]]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin.html"))])
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n⚡ <b>MINER PRO</b>\nMine TRX, buy upgrades, earn TON!\n\nPress the button to start:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check_membership":
        is_member = await check_membership(context.bot, query.from_user.id)
        if is_member:
            user = query.from_user
            url = WEBAPP_URL
            keyboard = [[InlineKeyboardButton("⚡ Play MINER PRO", web_app=WebAppInfo(url=url))]]
            if user.id == ADMIN_ID:
                keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin.html"))])
            await query.edit_message_text(
                f"👋 Welcome {user.first_name}!\n\n⚡ <b>MINER PRO</b>\nMine TRX, buy upgrades, earn TON!\n\nPress the button to start:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.answer("❌ You haven't joined the channel yet!", show_alert=True)

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start={user.id}"
    await update.message.reply_text(f"🔗 Your referral link:\n\n`{link}`", parse_mode="Markdown")

async def whitepaper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""📄 MINER PRO — Whitepaper

💡 Overview:
MINER PRO is a Telegram play-to-earn mining game on the TON ecosystem.

💰 Tokenomics:
• TRX: In-game currency (start: 1M TRX)
• TON: Real asset earned via miners

⛏️ Mining:
Tap to earn TRX + buy 12 items to boost hashrate.

💎 Investment Miners:
• Hyper-Core: 100 TON → 0.555 TON/day
• Nova Reactor: 1,000 TON → 5.55 TON/day
• Stellar Forge: 10,000 TON → 55.5 TON/day
• Quantum: 100,000 TON → 555 TON/day""")

async def roadmap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""🗺️ MINER PRO — Roadmap

✅ Phase 1 — Launch (Done)
🔄 Phase 2 — Growth (Now)
🔜 Phase 3 — Expansion (Q3 2026)
🚀 Phase 4 — Ecosystem (Q4 2026)
🌐 Phase 5 — Scale (2027)

@Minerbyner_bot — Mine. Invest. Earn. 🚀""")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>\n\n"
        "/reward [user_id] [trx] [ton]\n"
        "/broadcast [message]\n"
        "/stats\n"
        "/users",
        parse_mode="HTML"
    )

async def reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reward [user_id] [trx] [ton]")
        return
    try:
        uid = int(context.args[0])
        trx = float(context.args[1])
        ton = float(context.args[2]) if len(context.args) > 2 else 0
        r = requests.post(f"{API}/api/admin/reward_bot",
                         json={"user_id": uid, "trx": trx, "ton": ton, "admin_id": ADMIN_ID})
        data = r.json()
        if data.get("success"):
            await update.message.reply_text(f"✅ Sent!\nUser: {uid}\nTRX: {trx:,.0f}\nTON: {ton}")
        else:
            await update.message.reply_text(f"❌ {data.get('error')}")
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast [message]")
        return
    msg = " ".join(context.args)
    r = requests.post(f"{API}/api/admin/broadcast",
                     json={"admin_id": ADMIN_ID, "message": msg})
    data = r.json()
    await update.message.reply_text(f"✅ Sent: {data.get('sent')} | Failed: {data.get('failed')}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return
    r = requests.get(f"{API}/api/admin/stats_bot", params={"admin_id": ADMIN_ID})
    data = r.json()
    await update.message.reply_text(
        f"📊 <b>Stats</b>\n\n"
        f"👥 Users: {data.get('total_users', 0)}\n"
        f"💸 Pending: {data.get('pending_withdrawals', 0)}\n"
        f"💰 Total TRX: {data.get('total_trx', 0):,.0f}",
        parse_mode="HTML"
    )

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return
    r = requests.get(f"{API}/api/admin/users_bot", params={"admin_id": ADMIN_ID})
    data = r.json()
    msg = "👥 <b>Recent Users</b>\n\n"
    for u in data.get("users", [])[:20]:
        msg += f"ID: <code>{u['user_id']}</code> | {u['first_name']} | {u['balance']:,.0f} TRX\n"
    await update.message.reply_text(msg, parse_mode="HTML")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ref", referral))
    app.add_handler(CommandHandler("whitepaper", whitepaper))
    app.add_handler(CommandHandler("roadmap", roadmap_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("reward", reward))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling(close_loop=False)
