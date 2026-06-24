from flask import Blueprint, jsonify
from db import get_db, get_user
from auth import auth_required

network_bp = Blueprint('network', __name__)

@network_bp.route("/api/team", methods=["GET"])
@auth_required
def api_team(tg):
    conn = get_db()
    user = get_user(conn, tg["id"])
    referrals = conn.execute(
        "SELECT user_id, first_name, username, balance FROM users WHERE referrer_id=?",
        (tg["id"],)
    ).fetchall()
    rewards = conn.execute(
        "SELECT * FROM binary_rewards WHERE user_id=? ORDER BY created_at DESC",
        (tg["id"],)
    ).fetchall()
    result = {
        "referrals": [{"user_id": r["user_id"], "first_name": r["first_name"],
                       "username": r["username"], "balance": r["balance"]} for r in referrals],
        "count": len(referrals),
        "left_count": user["left_count"] or 0,
        "right_count": user["right_count"] or 0,
        "balance_milestone": user["balance_milestone"] or 0,
        "rewards": [{"milestone": r["milestone"], "reward_trx": r["reward_trx"],
                     "reward_ton": r["reward_ton"]} for r in rewards],
    }
    conn.close()
    return jsonify(result)

@network_bp.route("/api/leaderboard", methods=["GET"])
@auth_required
def api_leaderboard(tg):
    conn = get_db()
    top = conn.execute(
        "SELECT user_id, first_name, username, balance FROM users ORDER BY balance DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify({"leaderboard": [{"user_id": r["user_id"], "first_name": r["first_name"],
                                      "username": r["username"], "balance": r["balance"]} for r in top]})
