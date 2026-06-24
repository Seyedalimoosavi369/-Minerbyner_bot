import math
import time
from flask import Blueprint, request, jsonify
from db import get_db, get_user, get_inventory
from auth import auth_required
from routes.user import calc_hashrate, apply_mine, pay_commission

shop_bp = Blueprint('shop', __name__)

ITEMS = [
    {"id": 1, "name": "Basic Core", "price": 10000, "boost": 5},
    {"id": 2, "name": "Quantum Rig", "price": 20000, "boost": 12},
    {"id": 3, "name": "Nebula Core", "price": 30000, "boost": 25},
    {"id": 4, "name": "Nano Miner", "price": 40000, "boost": 45},
    {"id": 5, "name": "Ion Reactor", "price": 50000, "boost": 80},
    {"id": 6, "name": "Dark Plasma", "price": 60000, "boost": 150},
    {"id": 7, "name": "Void Engine", "price": 70000, "boost": 300},
    {"id": 8, "name": "Gravity Drill", "price": 80000, "boost": 600},
    {"id": 9, "name": "Star Forge", "price": 90000, "boost": 1200},
    {"id": 10, "name": "Cyber Node", "price": 100000, "boost": 2500},
    {"id": 11, "name": "Nova Matrix", "price": 110000, "boost": 5000},
    {"id": 12, "name": "God Engine", "price": 120000, "boost": 10000},
]

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
        pay_commission(conn, tg["id"], ton_cost * 10_000_000)
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

@shop_bp.route("/api/items", methods=["GET"])
def api_items():
    return jsonify({"items": ITEMS})
