import math
import time
from flask import Blueprint, request, jsonify
from db import get_db, get_user, get_inventory
from auth import auth_required
from routes.user import calc_hashrate, apply_mine, pay_commission

shop_bp = Blueprint('shop', __name__)

ITEMS = [
    {"id": 1,  "name": "Basic Core",    "price": 100000,    "boost": 5},
    {"id": 2,  "name": "Quantum Rig",   "price": 200000,    "boost": 12},
    {"id": 3,  "name": "Nebula Core",   "price": 400000,    "boost": 25},
    {"id": 4,  "name": "Nano Miner",    "price": 800000,    "boost": 45},
    {"id": 5,  "name": "Ion Reactor",   "price": 1600000,   "boost": 80},
    {"id": 6,  "name": "Dark Plasma",   "price": 3200000,   "boost": 150},
    {"id": 7,  "name": "Void Engine",   "price": 6400000,   "boost": 300},
    {"id": 8,  "name": "Gravity Drill", "price": 12800000,  "boost": 600},
    {"id": 9,  "name": "Star Forge",    "price": 25600000,  "boost": 1200},
    {"id": 10, "name": "Cyber Node",    "price": 51200000,  "boost": 2500},
    {"id": 11, "name": "Nova Matrix",   "price": 102400000, "boost": 5000},
    {"id": 12, "name": "God Engine",    "price": 204800000, "boost": 10000},
]

MINERS = [
    {"id": "hyper",    "name": "Hyper-Core Node",       "price": 100,    "daily": 100/180,    "duration": 180},
    {"id": "nova",     "name": "Nova Reactor",           "price": 1000,   "daily": 1000/180,   "duration": 180},
    {"id": "stellar",  "name": "Stellar Forge",          "price": 10000,  "daily": 10000/180,  "duration": 180},
    {"id": "quantum",  "name": "Quantum Singularity",    "price": 100000, "daily": 100000/180, "duration": 180},
]

def get_miner(miner_id):
    return next((m for m in MINERS if m["id"] == miner_id), None)

@shop_bp.route("/api/buy", methods=["POST"])
@auth_required
def api_buy(tg):
    data = request.json or {}
    item_id = int(data.get("item_id", 0))
    item = next((i for i in ITEMS if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    conn = get_db()
    apply_mine(conn, tg["id"])
    inv = get_inventory(conn, tg["id"])
    level = inv.get(str(item_id), 0)
    user = get_user(conn, tg["id"])
    if level < 10:
        cost = item["price"] * (2 ** level)
        if user["balance"] < cost:
            conn.close()
            return jsonify({"error": "Insufficient TRX"}), 400
        conn.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (cost, tg["id"]))
        pay_commission(conn, tg["id"], cost)
    else:
        ton_cost = 2 ** (level - 10) if level > 10 else 1
        if user["ton_balance"] < ton_cost:
            conn.close()
            return jsonify({"error": "Insufficient TON"}), 400
        conn.execute("UPDATE users SET ton_balance=ton_balance-? WHERE user_id=?", (ton_cost, tg["id"]))
        pay_commission(conn, tg["id"], ton_cost * 100_000_000)
    new_level = level + 1
    conn.execute(
        "INSERT INTO inventory (user_id, item_id, level) VALUES (?,?,?) ON CONFLICT(user_id,item_id) DO UPDATE SET level=?",
        (tg["id"], item_id, new_level, new_level)
    )
    conn.commit()
    user = get_user(conn, tg["id"])
    inv = get_inventory(conn, tg["id"])
    conn.close()
    return jsonify({
        "balance": user["balance"],
        "ton_balance": user["ton_balance"],
        "inventory": inv,
        "hashrate": calc_hashrate(inv)
    })

@shop_bp.route("/api/buy_miner", methods=["POST"])
@auth_required
def buy_miner(tg):
    data = request.json or {}
    miner_id = data.get("miner_id", "")
    miner = get_miner(miner_id)
    if not miner:
        return jsonify({"error": "Miner not found"}), 404
    conn = get_db()
    apply_mine(conn, tg["id"])
    user = get_user(conn, tg["id"])
    now = time.time()
    col_active = f"miner_{miner_id}_active"
    col_expires = f"miner_{miner_id}_expires"
    col_start = f"miner_{miner_id}_start"
    if user[col_active] and now < user[col_expires]:
        conn.close()
        return jsonify({"error": f"{miner['name']} already active"}), 400
    if user["ton_balance"] < miner["price"]:
        conn.close()
        return jsonify({"error": f"Need {miner['price']} TON"}), 400
    expires = now + miner["duration"] * 24 * 3600
    conn.execute(
        f"UPDATE users SET ton_balance=ton_balance-?, {col_active}=1, {col_start}=?, {col_expires}=? WHERE user_id=?",
        (miner["price"], now, expires, tg["id"])
    )
    conn.commit()
    ref_id = user["referrer_id"]
    if ref_id:
        ref = get_user(conn, ref_id)
        if ref and ref[f"miner_{miner_id}_active"] and now < ref[col_expires]:
            commission = miner["price"] * 0.10
            conn.execute("UPDATE users SET ton_balance=ton_balance+? WHERE user_id=?", (commission, ref_id))
            conn.commit()
            try:
                import requests as req, os
                req.post(f"https://api.telegram.org/bot{os.environ.get('BOT_TOKEN','')}/sendMessage",
                         json={"chat_id": ref_id, "text": f"💎 You earned {commission} TON commission!"})
            except: pass
    user = get_user(conn, tg["id"])
    conn.close()
    return jsonify({
        "success": True,
        "ton_balance": user["ton_balance"],
        "miner_id": miner_id,
        "expires": expires,
        "daily_ton": round(miner["daily"], 4)
    })

@shop_bp.route("/api/items", methods=["GET"])
def api_items():
    return jsonify({"items": ITEMS, "miners": MINERS})
