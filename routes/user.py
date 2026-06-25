import time
import random
from flask import Blueprint, request, jsonify
from db import get_db, get_user, get_inventory
from auth import auth_required

user_bp = Blueprint('user', __name__)

ITEMS = [
    {"id": 1,  "boost": 5},
    {"id": 2,  "boost": 12},
    {"id": 3,  "boost": 25},
    {"id": 4,  "boost": 45},
    {"id": 5,  "boost": 80},
    {"id": 6,  "boost": 150},
    {"id": 7,  "boost": 300},
    {"id": 8,  "boost": 600},
    {"id": 9,  "boost": 1200},
    {"id": 10, "boost": 2500},
    {"id": 11, "boost": 5000},
    {"id": 12, "boost": 10000},
]

MINERS = [
    {"id": "hyper",   "daily": 100/180},
    {"id": "nova",    "daily": 1000/180},
    {"id": "stellar", "daily": 10000/180},
    {"id": "quantum", "daily": 100000/180},
]

REFERRAL_JOIN_REWARDS = [
    10_000_000,
    1_000_000,
    100_000,
    10_000,
    1_000,
    100,
    10,
    1,
    1,
    1,
]

COMMISSION_LEVELS = [0.10, 0.01, 0.001, 0.0001, 0.00001, 0.000001, 0.0000001, 0.00000001, 0.000000001, 0.0000000001]

MILESTONES = [
    (10,   10,   10_000_000,  0),
    (50,   50,   20_000_000,  0),
    (100,  100,  50_000_000,  0),
    (1000, 1000, 70_000_000,  0),
    (10000,10000,100_000_000, 1),
]

def calc_hashrate(inv):
    return sum(item["boost"] * inv.get(str(item["id"]), 0) for item in ITEMS)

def apply_mine(conn, uid):
    user = get_user(conn, uid)
    now = time.time()
    elapsed = min(now - user["last_mine_time"], 3600 * 8)
    inv = get_inventory(conn, uid)
    earned_trx = calc_hashrate(inv) * elapsed / 10
    earned_ton = 0
    for m in MINERS:
        col_active = f"miner_{m['id']}_active"
        col_expires = f"miner_{m['id']}_expires"
        try:
            if user[col_active] and now < user[col_expires]:
                earned_ton += m["daily"] * elapsed / 86400
        except: pass
    if earned_trx > 0 or earned_ton > 0:
        conn.execute(
            "UPDATE users SET balance=balance+?, ton_balance=ton_balance+?, last_mine_time=? WHERE user_id=?",
            (earned_trx, earned_ton, now, uid)
        )
    else:
        conn.execute("UPDATE users SET last_mine_time=? WHERE user_id=?", (now, uid))

def pay_join_commission(conn, new_user_id):
    user = get_user(conn, new_user_id)
    ref_id = user["referrer_id"]
    level = 0
    while ref_id and level < len(REFERRAL_JOIN_REWARDS):
        reward = REFERRAL_JOIN_REWARDS[level]
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (reward, ref_id))
        ref = get_user(conn, ref_id)
        if not ref:
            break
        ref_id = ref["referrer_id"]
        level += 1

def pay_commission(conn, buyer_id, amount):
    user = get_user(conn, buyer_id)
    ref_id = user["referrer_id"]
    for rate in COMMISSION_LEVELS:
        if not ref_id:
            break
        conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount * rate, ref_id))
        ref = get_user(conn, ref_id)
        if not ref:
            break
        ref_id = ref["referrer_id"]

def update_counts(conn, uid, side):
    conn.execute(f"UPDATE users SET {side}_count={side}_count+1 WHERE user_id=?", (uid,))
    conn.commit()
    user = get_user(conn, uid)
    check_milestone(conn, user)
    parent = conn.execute(
        "SELECT user_id, left_child, right_child FROM users WHERE left_child=? OR right_child=?",
        (uid, uid)
    ).fetchone()
    if parent:
        parent_side = "left" if parent["left_child"] == uid else "right"
        update_counts(conn, parent["user_id"], parent_side)

def check_milestone(conn, user):
    uid = user["user_id"]
    lc = user["left_count"] or 0
    rc = user["right_count"] or 0
    current = user["balance_milestone"] or 0
    for i, (lr, rr, trx, ton) in enumerate(MILESTONES):
        milestone_num = i + 1
        if milestone_num <= current:
            continue
        if lc >= lr and rc >= rr:
            conn.execute(
                "UPDATE users SET balance=balance+?, ton_balance=ton_balance+?, balance_milestone=? WHERE user_id=?",
                (trx, ton, milestone_num, uid)
            )
            conn.execute(
                "INSERT INTO binary_rewards (user_id, milestone, reward_trx, reward_ton, created_at) VALUES (?,?,?,?,?)",
                (uid, milestone_num, trx, ton, time.time())
            )
            conn.commit()

def place_in_binary(conn, new_uid, referrer_id):
    if not referrer_id:
        return
    ref = get_user(conn, referrer_id)
    if not ref:
        return
    left = ref["left_child"]
    right = ref["right_child"]
    if left is None and right is None:
        side = random.choice(["left", "right"])
    elif left is None:
        side = "left"
    elif right is None:
        side = "right"
    else:
        side = random.choice(["left", "right"])
        deeper_id = left if side == "left" else right
        place_in_binary(conn, new_uid, deeper_id)
        return
    conn.execute(f"UPDATE users SET {side}_child=? WHERE user_id=?", (new_uid, referrer_id))
    update_counts(conn, referrer_id, side)

@user_bp.route("/api/user", methods=["POST"])
@auth_required
def api_user(tg):
    data = request.json or {}
    ref = data.get("ref")
    conn = get_db()
    user = get_user(conn, tg["id"])
    is_new = False
    if not user:
        is_new = True
        conn.execute(
            "INSERT INTO users (user_id, username, first_name, balance, ton_balance, last_mine_time, created_at) VALUES (?,?,?,?,?,?,?)",
            (tg["id"], tg.get("username",""), tg.get("first_name",""), 1000000, 0, time.time(), time.time())
        )
        conn.commit()
        if ref:
            try:
                rid = int(ref)
                if rid != tg["id"] and get_user(conn, rid):
                    conn.execute("UPDATE users SET referrer_id=? WHERE user_id=?", (rid, tg["id"]))
                    conn.commit()
                    pay_join_commission(conn, tg["id"])
                    place_in_binary(conn, tg["id"], rid)
                    conn.commit()
            except: pass
    apply_mine(conn, tg["id"])
    conn.commit()
    user = get_user(conn, tg["id"])
    inv = get_inventory(conn, tg["id"])
    now = time.time()
    miners_status = {}
    for m in MINERS:
        col_active = f"miner_{m['id']}_active"
        col_expires = f"miner_{m['id']}_expires"
        try:
            active = bool(user[col_active] and now < user[col_expires])
            expires = user[col_expires] if active else 0
        except:
            active = False
            expires = 0
        miners_status[m["id"]] = {"active": active, "expires": expires, "daily": round(m["daily"], 4)}
    conn.close()
    return jsonify({
        "user_id": user["user_id"],
        "first_name": user["first_name"],
        "balance": user["balance"],
        "ton_balance": user["ton_balance"],
        "inventory": inv,
        "hashrate": calc_hashrate(inv),
        "miners": miners_status,
    })

@user_bp.route("/api/click", methods=["POST"])
@auth_required
def api_click(tg):
    conn = get_db()
    inv = get_inventory(conn, tg["id"])
    bonus = 1 + sum(inv.values())
    conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (bonus, tg["id"]))
    conn.commit()
    user = get_user(conn, tg["id"])
    conn.close()
    return jsonify({"balance": user["balance"]})
