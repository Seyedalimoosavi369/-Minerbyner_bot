import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8935584033:AAGD6ICE5g0C5GPRAodt5XhK0gQlHUAd6jU")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://seyedalimoosavi369.github.io/-Minerbyner_bot")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8030373785"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = context.args[0] if context.args else ""
    url = f"{WEBAPP_URL}?ref={ref}" if ref else WEBAPP_URL
    keyboard = [[InlineKeyboardButton("⚡ Play MINER PRO", web_app=WebAppInfo(url=url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "⚡ <b>MINER PRO</b>\n"
        "Mine TRX, buy upgrades, earn TON!\n\n"
        "Press the button to start:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start={user.id}"
    await update.message.reply_text(
        f"🔗 Your referral link:\n\n`{link}`\n\n"
        "Share this link and earn commission from your team's purchases!",
        parse_mode="Markdown"
    )

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ref", referral))
    await app.run_polling()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
