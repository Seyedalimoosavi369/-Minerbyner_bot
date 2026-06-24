import time
import requests
import os
from flask import Blueprint, request, jsonify
from db import get_db, get_user
from auth import auth_required

wallet_bp = Blueprint('wallet', __name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8030373785"))
TON_WALLET = os.environ.get("TON_WALLET", "UQCs20TzgI5bmr5TJo3PigiEn0DMJhWktPOw7bo27K2FVZwI")
TRX_PER_TON = 100_000_000
MIN_WITHDRAW = 100

MINERS = [
    {"id": "hyper"},
    {"id": "nova"},
    {"id": "stellar"},
    {"id": "quantum"},
]

def has_active_miner(user):
    now = time.time()
    for m in MINERS:
        try:
            if user[f"miner_{m['id']}_active"] and now < user[f"miner_{m['id']}_expires"]:
                return True
        except: pass
    return False

@wallet_bp.route("/api/withdraw", methods=["POST"])
@auth_required
def api_withdraw(tg):
    data = request.json or {}
    amount = float(data.get("amount", 0))
    wallet = data.get("wallet", "")
    conn = get_db()
    user = get_user(conn, tg["id"])
    now = time.time()
    if not has_active_miner(user):
        conn.close()
        return jsonify({"error": "You need an active miner to withdraw"}), 400
    if amount < MIN_WITHDRAW:
        conn.close()
        return jsonify({"error": f"Minimum withdrawal is {MIN_WITHDRAW} TON"}), 400
    if not wallet:
        conn.close()
        return jsonify({"error": "Wallet address required"}), 400
    if user["ton_balance"] < amount:
        conn.close()
        return jsonify({"error": "Insufficient TON"}), 400
    conn.execute("UPDATE users SET ton_balance=ton_balance-? WHERE user_id=?", (amount, tg["id"]))
    conn.execute("INSERT INTO withdrawals (user_id, amount, wallet, created_at) VALUES (?,?,?,?)",
                 (tg["id"], amount, wallet, now))
    conn.commit()
    try:
        msg = f"💸 Withdrawal\nUser: {tg['id']}\nAmount: {amount} TON\nWallet: {wallet}"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": ADMIN_ID, "text": msg})
    except: pass
    conn.close()
    return jsonify({"success": True})

@wallet_bp.route("/api/verify_ton", methods=["POST"])
@auth_required
def api_verify_ton(tg):
    data = request.json or {}
    tx_hash = data.get("tx_hash", "")
    if not tx_hash:
        return jsonify({"error": "tx_hash required"}), 400
    conn = get_db()
    if conn.execute("SELECT * FROM ton_deposits WHERE tx_hash=?", (tx_hash,)).fetchone():
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
                     (tg["id"], tx_hash, amount_ton, time.time()))
        conn.execute("UPDATE users SET ton_balance=ton_balance+? WHERE user_id=?", (amount_ton, tg["id"]))
        conn.commit()
        user = get_user(conn, tg["id"])
        conn.close()
        return jsonify({"success": True, "amount": amount_ton, "ton_balance": user["ton_balance"]})
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500
