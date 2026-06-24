import requests
import os
from flask import Blueprint, request, jsonify
from db import get_db
from auth import parse_user

admin_bp = Blueprint('admin', __name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8935584033:AAGD6ICE5g0C5GPRAodt5XhK0gQlHUAd6jU")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8030373785"))

def is_admin():
    user = parse_user(request.headers.get("X-Init-Data", ""))
    return user and user.get("id") == ADMIN_ID

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
    except:
        pass
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
                      json={"chat_id": w["user_id"], "text": f"❌ Withdrawal of {w['amount']} TON rejected. Balance returned."})
    except:
        pass
    return jsonify({"success": True})

@admin_bp.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    if not is_admin():
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM withdrawals WHERE status='pending'").fetchone()["c"]
    conn.close()
    return jsonify({"total_users": users, "pending_withdrawals": pending})

@admin_bp.route("/api/admin/migrate", methods=["POST"])
def migrate():
    conn = get_db()
    try:
        conn.execute("ALTER TABLE users ADD COLUMN left_child INTEGER DEFAULT NULL")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN right_child INTEGER DEFAULT NULL")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN left_count INTEGER DEFAULT 0")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN right_count INTEGER DEFAULT 0")
    except: pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN balance_milestone INTEGER DEFAULT 0")
    except: pass
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Migration done"})
