import requests
import os
import time
from flask import Blueprint, request, jsonify
from db import get_db, get_user
from auth import parse_user

admin_bp = Blueprint('admin', __name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8030373785"))

def is_admin():
    user = parse_user(request.headers.get("X-Init-Data", ""))
    return user and user.get("id") == ADMIN_ID

@admin_bp.route("/api/admin/reward", methods=["POST"])
def admin_reward():
    if not is_admin():
        return jsonify({"error": "Forbidden"}), 403
    data = request.json or {}
    uid = int(data.get("user_id", 0))
    trx = float(data.get("trx", 0))
    ton = float(data.get("ton", 0))
    if not uid:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    user = get_user(conn, uid)
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404
    conn.execute("UPDATE users SET balance=balance+?, ton_balance=ton_balance+? WHERE user_id=?", (trx, ton, uid))
    conn.commit()
    user = get_user(conn, uid)
    conn.close()
    try:
        msg = "🎁 You received a reward!\n"
        if trx > 0: msg += f"💛 {trx:,.0f} TRX\n"
        if ton > 0: msg += f"💎 {ton} TON\n"
        msg += "\nKeep it up! 🚀"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": uid, "text": msg})
    except: pass
    return jsonify({"success": True, "new_balance": user["balance"], "new_ton": user["ton_balance"]})

@admin_bp.route("/api/admin/reward_bot", methods=["POST"])
def admin_reward_bot():
    data = request.json or {}
    if int(data.get("admin_id", 0)) != ADMIN_ID:
        return jsonify({"error": "Forbidden"}), 403
    uid = int(data.get("user_id", 0))
    trx = float(data.get("trx", 0))
    ton = float(data.get("ton", 0))
    if not uid:
        return jsonify({"error": "user_id required"}), 400
    conn = get_db()
    user = get_user(conn, uid)
    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404
    conn.execute("UPDATE users SET balance=balance+?, ton_balance=ton_balance+? WHERE user_id=?", (trx, ton, uid))
    conn.commit()
    user = get_user(conn, uid)
    conn.close()
    try:
        msg = "🎁 You received a reward!\n"
        if trx > 0: msg += f"💛 {trx:,.0f} TRX\n"
        if ton > 0: msg += f"💎 {ton} TON\n"
        msg += "\nKeep it up! 🚀"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": uid, "text": msg})
    except: pass
    return jsonify({"success": True, "new_balance": user["balance"], "new_ton": user["ton_balance"]})

@admin_bp.route("/api/admin/withdrawals", methods=["GET"])
def admin_withdrawals():
    if not is_admin():
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    rows = conn.execute("SELECT * FROM withdrawals WHERE status='pending' ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify({"withdrawals": [dict(r) for r in rows]})

@admin_bp.route("/api/admin/approve/<int:wid>", methods=["POST"])
def admin_approve(wid):
    if not is_admin():
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    conn.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (wid,))
    conn.commit()
    w = conn.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)).fetchone()
    conn.close()
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": w["user_id"], "text": f"✅ Withdrawal of {w['amount']} TON approved!"})
    except: pass
    return jsonify({"success": True})

@admin_bp.route("/api/admin/reject/<int:wid>", methods=["POST"])
def admin_reject(wid):
    if not is_admin():
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    w = conn.execute("SELECT * FROM withdrawals WHERE id=?", (wid,)).fetchone()
    conn.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (wid,))
    conn.execute("UPDATE users SET ton_balance=ton_balance+? WHERE user_id=?", (w["amount"], w["user_id"]))
    conn.commit()
    conn.close()
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": w["user_id"], "text": f"❌ Withdrawal of {w['amount']} TON rejected."})
    except: pass
    return jsonify({"success": True})

@admin_bp.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    if not is_admin():
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM withdrawals WHERE status='pending'").fetchone()["c"]
    total_trx = conn.execute("SELECT SUM(balance) as s FROM users").fetchone()["s"] or 0
    conn.close()
    return jsonify({"total_users": users, "pending_withdrawals": pending, "total_trx": total_trx})

@admin_bp.route("/api/admin/stats_bot", methods=["GET"])
def admin_stats_bot():
    if int(request.args.get("admin_id", 0)) != ADMIN_ID:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM withdrawals WHERE status='pending'").fetchone()["c"]
    total_trx = conn.execute("SELECT SUM(balance) as s FROM users").fetchone()["s"] or 0
    conn.close()
    return jsonify({"total_users": users, "pending_withdrawals": pending, "total_trx": total_trx})

@admin_bp.route("/api/admin/users_bot", methods=["GET"])
def admin_users_bot():
    if int(request.args.get("admin_id", 0)) != ADMIN_ID:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    rows = conn.execute("SELECT user_id, first_name, username, balance FROM users ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify({"users": [dict(r) for r in rows]})

@admin_bp.route("/api/admin/migrate", methods=["POST"])
def migrate():
    conn = get_db()
    for col in ["left_child INTEGER DEFAULT NULL", "right_child INTEGER DEFAULT NULL",
                "left_count INTEGER DEFAULT 0", "right_count INTEGER DEFAULT 0",
                "balance_milestone INTEGER DEFAULT 0"]:
        try: conn.execute(f"ALTER TABLE users ADD COLUMN {col}")
        except: pass
    conn.commit()
    conn.close()
    return jsonify({"success": True})
