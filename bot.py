import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://seyedalimoosavi369.github.io/-Minerbyner_bot")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8030373785"))
API = os.environ.get("API_URL", "https://web-production-aa8bad.up.railway.app")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start={user.id}"
    await update.message.reply_text(f"🔗 Your referral link:\n\n`{link}`", parse_mode="Markdown")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return
    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>\n\n"
        "Commands:\n"
        "/reward [user_id] [trx] [ton]\n"
        "Example: /reward 123456789 10000000 5\n\n"
        "/stats - Show bot stats\n"
        "/users - Show recent users",
        parse_mode="HTML"
    )

async def reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /reward [user_id] [trx] [ton]\nExample: /reward 123456789 10000000 5")
        return
    try:
        uid = int(context.args[0])
        trx = float(context.args[1])
        ton = float(context.args[2]) if len(context.args) > 2 else 0
        r = requests.post(f"{API}/api/admin/reward_bot",
                         json={"user_id": uid, "trx": trx, "ton": ton, "admin_id": ADMIN_ID})
        data = r.json()
        if data.get("success"):
            await update.message.reply_text(
                f"✅ Reward sent!\n"
                f"User: {uid}\n"
                f"TRX: {trx:,.0f}\n"
                f"TON: {ton}\n"
                f"New balance: {data['new_balance']:,.0f} TRX | {data['new_ton']} TON"
            )
        else:
            await update.message.reply_text(f"❌ Error: {data.get('error')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return
    r = requests.get(f"{API}/api/admin/stats_bot", params={"admin_id": ADMIN_ID})
    data = r.json()
    await update.message.reply_text(
        f"📊 <b>Bot Stats</b>\n\n"
        f"👥 Total Users: {data.get('total_users', 0)}\n"
        f"💸 Pending Withdrawals: {data.get('pending_withdrawals', 0)}\n"
        f"💰 Total TRX in game: {data.get('total_trx', 0):,.0f}",
        parse_mode="HTML"
    )

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("reward", reward))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("users", users))
    app.run_polling(close_loop=False)
