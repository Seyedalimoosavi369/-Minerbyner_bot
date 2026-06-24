from flask import Blueprint, jsonify
from db import get_db, get_user, get_inventory
from auth import auth_required

network_bp = Blueprint('network', __name__)

ITEM_BOOSTS = [(1,5),(2,12),(3,25),(4,45),(5,80),(6,150),(7,300),(8,600),(9,1200),(10,2500),(11,5000),(12,10000)]

def calc_hashrate(inv):
    return sum(boost * inv.get(str(iid), 0) for iid, boost in ITEM_BOOSTS)

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

@network_bp.route("/api/leaderboard/hashrate", methods=["GET"])
@auth_required
def leaderboard_hashrate(tg):
    conn = get_db()
    users = conn.execute("SELECT user_id, first_name, username FROM users").fetchall()
    result = []
    for u in users:
        inv = get_inventory(conn, u["user_id"])
        hashrate = calc_hashrate(inv)
        ref_count = conn.execute("SELECT COUNT(*) as c FROM users WHERE referrer_id=?",
                                 (u["user_id"],)).fetchone()["c"]
        if hashrate > 0 or ref_count > 0:
            result.append({
                "user_id": u["user_id"],
                "first_name": u["first_name"],
                "username": u["username"],
                "hashrate": hashrate,
                "referrals": ref_count
            })
    conn.close()
    result.sort(key=lambda x: x["hashrate"], reverse=True)
    return jsonify({"leaderboard": result[:50]})
