from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import time
import hmac
import hashlib
import json
import requests
from functools import wraps

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8935584033:AAGD6ICE5g0C5GPRAodt5XhK0gQlHUAd6jU")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8030373785"))
TON_WALLET = os.environ.get("TON_WALLET", "UQCs20TzgI5bmr5TJo3PigiEn0DMJhWktPOw7bo27K2FVZwI")
DB_PATH = os.environ.get("DB_PATH", "/data/minerbyner.db")

ITEMS = [
    {"id": 1, "name": "Basic Core", "price": 1000, "boost": 5},
    {"id": 2, "name": "Quantum Rig", "price": 2000, "boost": 12},
    {"id": 3, "name": "Nebula Core", "price": 4000, "boost": 25},
    {"id": 4, "name": "Nano Miner", "price": 8000, "boost": 45},
    {"id": 5, "name": "Ion Reactor", "price": 16000, "boost": 80},
    {"id": 6, "name": "Dark Plasma", "price": 32000, "boost": 150},
    {"id": 7, "name": "Void Engine", "price": 64000, "boost": 300},
    {"id": 8, "name": "Gravity Drill", "price": 128000, "boost": 600},
    {"id": 9, "name": "Star Forge", "price": 256000, "boost": 1200},
    {"id": 10, "name": "Cyber Node", "price": 512000, "boost": 2500},
    {"id": 11, "name": "Nova Matrix", "price": 1000000, "boost": 5000},
    {"id": 12, "name": "God Engine", "price": 2000000, "boost": 10000},
]

COMMISSION_LEVELS = [0.10, 0.05, 0.03, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01]

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance REAL DEFAULT 1000000,
            ton_balance REAL DEFAULT 5,
            referrer_id INTEGER DEFAULT NULL,
            last_mine_time REAL DEFAULT 0,
            created_at REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id INTEGER,
            level INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_id)
        );
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            wallet TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS ton_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tx_hash TEXT UNIQUE,
            amount REAL,
            created_at REAL
        );
    """)
    conn.commit()
    conn.close()

def verify_telegram_data(init_data):
    if not init_data:
        return None
    try:
        parsed = {}
        for part in init_data.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                parsed[k] = v
        received_hash = parsed.pop("hash", "")
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(received_hash, expected):
            user_str = parsed.get("user", "{}")
            from urllib.parse import unquote
            return json.loads(unquote(user_str))
        return None
    except Exception:
        return None

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        init_data = request.headers.get("X-Init-Data", "")
        user = verify_telegram_data(init_data)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        return f(user, *args, **kwargs)
    return decorated

def get_user(conn, user_id):
    return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

def get_inventory(conn, user_id):
    rows = conn.execute("SELECT item_id, level FROM inventory WHERE user_id=?", (user_id,)).fetchall()
    return {str(r["item_id"]): r["level"] for r in rows}

def calc_hashrate(inventory):
    total = 0
    for item in ITEMS:
        level = inventory.get(str(item["id"]), 0)
        total += item["boost"] * level
    return total

def apply_mine(conn, user_id):
    user = get_user(conn, user_id)
    now = time.time()
    elapsed = min(now - user["last_mine_time"], 3600 * 8)
    inventory = get_inventory(conn, user_id)
    hashrate = calc_hashrate(inventory)
    earned = hashrate * elapsed / 10
    if earned > 0:
        conn.execute("UPDATE users SET balance=balance+?, last_mine_time=? WHERE user_id=?", (earned, now, user_id))
    else:
        conn.execute("UPDATE users SET last_mine_time=? WHERE user_id=?", (now, user_id))
    return earned

def pay_referral_commission(conn, buyer_id, amount):
    user = get_user(conn, buyer_id)
    ref_id = user["referrer_id"]
    level = 0
    while ref_id and level < 10:
        rate = COMMISSION_LEVELS[level]
        commission = amount * rate
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (commission, ref_id))
        ref = get_user(conn, ref_id)
        if not ref:
            break
        ref_id = ref["referrer_id"]
        level += 1

@app.route("/api/user", methods=["POST"])
@auth_required
def register_or_get_user(tg_user):
    data = request.json or {}
    referrer_id = data.get("ref")
    conn = get_db()
    user = get_user(conn, tg_user["id"])
    if not user:
        conn.execute(
            "INSERT INTO users (user_id, username, first_name, balance, ton_balance, last_mine_time, created_at) VALUES (?,?,?,?,?,?,?)",
            (tg_user["id"], tg_user.get("username", ""), tg_user.get("first_name", ""), 1000000, 5, time.time(), time.time())
        )
        if referrer_id:
            try:
                rid = int(referrer_id)
                if rid != tg_user["id"]:
                    ref = get_user(conn, rid)
                    if ref:
                        conn.execute("UPDATE users SET referrer_id=? WHERE user_id=?", (rid, tg_user["id"]))
            except:
                pass
        conn.commit()
    apply_mine(conn, tg_user["id"])
    conn.commit()
    user = get_user(conn, tg_user["id"])
    inventory = get_inventory(conn, tg_user["id"])
    hashrate = calc_hashrate(inventory)
    result = {
        "user_id": user["user_id"],
        "first_name": user["first_name"],
        "balance": user["balance"],
        "ton_balance": user["ton_balance"],
        "inventory": inventory,
        "hashrate": hashrate,
    }
    conn.close()
    return jsonify(result)

@app.route("/api/click", methods=["POST"])
@auth_required
def click(tg_user):
    conn = get_db()
    inventory = get_inventory(conn, tg_user["id"])
    bonus = 1 + sum(inventory.values())
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (bonus, tg_user["id"]))
    conn.commit()
    user = get_user(conn, tg_user["id"])
    conn.close()
    return jsonify({"balance": user["balance"]})

@app.route("/api/buy", methods=["POST"])
@auth_required
def buy(tg_user):
    import math
    data = request.json or {}
    item_id = int(data.get("item_id", 0))
    item = next((i for i in ITEMS if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    conn = get_db()
    apply_mine(conn, tg_user["id"])
    inventory = get_inventory(conn, tg_user["id"])
    level = inventory.get(str(item_id), 0)
    user = get_user(conn, tg_user["id"])
    if level < 10:
        cost = math.floor(item["price"] * (1.5 ** level))
        if user["balance"] < cost:
            conn.close()
            return jsonify({"error": "Insufficient TRX"}), 400
        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (cost, tg_user["id"]))
        pay_referral_commission(conn, tg_user["id"], cost)
    else:
        if user["ton_balance"] < 1:
            conn.close()
            return jsonify({"error": "Insufficient TON"}), 400
        conn.execute("UPDATE users SET ton_balance=ton_balance-1 WHERE user_id=?", (tg_user["id"],))
        pay_referral_commission(conn, tg_user["id"], 1000000)
    new_level = level + 1
    conn.execute(
        "INSERT INTO inventory (user_id, item_id, level) VALUES (?,?,?) ON CONFLICT(user_id,item_id) DO UPDATE SET level=?",
        (tg_user["id"], item_id, new_level, new_level)
    )
    conn.commit()
    user = get_user(conn, tg_user["id"])
    inventory = get_inventory(conn, tg_user["id"])
    conn.close()
    return jsonify({"balance": user["balance"], "ton_balance": user["ton_balance"], "inventory": inventory})

@app.route("/api/convert", methods=["POST"])
@auth_required
def convert(tg_user):
    data = request.json or {}
    direction = data.get("direction")
    conn = get_db()
    user = get_user(conn, tg_user["id"])
    if direction == "trx_to_ton":
        if user["balance"] < 1000000:
            conn.close()
            return jsonify({"error": "Need 1,000,000 TRX"}), 400
        conn.execute("UPDATE users SET balance=balance-1000000, ton_balance=ton_balance+1 WHERE user_id=?", (tg_user["id"],))
    elif direction == "ton_to_trx":
        if user["ton_balance"] < 1:
            conn.close()
            return jsonify({"error": "Need 1 TON"}), 400
        conn.execute("UPDATE users SET balance=balance+1000000, ton_balance=ton_balance-1 WHERE user_id=?", (tg_user["id"],))
    else:
        conn.close()
        return jsonify({"error": "Invalid direction"}), 400
    conn.commit()
    user = get_user(conn, tg_user["id"])
    conn.close()
    return jsonify({"balance": user["balance"], "ton_balance": user["ton_balance"]})

@app.route("/api/withdraw", methods=["POST"])
@auth_required
def withdraw(tg_user):
    data = request.json or {}
    amount = float(data.get("amount", 0))
    wallet = data.get("wallet", "")
    if amount < 10:
        return jsonify({"error": "Minimum withdrawal is 10 TON"}), 400
    if not wallet:
        return jsonify({"error": "Wallet address required"}), 400
    conn = get_db()
    user = get_user(conn, tg_user["id"])
    if user["ton_balance"] < amount:
        conn.close()
        return jsonify({"error": "Insufficient TON"}), 400
    conn.execute("UPDATE users SET ton_balance=ton_balance-? WHERE user_id=?", (amount, tg_user["id"]))
    conn.execute(
        "INSERT INTO withdrawals (user_id, amount, wallet, created_at) VALUES (?,?,?,?)",
        (tg_user["id"], amount, wallet, time.time())
    )
    conn.commit()
    try:
        msg = f"💸 Withdrawal Request\nUser: {tg_user['id']}\nAmount: {amount} TON\nWallet: {wallet}"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": ADMIN_ID, "text": msg})
    except:
        pass
    conn.close()
    return jsonify({"success": True})

@app.route("/api/verify_ton", methods=["POST"])
@auth_required
def verify_ton(tg_user):
    data = request.json or {}
    tx_hash = data.get("tx_hash", "")
    if not tx_hash:
        return jsonify({"error": "tx_hash required"}), 400
    conn = get_db()
    existing = conn.execute("SELECT * FROM ton_deposits WHERE tx_hash=?", (tx_hash,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Already processed"}), 400
    try:
        r = requests.get(f"https://toncenter.com/api/v2/getTransaction?hash={tx_hash}", timeout=10)
        tx = r.json()
        if not tx.get("ok"):
            conn.close()
            return jsonify({"error": "Transaction not found"}), 400
        result = tx["result"]
        to_addr = result.get("in_msg", {}).get("destination", "")
        amount_ton = int(result.get("in_msg", {}).get("value", 0)) / 1e9
        if TON_WALLET not in to_addr:
            conn.close()
            return jsonify({"error": "Wrong destination"}), 400
        if amount_ton < 0.1:
            conn.close()
            return jsonify({"error": "Amount too small"}), 400
        conn.execute("INSERT INTO ton_deposits (user_id, tx_hash, amount, created_at) VALUES (?,?,?,?)",
                     (tg_user["id"], tx_hash, amount_ton, time.time()))
        conn.execute("UPDATE users SET ton_balance=ton_balance+? WHERE user_id=?", (amount_ton, tg_user["id"]))
        conn.commit()
        user = get_user(conn, tg_user["id"])
        conn.close()
        return jsonify({"success": True, "amount": amount_ton, "ton_balance": user["ton_balance"]})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route("/api/team", methods=["GET"])
@auth_required
def team(tg_user):
    conn = get_db()
    referrals = conn.execute(
        "SELECT user_id, first_name, username, balance FROM users WHERE referrer_id=?",
        (tg_user["id"],)
    ).fetchall()
    result = [{"user_id": r["user_id"], "first_name": r["first_name"],
               "username": r["username"], "balance": r["balance"]} for r in referrals]
    conn.close()
    return jsonify({"referrals": result, "count": len(result)})

@app.route("/api/leaderboard", methods=["GET"])
@auth_required
def leaderboard(tg_user):
    conn = get_db()
    top = conn.execute(
        "SELECT user_id, first_name, username, balance FROM users ORDER BY balance DESC LIMIT 50"
    ).fetchall()
    result = [{"user_id": r["user_id"], "first_name": r["first_name"],
               "username": r["username"], "balance": r["balance"]} for r in top]
    conn.close()
    return jsonify({"leaderboard": result})

@app.route("/api/admin/withdrawals", methods=["GET"])
def admin_withdrawals():
    init_data = request.headers.get("X-Init-Data", "")
    user = verify_telegram_data(init_data)
    if not user or user["id"] != ADMIN_ID:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    rows = conn.execute("SELECT * FROM withdrawals WHERE status='pending' ORDER BY created_at DESC").fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return jsonify({"withdrawals": result})

@app.route("/api/admin/approve/<int:wid>", methods=["POST"])
def admin_approve(wid):
    init_data = request.headers.get("X-Init-Data", "")
    user = verify_telegram_data(init_data)
    if not user or user["id"] != ADMIN_ID:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    conn.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (wid,))
    conn.commit()
    w = conn.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)).fetchone()
    conn.close()
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": w["user_id"], "text": f"✅ Your withdrawal of {w['amount']} TON has been approved!"})
    except:
        pass
    return jsonify({"success": True})

@app.route("/api/admin/reject/<int:wid>", methods=["POST"])
def admin_reject(wid):
    init_data = request.headers.get("X-Init-Data", "")
    user = verify_telegram_data(init_data)
    if not user or user["id"] != ADMIN_ID:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    w = conn.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)).fetchone()
    conn.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (wid,))
    conn.execute("UPDATE users SET ton_balance=ton_balance+? WHERE user_id=?", (w["amount"], w["user_id"]))
    conn.commit()
    conn.close()
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": w["user_id"], "text": f"❌ Your withdrawal of {w['amount']} TON was rejected. Balance returned."})
    except:
        pass
    return jsonify({"success": True})

@app.route("/")
def index():
    return jsonify({"status": "Minerbyner API running"})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
