import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8935584033:AAGD6ICE5g0C5GPRAodt5XhK0gQlHUAd6jU")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://seyedalimoosavi369.github.io/-Minerbyner_bot")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = context.args[0] if context.args else ""
    url = f"{WEBAPP_URL}?ref={ref}" if ref else WEBAPP_URL
    keyboard = [[InlineKeyboardButton("⚡ Play MINER PRO", web_app=WebAppInfo(url=url))]]
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

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ref", referral))
    app.run_polling(close_loop=False)
