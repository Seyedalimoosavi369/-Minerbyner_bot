import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://seyedalimoosavi369.github.io/-Minerbyner_bot")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8030373785"))
API = os.environ.get("API_URL", "https://web-production-aa8bad.up.railway.app")

WHITEPAPER = """📄 MINER PRO — Whitepaper

💡 Overview:
MINER PRO is a Telegram play-to-earn mining game on the TON ecosystem. Mine TRX, build networks, invest in miners.

💰 Tokenomics:
• TRX: In-game currency (start: 1M TRX)
• TON: Real asset earned via miners
• Rate: 100M TRX = 1 TON

⛏️ Mining:
Tap to earn TRX + buy 12 items to boost hashrate. Each level doubles in price.

🌲 Binary Network:
• Level 1 ref: 10% commission
• Level 2: 1% | Level 3: 0.1% ...
• Milestones: up to 100M TRX + 1 TON

💎 Investment Miners:
• Hyper-Core: 100 TON → 0.555 TON/day
• Nova Reactor: 1,000 TON → 5.55 TON/day
• Stellar Forge: 10,000 TON → 55.5 TON/day
• Quantum: 100,000 TON → 555 TON/day

All miners return full investment in 6 months.

🔐 Security:
• Telegram WebApp auth on all API calls
• Manual withdrawal approval by admin
• Transparent on-chain TON transactions"""

ROADMAP = """🗺️ MINER PRO — Roadmap

✅ Phase 1 — Launch (Done)
• Telegram Mini-App
• 12-item shop + upgrade system
• Binary referral network
• Hashrate leaderboard
• TON wallet integration
• Admin panel

🔄 Phase 2 — Growth (Now)
• 4-tier investment miners
• Daily TON yield automation
• Network milestone rewards
• Multi-level commissions
• User acquisition campaign

🔜 Phase 3 — Expansion (Q3 2026)
• PvP mining battles
• Weekly tournaments
• Clan/team system
• Achievement badges
• Referral leaderboard

🚀 Phase 4 — Ecosystem (Q4 2026)
• NFT miner skins on TON
• On-chain TRX token launch
• DEX listing
• DAO governance
• Mobile app (iOS & Android)

🌐 Phase 5 — Scale (2027)
• Multi-language support
• Real TRX (Tron) integration
• TON ecosystem partnerships
• Global marketing campaign

@Minerbyner_bot — Mine. Invest. Earn. 🚀"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = context.args[0] if context.args else ""
    url = f"{WEBAPP_URL}?ref={ref}" if ref else WEBAPP_URL
    keyboard = [[InlineKeyboardButton("⚡ Play MINER PRO", web_app=WebAppInfo(url=url))]]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin.html"))])
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "⚡ <b>MINER PRO</b>\n"
        "Mine TRX, buy upgrades, earn TON!\n\n"
        "Press the button to start:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start={user.id}"
    await update.message.reply_text(f"🔗 Your referral link:\n\n`{link}`", parse_mode="Markdown")

async def whitepaper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WHITEPAPER)

async def roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(ROADMAP)

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
    app.add_handler(CommandHandler("whitepaper", whitepaper))
    app.add_handler(CommandHandler("roadmap", roadmap))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("reward", reward))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("users", users))
    app.run_polling(close_loop=False)
